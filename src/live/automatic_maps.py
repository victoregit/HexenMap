"""Bounded background map discovery; the existing active tracker stays untouched."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import hashlib
import json
import time

import cv2
import numpy as np

from src.live.budget_vision import BudgetRecognizer
from src.live.reference import ReferenceCancelled
from src.live.reference_store import read_spec
from src.live.vision import TerrainMatcher, confirmed_circle, template_visible


class Confirmation:
    """Three distinct, ordered captures; failures and context changes break a streak."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.scope = None
        self.count = 0
        self.stamp = -float('inf')

    def accept(self, observation):
        scope = (observation.map_id, observation.layer_id)
        if not observation.fresh(observation.captured_at) or None in scope:
            self.reset()
            return None
        if observation.captured_at <= self.stamp:
            return None
        self.count = self.count+1 if scope == self.scope else 1
        self.scope, self.stamp = scope, observation.captured_at
        return scope if self.count >= 3 else None


class MapRouter:
    """At most 1,200 float32 SIFT descriptors per map, loaded only on recovery."""
    def __init__(self, scopes, root):
        self.engine = object.__new__(TerrainMatcher)
        self.engine.sift = cv2.SIFT_create(nfeatures=1200, contrastThreshold=.025)
        descriptors, self.owners = [], []
        counts=Counter(scope[0] for scope in scopes)
        for scope in scopes:
            path = root / scope[0] / scope[1] / 'routing.npz'
            if not path.is_file():
                continue
            metadata=json.loads((path.parent/'manifest.json').read_text(encoding='utf-8'))
            expected=metadata.get('routing',{}).get('sha256')
            if expected is None or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                continue
            with np.load(path, allow_pickle=False) as source:
                desc = np.asarray(source['descriptors'], dtype=np.float32)
            if desc.ndim != 2 or desc.shape[1] != 128 or len(desc)>1200 or not np.isfinite(desc).all():
                raise ValueError('Invalid map routing index')
            # More floors must not multiply the persistent routing-memory budget.
            budget=max(1,1200//counts[scope[0]])
            desc=desc[:budget].copy()
            descriptors.append(desc)
            self.owners.extend([scope]*len(desc))
        self.matcher = None
        if descriptors:
            self.matcher = cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=32))
            self.matcher.add([np.concatenate(descriptors)])
            self.matcher.train()

    def rank(self, frame, pack):
        h,w = frame.shape[:2]
        mask = np.zeros((h,w),np.uint8)
        if template_visible(frame,pack.map_ui,pack.map_ui_roi):
            mask[int(.08*h):int(.9*h),int(.2*w):int(.8*w)] = 255
            self.engine.query_scale = 1.
        else:
            circle = confirmed_circle(frame)
            if circle is None:
                return None, False
            x,y,r = circle
            cv2.circle(mask,(round(x),round(y)),max(1,round(r-8)),255,-1)
            cv2.circle(mask,(round(x),round(y)),max(8,round(r*.17)),0,-1)
            self.engine.query_scale = 1.5
        query = self.engine.query(frame,mask)
        if query is None:
            return None, False
        votes = Counter()
        if self.matcher is not None:
            for pair in self.matcher.knnMatch(query[1],k=8):
                if len(pair)<2:
                    continue
                first = pair[0]
                other = next((m for m in pair[1:] if self.owners[m.trainIdx]!=self.owners[first.trainIdx]),None)
                if other is not None and first.distance<.8*other.distance:
                    votes[self.owners[first.trainIdx]] += 1
        ranked = votes.most_common()
        ambiguous = len(ranked)>1 and ranked[0][1]>=4 and ranked[1][1]>=.75*ranked[0][1]
        return [scope for scope,count in ranked if count>=4], ambiguous


class AutomaticMapSearch:
    def __init__(self, scopes, active_scope, root, cache_dir, pack):
        alternatives=[s for s in scopes if s!=active_scope]
        self.scopes=[s for s in alternatives if s[1]=='surface']+[s for s in alternatives if s[1]!='surface']
        self.root, self.cache_dir, self.pack = Path(root), Path(cache_dir), pack
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='MapDiscovery')
        self.future = None
        self.closed = threading.Event()
        self.generation = 0
        self.lost_since = None
        self.last_submit = -float('inf')
        self.searching = False
        self.confirmed = False
        self.router = None
        self.candidate = None
        self.candidate_scope = None
        self.candidate_generation = None
        self.cursor = 0
        self.confirmation = Confirmation()
        self.state = 'tracking'
        self.located_once=False
        self.transition_seen=False
        self.hidden_since=None
        self.loss_grace=5.

    def reset(self):
        self.generation += 1
        self.lost_since = None
        self.searching = False
        self.confirmed = False
        self.state = 'tracking'
        self.transition_seen=False
        self.hidden_since=None
        # Candidate OpenCV caches must not stay resident after tracking recovers.
        if self.future is not None or self.candidate is not None:
            self.pool.submit(self._drop_candidate)

    def tick(self, frame, stamp, observation, *, surface=None, paused=False):
        if observation.fresh(stamp):
            self.located_once=True
            if self.searching or self.lost_since is not None:
                self.reset()
            return None
        if paused:
            if self.searching or self.lost_since is not None:self.reset()
            return None
        if frame is None or not self.scopes or self.confirmed:
            return None
        # LK/absolute-registration gaps while the HUD remains visible do not
        # indicate travel. Avoid loading competing SIFT indices on every gap.
        if surface is not None:
            if surface=='hidden':
                if self.hidden_since is None:self.hidden_since=stamp
                if stamp-self.hidden_since>=.75:self.transition_seen=True
            else:
                self.hidden_since=None
                if surface=='map':self.transition_seen=True
            if self.located_once and not self.transition_seen:
                self.lost_since=None
                return None
        if self.lost_since is None:
            self.lost_since = stamp
        if stamp-self.lost_since<self.loss_grace:
            return None
        self.searching = True
        self.state = 'searching'
        if self.future is not None:
            if not self.future.done():
                return None
            try:
                generation, scope, captured_at = self.future.result()
            except ReferenceCancelled:
                generation, scope = None, None
            except Exception:
                self.state = 'reference_error'
                generation, scope = None, None
            self.future = None
            if generation==self.generation and scope is not None and 0<=stamp-captured_at<=1.5:
                self.confirmed = True
                self.state = 'confirmed'
                return scope
            if generation==self.generation and scope is not None:
                self.pool.submit(self._drop_candidate)
        if stamp-self.last_submit>=1:
            self.last_submit = stamp
            self.future = self.pool.submit(self._probe,frame.copy(),stamp,self.generation)
        return None

    def _drop_candidate(self):
        if self.candidate is not None:
            self.candidate.close()
        self.candidate = None
        self.candidate_scope = None
        self.confirmation.reset()

    def _next_scope(self,ranked):
        # A coarse false positive must not starve every other map indefinitely.
        order=ranked+[scope for scope in self.scopes if scope not in ranked]
        scope=order[self.cursor%len(order)]
        self.cursor+=1
        return scope

    def _probe(self, frame, stamp, generation):
        cancelled = lambda: self.closed.is_set() or self.generation!=generation
        if cancelled():
            raise ReferenceCancelled('Map discovery canceled')
        if self.candidate_generation!=generation:
            self._drop_candidate()
        if self.router is None:
            self.router = MapRouter(self.scopes,self.root)
        ranked, ambiguous = self.router.rank(frame,self.pack)
        if ranked is None:
            self._drop_candidate()
            return generation, None, stamp
        if ambiguous:
            self._drop_candidate()
            self.state = 'ambiguous'
            return generation, None, stamp
        if self.candidate is None:
            scope = self._next_scope(ranked)
            directory = self.root / scope[0] / scope[1]
            spec = read_spec(directory,'appsample',scope[0],scope[1],'appsample-webmercator-z14',0)
            if cancelled():
                raise ReferenceCancelled('Map discovery canceled')
            self.candidate = BudgetRecognizer([spec],self.cache_dir,'light',cancelled)
            self.candidate_scope, self.candidate_generation = scope,generation
        observation = self.candidate.observe(frame,stamp)
        if cancelled():
            self._drop_candidate()
            raise ReferenceCancelled('Map discovery canceled')
        if time.monotonic()-stamp>1.5:
            self.confirmation.reset()
            return generation, None, stamp
        scope = self.confirmation.accept(observation)
        if not observation.fresh(stamp) or scope is not None:
            self._drop_candidate()
        return generation, scope, stamp

    def diagnostics(self):
        return {'map_discovery':self.state,'map_candidate':self.candidate_scope,
                'map_confirmations':self.confirmation.count}

    def close(self):
        self.closed.set()
        self.generation += 1
        self.pool.shutdown(wait=True,cancel_futures=True)
        self._drop_candidate()
        self.router = None
