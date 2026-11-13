"""Coarse routing plus bounded native-resolution blocks, shared across selected layers."""
from src.live.i18n import tr as _tr
from collections import Counter
import math
import time

import cv2
import numpy as np

from src.live.reference_store import FeatureCache, ReferenceStore, blocks, check_cancel
from src.live.vision import (Observation,TerrainMatcher,template_visible,foreground_ui_visible,
                             confirmed_circle)


class BudgetRecognizer:
    def __init__(self,packs,cache_dir,mode='light',cancelled=lambda:False):
        cv2.setNumThreads(2)
        self.packs=tuple(packs)
        if not self.packs:raise ValueError(_tr('Nenhuma referência válida para a seleção'))
        self.pack=self.packs[0];self.cancelled=cancelled
        self.store=ReferenceStore(FeatureCache(cache_dir,cancelled),mode)
        self.mode=mode;self.circle_hint=None;self.last={};self.position=None;self.cursor={}
        self.bad=set();self.failed={};self.coarse={};self.coarse_points={};self.coarse_owners={}
        self.rasters=[r for p in self.packs for r in p.rasters]
        self.tiles={id(r):list(blocks(r)) for r in self.rasters}
        self.by_surface={}
        self.fallback_tiles={id(r):list(blocks(r,1.25)) for r in self.rasters if r.surface=='map'}
        self.query_engine=object.__new__(TerrainMatcher)
        self.query_engine.sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.025)
        for surface in ('map','minimap'):
            sources=[r for r in self.rasters if r.surface==surface]
            if surface=='minimap' and not sources:sources=[r for r in self.rasters if r.surface=='map']
            self.by_surface[surface]=[b for r in sources for b in self.tiles[id(r)]]
            if surface=='map':self.by_surface[surface].extend(b for r in self.rasters if r.surface=='minimap' and r.map_compatible for b in self.tiles[id(r)])
            if not sources:continue
            total=sum(r.width*r.height for r in sources);descriptors=[];points=[];owners=[]
            for r in sources:
                check_cancel(cancelled)
                budget=(min(1200,max(200,100000//len(sources))) if surface=='minimap'
                        else max(30,min(2000,round(16000*r.width*r.height/total))))
                xy,desc=self.store.features.coarse(r,budget)
                if len(desc)<2:continue
                descriptors.append(desc);points.append(xy);owners.extend([r]*len(xy))
            if not descriptors:continue
            descriptors=np.concatenate(descriptors);self.coarse_points[surface]=np.concatenate(points)
            self.coarse_owners[surface]=owners
            matcher=cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=64))
            matcher.add([descriptors]);matcher.train();self.coarse[surface]=matcher
        self.global_map=None
        if not self.coarse:raise ValueError(_tr('Referências sem detalhes suficientes para localização'))
        selected_maps={pack.map_id for pack in self.packs}
        if mode=='global' and len(selected_maps)==1:self.preload_global(next(iter(selected_maps)))

    def preload_global(self,map_id):
        # Automatic map choice must never mean all installed maps resident at once.
        self.store.close();self.global_map=None
        try:
            for tile in (b for surface in self.by_surface.values() for b in surface):
                if self.packs[tile.raster.pack_index].map_id!=map_id:continue
                check_cancel(self.cancelled)
                try:self.store.get(tile)
                except ValueError:self.bad.add(tile.key)
            self.global_map=map_id
        except BaseException:
            self.store.close();raise

    def close(self):
        self.store.close()
        for matcher in self.coarse.values():
            try:
                matcher.clear()
            except Exception:
                pass
        self.coarse.clear();self.coarse_points.clear();self.coarse_owners.clear()

    def diagnostics(self):
        return dict(self.store.diagnostics(),coarse_surfaces=len(self.coarse),selected_layers=len(self.packs),global_map=self.global_map)

    def candidates(self,surface,query):
        candidates=[]
        def add(tile):
            if (tile is not None and tile.key not in self.bad and self.failed.get(tile.key,0)<=time.monotonic()
                    and all(t.key!=tile.key for t in candidates)):candidates.append(tile)
        add(self.last.get(surface))
        yield from candidates
        initial=len(candidates)
        def ranked(which,tile_groups):
            if query is None or which not in self.coarse:return []
            votes=Counter();owners=self.coarse_owners[which];points=self.coarse_points[which];lookup={}
            inverses={id(r):cv2.invertAffineTransform(r.matrix) for r in self.rasters}
            def world(index):
                owner=owners[index];point=points[index]
                return inverses[id(owner)]@np.array([*point,1.])
            for pair in self.coarse[which].knnMatch(query[1],k=8):
                if len(pair)<2:continue
                a=pair[0];origin=world(a.trainIdx)
                # Overlap copies of one landmark are not competing locations.
                b=next((m for m in pair[1:] if owners[m.trainIdx].pack_index!=owners[a.trainIdx].pack_index
                        or np.linalg.norm(world(m.trainIdx)-origin)>12),None)
                if b is None:continue
                if a.distance>=.83*b.distance:continue
                r=owners[a.trainIdx];x,y=points[a.trainIdx]
                tile=min(tile_groups[id(r)],key=lambda t:(max(0,t.box[0]-x,x-t.box[2])**2+max(0,t.box[1]-y,y-t.box[3])**2,
                                                          (x-(t.box[0]+t.box[2])/2)**2+(y-(t.box[1]+t.box[3])/2)**2))
                votes[tile.key]+=1;lookup[tile.key]=tile
            return [lookup[key] for key,count in votes.most_common(5) if count>=2]
        for tile in ranked(surface,self.tiles):add(tile)
        if surface=='minimap':
            for tile in ranked('map',self.fallback_tiles):add(tile)
            if self.position is not None:
                fallback=[t for group in self.fallback_tiles.values() for t in group]
                for tile in sorted(fallback,key=lambda t:t.distance(self.position))[:1]:add(tile)
        if self.position is not None:
            for tile in sorted(self.by_surface[surface],key=lambda t:t.distance(self.position))[:2]:add(tile)
        all_tiles=self.by_surface[surface];cursor=self.cursor.get(surface,0)
        for step in range(min(2,len(all_tiles))):add(all_tiles[(cursor+step)%len(all_tiles)])
        if all_tiles:self.cursor[surface]=(cursor+2)%len(all_tiles)
        yield from candidates[initial:]

    def observe(self,frame,captured_at=None):
        stamp=time.monotonic() if captured_at is None else captured_at
        if frame is None or not frame.size:return Observation('hidden',stamp,reason=_tr('Captura indisponível'))
        check_cancel(self.cancelled);h,w=frame.shape[:2];p=self.pack;circle=None
        if template_visible(frame,p.map_ui,p.map_ui_roi):
            surface='map';mask=np.zeros((h,w),np.uint8);mask[int(.08*h):int(.9*h),int(.2*w):int(.8*w)]=255
        else:
            hud=template_visible(frame,p.gameplay_ui,p.gameplay_ui_roi) or foreground_ui_visible(frame,p.gameplay_ui,p.gameplay_ui_roi)
            # A current circumference plus the native cyan pointer can qualify
            # gameplay independently of a single colour-sensitive HUD glyph.
            circle=confirmed_circle(frame,self.circle_hint)
            if circle is None:return Observation('hidden',stamp,reason=_tr('Minimapa não reconhecido'))
            self.circle_hint=circle;surface='minimap';x,y,r=circle
            mask=np.zeros((h,w),np.uint8);cv2.circle(mask,(round(x),round(y)),max(1,round(r-8)),255,-1)
            cv2.circle(mask,(round(x),round(y)),max(8,round(r*.17)),0,-1)
        # The HUD is tiny. A small crop-only resampling recovers stable corners
        # without relaxing the geometric inlier or error gates.
        self.query_engine.query_scale=1.5 if surface=='minimap' else 1.
        query=self.query_engine.query(frame,mask)
        if query is None:return Observation('hidden',stamp,reason=_tr('Detalhes insuficientes no mapa'))
        queries=[(mask,query)]
        if circle:
            for fraction in (.85,.7):
                inner=np.zeros_like(mask);cv2.circle(inner,(round(x),round(y)),max(1,round((r-8)*fraction)),255,-1)
                inner=cv2.bitwise_and(inner,mask);queries.append((inner,None))
        start=time.monotonic();loads=0;fits=[]
        for tile in self.candidates(surface,query):
            check_cancel(self.cancelled)
            if fits and tile.raster.pack_index==fits[0][0].raster.pack_index:continue
            missing=tile.key not in self.store.cache
            if self.mode=='light' and missing and (loads>=4 or time.monotonic()-start>.75):break
            try:matcher=self.store.get(tile)
            except ValueError:self.bad.add(tile.key);continue
            loads+=missing
            for n,(candidate_mask,q) in enumerate(queries):
                if q is None:
                    q=self.query_engine.query(frame,candidate_mask);queries[n]=(candidate_mask,q)
                if q is None:continue
                fit=matcher.match(frame,candidate_mask,query=q)
                if fit is not None:
                    fits.append((tile,fit));break
            if fits and len(self.packs)==1:break
            if fit is None and tile is not self.last.get(surface):self.failed[tile.key]=time.monotonic()+2
            del matcher
        if not fits:return Observation('hidden',stamp,reason=_tr('Localizando trecho do mapa…'))
        if len({tile.raster.pack_index for tile,fit in fits})>1:return Observation('hidden',stamp,reason=_tr('Camada ambígua'))
        tile,(matrix,confidence,error)=fits[0]
        self.last[surface]=tile
        self.store.protected_key=tile.key
        center=circle[:2] if circle else (w*.5,h*.5)
        self.position=tuple(cv2.invertAffineTransform(matrix)@np.array([*center,1.]))
        p=self.packs[tile.raster.pack_index]
        if self.mode=='global' and self.global_map!=p.map_id:self.preload_global(p.map_id)
        self.pack=p
        return Observation(surface,stamp,matrix,confidence,error,circle,self.position if circle else None,
                           'Explorando' if circle else 'Mapa reconhecido',p.map_id,p.layer_id)
