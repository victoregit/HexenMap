"""Conservative chest-opening events; missing qualified visual evidence disables writes."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from functools import lru_cache

import cv2
import numpy as np

from src.live.chest_types import CHEST_NAMES

DESIGN_SIZE=(1920,1080)
# Existing proximity tolerances expressed in the Full HD design space.
NEAR_RADIUS=25.3125
CLEAR_GAP=8.4375


@lru_cache(maxsize=32)
def contrast_template(shape,raw):
    image=np.frombuffer(raw,np.uint8).reshape(shape).astype(np.float32)
    image=cv2.GaussianBlur(image,(0,0),.65)
    return np.maximum(0,image-cv2.GaussianBlur(image,(0,0),2))


@dataclass(frozen=True)
class OpeningEvent:
    token: int
    stamp: float
    observation: object
    hud_scale: float = 1.


class ChestSignals:
    """A local, reviewed template pack. No downloads, OCR or game-memory access."""
    def __init__(self,directory,*,review_only=False):
        self.templates={};self.ready=False;self.reference_size=DESIGN_SIZE;self.anchors={}
        self.methods={};self.alternatives={};self.scores={};self.state='idle'
        self.hud_scale=1.
        self.layout_size=None;self.detected_hud_height=None
        self.reason='Aguardando conferência de uma abertura real de baú.'
        self.phase=None;self.token=0;self.quiet=None;self.last_stamp=None
        self.opening_count=0;self.loot_seen=-math.inf;self.gem_seen=-math.inf;self.exp_seen=-math.inf
        try:
            root=Path(directory).resolve();data=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
            validation=data.get('validation',{})
            if (data.get('schema')!=1 or (validation.get('approved') is not True and not review_only)
                    or not validation.get('positive_sessions') or not validation.get('negative_sessions')
                    or not validation.get('reviewed_at')):return
            # Legacy client_size records where artwork was captured, not a lock
            # on the player's display. Preserve the original pixels and hashes.
            size=data.get('reference_size',data.get('client_size'))
            if size is not None:
                if not isinstance(size,list) or len(size)!=2 or any(type(v) is not int or v<1 for v in size):return
                self.reference_size=tuple(size)
            def decode(entry):
                path=(root/entry['file']).resolve()
                if not path.is_relative_to(root):raise ValueError('Template fora da pasta')
                raw=path.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Template alterado')
                template=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_GRAYSCALE)
                roi=tuple(float(v) for v in entry['roi']);threshold=float(entry['threshold'])
                if (template is None or min(template.shape)<6 or float(template.std())<5
                        or len(roi)!=4 or min(roi)<0 or min(roi[2:])<=0
                        or roi[0]+roi[2]>1 or roi[1]+roi[3]>1 or not .85<=threshold<1):
                    raise ValueError('Sinal inválido')
                method=entry.get('method','grayscale')
                if method not in ('grayscale','white_glyph','local_contrast'):raise ValueError('Método visual inválido')
                return template,roi,threshold,method
            for role in ('opening','loot','primogem','adventure_exp'):
                if role=='adventure_exp' and role not in data['signals']:continue
                entry=data['signals'][role]
                template,roi,threshold,method=decode(entry)
                self.templates[role]=(template,roi,threshold);self.methods[role]=method
                self.alternatives[role]=[decode(e) for e in entry.get('variants',[])]
                anchor=entry.get('anchor','center' if role=='opening' else 'left')
                if anchor not in ('left','center','right'):raise ValueError('Âncora inválida')
                self.anchors[role]=anchor
            self.ready=True;self.reason='Beta: escala automática da janela, referência Full HD. HUD em português; mudanças na interface do jogo ainda exigem conferência. F10 desfaz.'
        except (OSError,ValueError,KeyError,TypeError,cv2.error):
            self.templates.clear()

    def reset(self):
        self.phase=None;self.quiet=None;self.last_stamp=None
        self.opening_count=0;self.loot_seen=-math.inf;self.gem_seen=-math.inf;self.exp_seen=-math.inf
        self.state='idle'

    def region(self,role,roi,width,height,hud_height=None):
        """Uniform HUD scaling, with side/center anchoring for wider displays."""
        rw,rh=self.reference_size
        scale=(height if hud_height is None else hud_height)/rh
        anchor=self.anchors.get(role,'center' if role=='opening' else 'left')
        offset=(width-rw*scale)*{'left':0.,'center':.5,'right':1.}[anchor]
        x,y,w,h=roi
        left=max(0,min(width,round(offset+x*rw*scale)))
        right=max(left,min(width,round(offset+(x+w)*rw*scale)))
        top=max(0,min(height,round(y*height)))
        bottom=max(top,min(height,round((y+h)*height)))
        return left,top,right-left,bottom-top

    def score_crop(self,crop,template,height,method='grayscale'):
        if crop is None or crop.size==0:return 0.
        gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        scale=self.reference_size[1]/height
        if scale!=1.:
            gray=cv2.resize(gray,(max(1,round(gray.shape[1]*scale)),max(1,round(gray.shape[0]*scale))),
                            interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_CUBIC)
        if gray.shape[0]<template.shape[0] or gray.shape[1]<template.shape[1]:return 0.
        if method=='white_glyph':
            gray=cv2.threshold(gray,205,255,cv2.THRESH_BINARY)[1]
            template=cv2.threshold(template,205,255,cv2.THRESH_BINARY)[1]
        elif method=='local_contrast':
            gray=gray.astype(np.float32)
            gray=cv2.GaussianBlur(gray,(0,0),.65)
            gray=np.maximum(0,gray-cv2.GaussianBlur(gray,(0,0),2))
            template=contrast_template(template.shape,template.tobytes())
        return float(cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED).max())

    def match_crop(self,crop,template,height,threshold):
        return self.score_crop(crop,template,height)>=threshold

    def read_signals(self,width,height,get_crop):
        if self.layout_size!=(width,height):
            self.layout_size=(width,height);self.detected_hud_height=None
        self.hud_scale=(self.detected_hud_height or height)/DESIGN_SIZE[1];self.scores={};result={};crops={}
        heights=[self.detected_hud_height] if self.detected_hud_height else [height]
        width_height=width*self.reference_size[1]/self.reference_size[0]
        if self.detected_hud_height is None and width_height<height*.98:heights.append(width_height)
        for role,(template,roi,threshold) in self.templates.items():
            result[role]=False;self.scores[role]=0.
            entries=[(template,roi,threshold,self.methods.get(role,'grayscale')),*self.alternatives.get(role,[])]
            for template,roi,threshold,method in entries:
                scores=[]
                for hud_height in heights:
                    box=self.region(role,roi,width,height,hud_height)
                    if box not in crops:
                        crop=get_crop(box) if min(box[2:])>0 else None
                        crops[box]=crop.copy() if crop is not None else None
                    scores.append((self.score_crop(crops[box],template,hud_height,method),hud_height))
                score,hud_height=max(scores)
                self.scores[role]=max(self.scores[role],score)
                if score>=threshold:
                    result[role]=True
                    if role=='opening':
                        self.detected_hud_height=hud_height;self.hud_scale=hud_height/DESIGN_SIZE[1]
                    break
        return result

    def measure(self,frame):
        if not self.ready or frame is None:return {}
        h,w=frame.shape[:2]
        def crop(box):
            x,y,rw,rh=box
            return frame[y:y+rh,x:x+rw]
        return self.read_signals(w,h,crop)

    def capture_signals(self,native,rect):
        """Only the configured HUD rectangles, from the game client DC."""
        return self.read_signals(rect.width,rect.height,lambda box:native.capture(rect,region=box))

    def resolve_opening(self,observation,now):
        if self.phase and self.phase[0]=='opening_unlocated':
            _,opened,_,scale=self.phase
            if 0<=now-opened<=3 and observation.fresh(opened) and abs(observation.captured_at-opened)<1e-5:
                self.phase=('opening',opened,observation,scale);self.state='recovered_opening'

    def advance(self,signals,observation,stamp,gameplay_confirmed=False):
        located=observation.fresh(stamp) and observation.surface=='minimap'
        if not self.ready or (not located and not gameplay_confirmed):
            self.reset();return None
        if self.last_stamp is not None and not 0<=stamp-self.last_stamp<=.6:self.reset()
        self.last_stamp=stamp
        opening=signals.get('opening',False)
        loot=signals.get('loot',False);gem=signals.get('primogem',False);exp=signals.get('adventure_exp',False)
        if self.phase and (self.phase[0]=='done'):
            self.state='duplicate_wave'
            if not opening and not loot and not gem and not exp:
                if self.quiet is None:self.quiet=stamp
                if stamp-self.quiet>=1.5:self.phase=None
            else:self.quiet=None
            return None
        if self.phase and self.phase[0]=='opening_unlocated' and stamp-self.phase[1]>3:
            self.reset();self.state='unresolved_opening';return None
        if self.phase and located and self.phase[0]!='opening_unlocated':
            old=self.phase[2]
            displacement=(np.linalg.norm(observation.world_to_screen[:,:2]@(np.asarray(observation.player)-old.player))
                          if observation.player is not None and old.player is not None else math.inf)
            if (stamp-self.phase[1]>6 or observation.map_id!=old.map_id or observation.layer_id!=old.layer_id
                    or displacement>36*self.hud_scale or abs(self.phase[3]-self.hud_scale)>.001):
                self.reset();self.last_stamp=stamp
        if self.phase and stamp-self.phase[1]>6:self.reset();self.last_stamp=stamp
        if opening:
            self.opening_count+=1
            if self.opening_count>=2:
                if self.phase is None:
                    self.phase=('opening' if located else 'opening_unlocated',stamp,observation,self.hud_scale)
                    self.loot_seen=-math.inf;self.gem_seen=-math.inf;self.exp_seen=-math.inf
                elif self.phase[0]=='opening' and located:
                    self.phase=('opening',stamp,observation,self.hud_scale)
                self.state='armed' if self.phase[0]=='opening' else 'recovering_opening'
            return None
        self.opening_count=0
        if self.phase:
            if loot:self.loot_seen=stamp
            if gem:self.gem_seen=stamp
            if exp:self.exp_seen=stamp
            self.state='awaiting_reward'
        else:self.state='awaiting_chest'
        # The game staggers the notifications; both must follow the prompt's
        # disappearance, within one short reward wave, rather than one frame.
        reward=max(self.gem_seen,self.exp_seen)
        if (self.phase and self.phase[0]=='opening' and abs(self.loot_seen-reward)<=2
                and self.phase[1]<min(self.loot_seen,reward)
                and max(self.loot_seen,reward)-self.phase[1]<=6
                and 0<stamp-self.phase[1]<=6):
            _,opened,at_open,scale=self.phase;self.token+=1;self.phase=('done',stamp,None);self.quiet=None
            self.state='confirmed'
            return OpeningEvent(self.token,opened,at_open,scale)
        return None


class AutoMark:
    def __init__(self):
        self.pending=None;self.seen=set();self.context=None
        self.last_reason='idle';self.last_candidates=[]

    def reset(self):self.pending=None;self.context=None

    @staticmethod
    def scope(session):return id(session.items),session.region_id,session.map_id,session.layer_id

    def apply(self,event,session,now):
        self.last_candidates=[]
        def result(value,reason):self.last_reason=reason;return value
        if event.token in self.seen:return result('duplicate','duplicate_event')
        self.seen.add(event.token)
        if len(self.seen)>128:self.seen={event.token}
        obs=event.observation
        scale=event.hud_scale
        if (not 0<=now-event.stamp<=6 or not obs.fresh(event.stamp) or obs.surface!='minimap'
                or obs.player is None or obs.circle is None or obs.map_id!=session.map_id
                or (session.layer_id and obs.layer_id!=session.layer_id)
                or not math.isfinite(scale) or not .1<=scale<=8):return result('ignored','expired_or_changed_scope')
        candidates=[]
        for item in session.scoped_items():
            if item.category not in CHEST_NAMES:continue
            if item.map_id!=obs.map_id or obs.layer_id not in (item.layer_ids or (item.layer_id,)):continue
            point=obs.world_to_screen@np.array([item.x,item.y,1.])
            distance=math.hypot(point[0]-obs.circle[0],point[1]-obs.circle[1])
            if distance<=NEAR_RADIUS*scale:candidates.append((distance,item))
        candidates.sort(key=lambda pair:(pair[0],pair[1].id))
        self.last_candidates=[(item.id,round(distance,2),session.is_collected(item.id)) for distance,item in candidates[:4]]
        if not candidates:return result('ignored','no_nearby_chest')
        if session.is_collected(candidates[0][1].id):return result('ignored','nearest_already_collected')
        uncertainty=max(obs.position_uncertainty_px,obs.error_px)
        if not math.isfinite(uncertainty) or uncertainty>3:return result('ignored','uncertain_opening_position')
        if len(candidates)==1 or (candidates[1][0]-candidates[0][0]>max(CLEAR_GAP*scale,2*uncertainty) and candidates[1][0]>candidates[0][0]*1.6):
            changed=session.set_collected(candidates[0][1].id,True)
            return result('marked' if changed else 'ignored','saved' if changed else 'unchanged')
        self.context=self.scope(session)
        self.pending=(now+10,tuple(item.id for _,item in candidates if not session.is_collected(item.id)))
        session.notice='AutoMark beta: há baús próximos. Use o atalho de coleta para escolher.'
        return result('ambiguous','multiple_nearby_chests')

    def choices(self,session,now):
        if self.pending is None:return []
        deadline,ids=self.pending
        if now>deadline or self.context!=self.scope(session):self.reset();return []
        return [item for identifier in ids if (item:=session.item_by_id(identifier)) is not None
                and not session.is_collected(identifier)]
