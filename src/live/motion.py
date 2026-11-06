"""Track current terrain between absolute registrations, without stale pin positions."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import math

import cv2
import numpy as np

from src.live.vision import Observation, ScreenRecognizer, gray, template_visible


def terrain_mask(frame: np.ndarray, observation: Observation) -> np.ndarray:
    h,w=frame.shape[:2]
    mask=np.zeros((h,w),np.uint8)
    if observation.surface=="map":
        mask[int(.10*h):int(.88*h),int(.22*w):int(.78*w)]=255
    elif observation.circle:
        x,y,r=observation.circle
        cv2.circle(mask,(round(x),round(y)),max(1,round(r-10)),255,-1)
        cv2.circle(mask,(round(x),round(y)),max(10,round(r*.20)),0,-1)
    return mask


def follow(previous: np.ndarray, current: np.ndarray, observation: Observation,
           stamp: float) -> Observation | None:
    """Forward/backward LK and spatially distributed RANSAC, no input prediction."""
    if previous.shape!=current.shape or observation.world_to_screen is None:
        return None
    mask=terrain_mask(previous,observation)
    points=cv2.goodFeaturesToTrack(previous,maxCorners=180,qualityLevel=.015,minDistance=5,mask=mask)
    if points is None or len(points)<16:
        return None
    target,status,error=cv2.calcOpticalFlowPyrLK(previous,current,points,None,
                                                winSize=(21,21),maxLevel=3)
    if target is None or status is None:
        return None
    back,back_status,_=cv2.calcOpticalFlowPyrLK(current,previous,target,None,
                                             winSize=(21,21),maxLevel=3)
    if back is None:
        return None
    good=(status.ravel()>0)&(back_status.ravel()>0)&(error.ravel()<25)
    good&=np.linalg.norm(points[:,0]-back[:,0],axis=1)<1.0
    source=points[good,0];destination=target[good,0]
    if len(source)<16 or len(source)<len(points)*.55:
        return None
    delta,inliers=cv2.estimateAffinePartial2D(source,destination,method=cv2.RANSAC,
                                             ransacReprojThreshold=1.5,maxIters=1000)
    if delta is None or inliers is None or not np.isfinite(delta).all():
        return None
    accepted=inliers.ravel().astype(bool)
    if accepted.sum()<14 or accepted.mean()<.8:
        return None
    if cv2.contourArea(cv2.convexHull(source[accepted])) < cv2.countNonZero(mask)*.10:
        return None
    scale=float(np.linalg.norm(delta[:,0]))
    rotation=math.degrees(math.atan2(delta[1,0],delta[0,0]))
    if not .75<scale<1.33 or abs(rotation)>25:
        return None
    predicted=cv2.transform(source[accepted].reshape(1,-1,2),delta)[0]
    residual=float(np.percentile(np.linalg.norm(predicted-destination[accepted],axis=1),95))
    if residual>1.5:
        return None
    matrix=delta@np.vstack([observation.world_to_screen,[0,0,1]])
    player=None
    if observation.circle:
        x,y,_=observation.circle
        p=cv2.invertAffineTransform(matrix)@np.array([x,y,1])
        player=(float(p[0]),float(p[1]))
    return Observation(observation.surface,stamp,matrix,min(observation.confidence,.95),
                       residual,observation.circle,player,observation.reason,observation.map_id,observation.layer_id)


class MotionRecognizer:
    """One absolute matcher in the background, fast frame-to-frame foreground tracking.

    Anchor age is bounded even when optical tracking succeeds. Recovered absolute
    results are reprojected to the latest frame before they can be displayed.
    """
    def __init__(self, recognizer: ScreenRecognizer):
        self.recognizer=recognizer
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="AbsoluteRegistration")
        self.future=None
        self.anchor_frame=None
        self.anchor_stamp=0.0
        self.last_submit=-math.inf
        self.last_absolute=-math.inf
        self.previous=None
        self.current=Observation("hidden",0)

    def reset(self):
        self.previous=None
        self.current=Observation("hidden",0)
        self.last_absolute=-math.inf
        # A result captured before losing focus/geometry must never revive pins.
        if self.future:
            self.future.cancel()
            self.future=None
        self.anchor_frame=None

    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)

    def observe(self, frame: np.ndarray | None, stamp: float) -> Observation:
        if frame is None or frame.size==0:
            self.reset()
            return Observation("hidden",stamp,reason="Captura indisponível")
        image=gray(frame)
        pack=self.recognizer.pack
        is_map=template_visible(frame,pack.map_ui,pack.map_ui_roi)
        is_gameplay=not is_map and template_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi)
        surface="map" if is_map else "minimap" if is_gameplay else "hidden"
        if surface=="hidden":
            self.reset()
            return Observation("hidden",stamp,reason="Menu, carregamento ou tela não reconhecida")
        updated=None
        if self.previous is not None and self.current.surface==surface and stamp-self.last_absolute<=1.5:
            updated=follow(self.previous,image,self.current,stamp)
        if self.future is not None and self.future.done():
            try:
                absolute=self.future.result()
                if absolute.surface==surface and stamp-self.anchor_stamp<=1.5:
                    rebased=follow(self.anchor_frame,image,absolute,stamp)
                    if rebased is not None:
                        updated=rebased
                        self.last_absolute=self.anchor_stamp
            finally:
                self.future=None
                self.anchor_frame=None
        # If flow fails, stop drawing immediately; reacquire without waiting for
        # the usual anchor interval. Do not retain the old screen transform.
        if self.future is None and (updated is None or stamp-self.last_submit>=.65):
            self.anchor_frame=image.copy()
            self.anchor_stamp=stamp
            self.last_submit=stamp
            self.future=self.pool.submit(self.recognizer.observe,frame.copy(),stamp)
        self.previous=image
        self.current=updated or Observation("hidden",stamp,reason="Localizando no mapa selecionado…")
        return self.current
