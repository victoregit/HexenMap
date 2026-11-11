"""Bounded, in-memory minimap evidence for reconstruction at the opening instant."""
from src.live.i18n import tr as _tr
from collections import deque
from dataclasses import dataclass,replace
import math
import cv2
import numpy as np
from src.live.motion import follow


@dataclass(frozen=True)
class MiniFrame:
    stamp: float
    pixels: object
    origin: tuple
    circle: tuple


def minimap_frame(frame,circle,stamp):
    if frame is None or circle is None:return None
    x,y,r=circle;h,w=frame.shape[:2]
    left=max(0,int(x-r-2));top=max(0,int(y-r-2))
    right=min(w,math.ceil(x+r+3));bottom=min(h,math.ceil(y+r+3))
    image=frame[top:bottom,left:right]
    if image.size==0:return None
    image=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
    return MiniFrame(stamp,image.copy(),(left,top),(x-left,y-top,r))


class OpeningRecovery:
    MAX_BYTES=16*1024**2
    def __init__(self):self.frames=deque();self.bytes=0
    def clear(self):self.frames.clear();self.bytes=0
    def add(self,frame):
        if frame is None:return
        if self.frames:
            previous=self.frames[-1]
            if (max(abs(a-b) for a,b in zip(frame.pixels.shape,previous.pixels.shape))>6
                    or frame.stamp<previous.stamp):self.clear()
        if frame.pixels.nbytes>self.MAX_BYTES:return
        self.frames.append(frame);self.bytes+=frame.pixels.nbytes
        while self.frames and (self.bytes>self.MAX_BYTES or frame.stamp-self.frames[0].stamp>3):
            self.bytes-=self.frames.popleft().pixels.nbytes
    def recover(self,opened,anchor,observation,now):
        if anchor is None or not observation.fresh(now) or observation.surface!='minimap' or not 0<=now-opened<=3:return None
        if abs(anchor.stamp-observation.captured_at)>1e-5:return None
        target=next((f for f in self.frames if abs(f.stamp-opened)<1e-5),None)
        if target is None:return None
        reverse=anchor.stamp>=opened
        steps=[f for f in self.frames if (opened<=f.stamp<anchor.stamp if reverse else anchor.stamp<f.stamp<=opened)]
        steps.sort(key=lambda f:f.stamp,reverse=reverse)
        # The HUD and tracker may measure its rim a pixel apart. Register their
        # actual shared pixels; never assume separately cropped arrays coincide.
        samples=[anchor,*steps]
        left=max(f.origin[0] for f in samples);top=max(f.origin[1] for f in samples)
        right=min(f.origin[0]+f.pixels.shape[1] for f in samples)
        bottom=min(f.origin[1]+f.pixels.shape[0] for f in samples)
        if right-left<min(f.pixels.shape[1] for f in samples)*.8 or bottom-top<min(f.pixels.shape[0] for f in samples)*.8:return None
        def shared(sample):
            x,y=sample.origin
            circle=(sample.circle[0]+x-left,sample.circle[1]+y-top,sample.circle[2])
            return MiniFrame(sample.stamp,sample.pixels[top-y:bottom-y,left-x:right-x],(left,top),circle)
        anchor=shared(anchor);steps=[shared(f) for f in steps]
        matrix=observation.world_to_screen.copy();matrix[:,2]-=anchor.origin
        current=replace(observation,world_to_screen=matrix,circle=anchor.circle)
        previous=anchor;error=observation.error_px
        for sample in steps:
            if abs(previous.stamp-sample.stamp)>.3 or previous.origin!=sample.origin:return None
            # Spatial solve is reversed in time when necessary, never extrapolated.
            recovered=follow(previous.pixels,sample.pixels,current,sample.stamp)
            if recovered is None:return None
            error+=recovered.error_px
            if error>3:return None
            current=recovered;previous=sample
        if abs(previous.stamp-opened)>1e-5:return None
        matrix=current.world_to_screen.copy();matrix[:,2]+=anchor.origin
        circle=tuple(np.asarray(target.circle)+np.array([*target.origin,0]))
        center_error=float(np.linalg.norm(np.asarray(circle[:2])-np.asarray(observation.circle[:2])))
        error+=center_error
        if error>3:return None
        player=tuple(cv2.invertAffineTransform(matrix)@np.array([*circle[:2],1.]))
        return replace(current,world_to_screen=matrix,circle=circle,player=player,captured_at=opened,
                       position_uncertainty_px=error,reason=_tr('Abertura reconstruída por movimento verificado'))
