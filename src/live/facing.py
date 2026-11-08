"""Current character facing from the native cyan minimap pointer, not camera yaw."""
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


def player_facing(frame,circle):
    return shape_facing(pointer_shape(frame,circle))


class FacingTracker:
    """Short-arc smoothing and confirmation of sudden glyph interpretation changes."""
    def __init__(self):self.reset()

    def reset(self):
        self.heading=None;self.stamp=None;self.confirmed=-math.inf;self.pending=None

    def update(self,frame,circle,stamp):
        pointer=pointer_shape(frame,circle);raw,confidence=shape_facing(pointer)
        if pointer is None:
            self.reset();return None,0.
        if self.stamp is not None and (stamp<self.stamp or stamp-self.stamp>.25):self.reset()
        dt=stamp-self.stamp if self.stamp is not None else 0.
        self.stamp=stamp
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
