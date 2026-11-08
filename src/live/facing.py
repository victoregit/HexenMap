"""View direction from the native minimap V-shaped field of view."""
import math
import cv2
import numpy as np


def pointer_shape(frame,circle):
    if circle is None or frame is None or frame.ndim!=3:return None
    x,y,r=circle;h,w=frame.shape[:2];margin=max(12,round(r*.27))
    left=max(0,round(x)-margin);top=max(0,round(y)-margin)
    crop=frame[top:min(h,round(y)+margin+1),left:min(w,round(x)+margin+1)]
    if crop.size==0:return None
    mask=cv2.inRange(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV),(80,100,160),(110,255,255))
    count,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
    candidates=[]
    for i in range(1,count):
        _,_,aw,ah,area=stats[i];px,py=centers[i]+[left,top]
        if (.015*r*r<area<.07*r*r and .5<aw/max(ah,1)<2
                and math.hypot(px-x,py-y)<max(5,r*.12)):
            candidates.append(i)
    if len(candidates)!=1:return None
    component=np.uint8(labels==candidates[0])*255
    return component,centers[candidates[0]]


def shape_facing(pointer):
    if pointer is None:return None,0.
    component,center=pointer
    contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour=max(contours,key=cv2.contourArea);perimeter=cv2.arcLength(contour,True)
    if perimeter<=0:return None,0.
    circularity=4*math.pi*cv2.contourArea(contour)/perimeter**2
    if circularity>.82:return None,0.
    hull=cv2.convexHull(contour)
    vertices=cv2.approxPolyDP(hull,perimeter*.045,True)[:,0].astype(float)
    if not 3<=len(vertices)<=5:return None,0.
    vectors=vertices-center;distances=np.linalg.norm(vectors,axis=1)
    order=np.argsort(distances)
    tip=None
    indices=cv2.convexHull(contour,returnPoints=False)
    try:defects=cv2.convexityDefects(contour,indices) if len(contour)>3 else None
    except cv2.error:defects=None
    if defects is not None:
        start,end,_,depth=max(defects.reshape(-1,4),key=lambda d:d[3])
        if depth>=256:
            a=contour[start,0].astype(float);b=contour[end,0].astype(float);edge=b-a
            points=hull.reshape(-1,2).astype(float)
            offsets=np.abs((points[:,0]-a[0])*edge[1]-(points[:,1]-a[1])*edge[0])
            tip=points[np.argmax(offsets)]
    if tip is None:
        # A triangular glyph without a rear notch requires a distinct long tip.
        if distances[order[-1]]-distances[order[-2]]<1.:return None,0.
        tip=vertices[order[-1]]
    dx,dy=tip-center
    heading=math.degrees(math.atan2(float(dx),-float(dy)))%360
    confidence=.85
    return heading,confidence


def _polar(image,circle,left=0,top=0):
    x,y,r=circle
    angles=np.deg2rad(np.arange(360,dtype=np.float32))
    radii=np.linspace(r*.30,r*.80,32,dtype=np.float32)
    mx=(x-left+np.sin(angles)[None,:]*radii[:,None]).astype(np.float32)
    my=(y-top-np.cos(angles)[None,:]*radii[:,None]).astype(np.float32)
    return cv2.remap(image,mx,my,cv2.INTER_LINEAR)


def white_blend(inside,outside):
    """Fit the white HUD blend in RGB, retaining weak edges on bright snow.

    Regularization models quantization noise; fully white terrain carries no signal.
    """
    headroom=255-outside
    delta=inside-outside
    gain=np.sum(headroom*delta,axis=2)/(np.sum(headroom*headroom,axis=2)+6.75)
    residual=np.sqrt(np.mean((delta-gain[:,:,None]*headroom)**2,axis=2))
    valid=(residual<2.5)&(gain>.055)&(gain<.35)&(np.mean(delta,axis=2)>.65)
    return gain,valid


def view_cone_facing(frame,circle):
    """Conservative single-frame reading of both white field-of-view edges."""
    if pointer_shape(frame,circle) is None:return None,0.
    x,y,r=circle
    if not np.isfinite((x,y,r)).all() or r<20:return None,0.
    if x-r*.81<0 or y-r*.81<0 or x+r*.81>=frame.shape[1] or y+r*.81>=frame.shape[0]:
        return None,0.
    left=max(0,round(x-r*.9));top=max(0,round(y-r*.9))
    crop=frame[top:min(frame.shape[0],round(y+r*.9)+1),left:min(frame.shape[1],round(x+r*.9)+1)]
    polar=_polar(crop.astype(np.float32),circle,left,top)
    positive=np.roll(polar,-4,axis=1);negative=np.roll(polar,4,axis=1)
    def edge(inside,outside):
        strength,valid=white_blend(inside,outside)
        alpha=(inside-outside)/np.maximum(255-outside,25)
        ordinary=np.median(alpha,axis=2)
        dark=np.mean(255-outside,axis=2)>=25
        strength=np.where(dark,ordinary,strength)
        valid=np.where(dark,(np.std(alpha,axis=2)<.035)&(ordinary>.055)&(ordinary<.35),valid)
        return np.mean(np.where(valid,strength,0),axis=0),np.mean(valid,axis=0)
    entering,es=edge(positive,negative);leaving,ls=edge(negative,positive)
    scores=[]
    for half in range(40,51):
        a=np.roll(entering,half);b=np.roll(leaving,-half)
        support=np.minimum(np.roll(es,half),np.roll(ls,-half))
        scores.append(np.where(support>=.5,2*np.minimum(a,b)-.25*np.abs(a-b),0))
    score=np.max(scores,axis=0);best=int(np.argmax(score))
    offsets=(np.arange(360)-best+180)%360-180
    if score[best]<.12 or score[best]-max(score[np.abs(offsets)>30])<.025:return None,0.
    return float(best),.80


def _profile_facing(profile):
    def mean_window(half):
        return np.convolve(np.r_[profile[-half:],profile,profile[:half]],
                           np.ones(2*half+1)/(2*half+1),mode='valid')
    inside=mean_window(45)
    outside=(profile.sum()-mean_window(60)*121)/239
    score=inside-outside;best=int(np.argmax(score))
    offsets=(np.arange(360)-best+180)%360-180
    if (score[best]<.055 or score[best]-max(score[np.abs(offsets)>35])<.025
            or np.mean(profile[np.abs(offsets)<=40]>.04)<.70):return None,0.
    return float(best),.88


def player_facing(frame,circle):
    # Compatibility name for the observation contract: this is the V, not the arrow.
    return view_cone_facing(frame,circle)


class FacingTracker:
    """Short-arc smoothing and confirmation of sudden view-sector changes."""
    def __init__(self):self.reset()

    def reset(self):
        self.heading=None;self.stamp=None;self.confirmed=-math.inf;self.pending=None
        self.background=None;self.background_matrix=None;self.background_origin=None

    def _measure(self,frame,circle,transform):
        x,y,r=circle;h,w=frame.shape[:2]
        left=max(0,round(x-r*.9));top=max(0,round(y-r*.9))
        crop=frame[top:min(h,round(y+r*.9)+1),left:min(w,round(x+r*.9)+1)].astype(np.float32)
        matrix=np.vstack((transform,[0.,0.,1.])) if transform is not None else None
        background=self.background
        if background is not None:
            warp=np.eye(3)
            if matrix is not None and self.background_matrix is not None:
                try:warp=matrix@np.linalg.inv(self.background_matrix)
                except np.linalg.LinAlgError:background=None
            if background is not None:
                shift=warp[:2,:2]@np.asarray(self.background_origin)+warp[:2,2]-[left,top]
                warp[:2,2]=shift
                # Discontinuities must not teach the view detector the wrong terrain.
                if (not np.isfinite(warp).all() or np.linalg.norm(shift)>r*.3
                        or np.linalg.norm(warp[:2,:2]-np.eye(2))>.25):background=None
                else:background=cv2.warpAffine(background,warp[:2],(crop.shape[1],crop.shape[0]),
                                               flags=cv2.INTER_LINEAR,borderValue=(255,255,255))
        self.background=crop.copy() if background is None else np.minimum(background,crop)
        self.background_matrix=matrix;self.background_origin=(left,top)
        if background is not None:
            headroom=255-self.background
            ordinary=np.clip((crop-self.background)/np.maximum(headroom,25),0,.5)
            strength,valid=white_blend(crop,self.background)
            bright=np.mean(headroom,axis=2)<25
            excess=np.where(bright[:,:,None],np.where(valid,strength,0)[:,:,None],ordinary).astype(np.float32)
            profile=np.median(_polar(excess,circle,left,top),axis=(0,2))
            direction,confidence=_profile_facing(profile)
            if direction is not None:return direction,confidence
        return view_cone_facing(frame,circle)

    def update(self,frame,circle,stamp,transform=None):
        if pointer_shape(frame,circle) is None:
            self.reset();return None,0.
        if self.stamp is not None and (stamp<self.stamp or stamp-self.stamp>.25):self.reset()
        dt=stamp-self.stamp if self.stamp is not None else 0.
        self.stamp=stamp
        raw,confidence=self._measure(frame,circle,transform)
        if raw is None:
            return (self.heading,.72) if self.heading is not None and 0<=stamp-self.confirmed<=.18 else (None,0.)
        if self.heading is None:
            self.heading=raw;self.confirmed=stamp;return raw,confidence
        delta=(raw-self.heading+180)%360-180
        if abs(delta)>70:
            pending=self.pending
            if pending and 0<=stamp-pending[1]<=.18 and abs((raw-pending[0]+180)%360-180)<20:
                self.heading=raw;self.confirmed=stamp;self.pending=None
                return self.heading,confidence
            self.pending=(raw,stamp)
            return (self.heading,.72) if 0<=stamp-self.confirmed<=.18 else (None,0.)
        self.pending=None
        alpha=1-math.exp(-max(0,dt)/.065)
        self.heading=(self.heading+alpha*delta)%360;self.confirmed=stamp
        return self.heading,confidence
