"""Track current terrain between absolute registrations, without stale pin positions."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import math
import logging

import cv2
import numpy as np

from src.live.vision import Observation, ScreenRecognizer, gray, template_visible, detect_circle, foreground_ui_visible
from src.live.facing import FacingTracker

logger=logging.getLogger(__name__)


def comparison_points(observation, width, height):
    """Judge corrections only inside the surface actually recognized."""
    if observation.surface=='minimap' and observation.circle:
        x,y,radius=observation.circle
        r=max(1,radius-12)*.7
        return np.array([[x,y,1],[x-r,y,1],[x+r,y,1],[x,y-r,1],[x,y+r,1]])
    return np.array([[width*.3,height*.3,1],[width*.5,height*.5,1],[width*.7,height*.7,1]])


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
    bounds=cv2.findNonZero(mask)
    if bounds is None: return None
    x,y,w,h=cv2.boundingRect(bounds)
    # LK builds pyramids for its entire input. Crop to terrain, never the whole HUD.
    before=previous[y:y+h,x:x+w]
    after=current[y:y+h,x:x+w]
    mask=mask[y:y+h,x:x+w]
    factor=.5 if observation.surface=='map' and w>600 else 1.
    if factor!=1:
        before=cv2.resize(before,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA)
        after=cv2.resize(after,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA)
        mask=cv2.resize(mask,(before.shape[1],before.shape[0]),interpolation=cv2.INTER_NEAREST)
    points=cv2.goodFeaturesToTrack(before,maxCorners=180,qualityLevel=.015,minDistance=5*factor,mask=mask)
    if points is None or len(points)<16:
        return None
    target,status,error=cv2.calcOpticalFlowPyrLK(before,after,points,None,
                                                winSize=(21,21),maxLevel=3)
    if target is None or status is None:
        return None
    back,back_status,_=cv2.calcOpticalFlowPyrLK(after,before,target,None,
                                             winSize=(21,21),maxLevel=3)
    if back is None:
        return None
    good=(status.ravel()>0)&(back_status.ravel()>0)&(error.ravel()<25)
    good&=np.linalg.norm(points[:,0]-back[:,0],axis=1)<factor
    source=points[good,0]/factor+np.array([x,y],dtype=np.float32)
    destination=target[good,0]/factor+np.array([x,y],dtype=np.float32)
    if len(source)<16 or len(source)<len(points)*.55:
        return None
    delta,inliers=cv2.estimateAffinePartial2D(source,destination,method=cv2.RANSAC,
                                             ransacReprojThreshold=1.5,maxIters=1000)
    if delta is None or inliers is None or not np.isfinite(delta).all():
        return None
    accepted=inliers.ravel().astype(bool)
    if accepted.sum()<14 or accepted.mean()<.8:
        return None
    if cv2.contourArea(cv2.convexHull(source[accepted])) < cv2.countNonZero(mask)/factor**2*.10:
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
        self.anchor_motion=None
        self.previous_surface='hidden'
        self.circle=None
        self.tracking_status=None
        self.verified_frame=None
        self.verified_observation=None
        self.absolute_reason='pending'
        self.facing=FacingTracker()

    def reset(self):
        self.previous=None
        self.current=Observation("hidden",0)
        self.last_absolute=-math.inf
        # A result captured before losing focus/geometry must never revive pins.
        if self.future:
            self.future.cancel()
            self.future=None
        self.anchor_frame=None
        self.anchor_motion=None
        self.previous_surface='hidden'
        self.circle=None
        self.verified_frame=None
        self.verified_observation=None
        self.facing.reset()

    def close(self,wait=False):
        self.pool.shutdown(wait=wait,cancel_futures=True)

    def observe(self, frame: np.ndarray | None, stamp: float) -> Observation:
        if frame is None or frame.size==0:
            self.reset()
            return Observation("hidden",stamp,reason="Captura indisponível")
        image=gray(frame)
        pack=self.recognizer.pack
        is_map=template_visible(frame,pack.map_ui,pack.map_ui_roi)
        is_gameplay=not is_map and (template_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi) or
                                   foreground_ui_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi))
        surface="map" if is_map else "minimap" if is_gameplay else "hidden"
        if surface=="hidden":
            self.reset()
            return Observation("hidden",stamp,reason="Menu, carregamento ou tela não reconhecida")
        if surface=='minimap':
            if self.circle is None or self.previous_surface!='minimap':
                self.circle=detect_circle(frame)
        else:self.circle=None
        updated=None
        discontinuity=False
        if self.previous is not None and self.current.surface==surface and stamp-self.last_absolute<=1.5:
            updated=follow(self.previous,image,self.current,stamp)
        if (updated is None and surface=='minimap' and self.verified_frame is not None
                and self.verified_observation is not None and stamp-self.last_absolute<=1.5
                and 0<stamp-self.verified_observation.captured_at<=.25):
            # A brief occlusion can defeat one LK step. Re-register against the
            # last verified image; never reuse its old screen coordinates.
            updated=follow(self.verified_frame,image,self.verified_observation,stamp)
        if self.future is not None and self.anchor_motion is not None:
            step=None
            if updated is not None and self.current.world_to_screen is not None:
                step=updated.world_to_screen@np.vstack([
                    cv2.invertAffineTransform(self.current.world_to_screen),[0,0,1]])
            elif (self.previous is not None and self.previous_surface==surface and
                  (surface=='map' or self.circle is not None)):
                # Bootstrap tracking while the first absolute result is still pending.
                identity=Observation(surface,stamp,np.eye(2,3),.95,circle=self.circle)
                relative=follow(self.previous,image,identity,stamp)
                if relative is not None: step=relative.world_to_screen
            if step is None:
                self.anchor_motion=None
            else:
                self.anchor_motion=np.vstack([step,[0,0,1]])@self.anchor_motion
        if self.future is not None and self.future.done():
            try:
                absolute=self.future.result()
                self.absolute_reason=absolute.reason
                if absolute.surface==surface and stamp-self.anchor_stamp<=1.5:
                    if self.anchor_motion is not None:
                        matrix=(self.anchor_motion@np.vstack([absolute.world_to_screen,[0,0,1]]))[:2]
                        circle=self.circle if surface=='minimap' and self.circle else absolute.circle
                        player=absolute.player
                        if circle:
                            cx,cy,_=circle
                            player=tuple(cv2.invertAffineTransform(matrix)@np.array([cx,cy,1]))
                        rebased=replace(absolute,captured_at=stamp,world_to_screen=matrix,player=player,circle=circle)
                    else:
                        rebased=follow(self.anchor_frame,image,absolute,stamp)
                    if rebased is not None:
                        if (updated is not None and updated.map_id==rebased.map_id
                                and updated.layer_id==rebased.layer_id):
                            # Compare both estimates on this capture, not the old anchor.
                            relative=rebased.world_to_screen@np.vstack([
                                cv2.invertAffineTransform(updated.world_to_screen),[0,0,1]])
                            h,w=image.shape[:2]
                            probes=comparison_points(rebased,w,h)
                            discrepancy=float(np.max(np.linalg.norm(
                                probes@relative.T-probes[:,:2],axis=1)))
                            discontinuity=discrepancy>24
                            if discrepancy<=3:
                                rebased=replace(rebased,world_to_screen=(
                                    rebased.world_to_screen+updated.world_to_screen)/2)
                        updated=rebased
                        self.last_absolute=self.anchor_stamp
                        if surface=='minimap':self.circle=rebased.circle
            finally:
                self.future=None
                self.anchor_frame=None
                self.anchor_motion=None
        # If flow fails, stop drawing immediately; reacquire without waiting for
        # the usual anchor interval. Do not retain the old screen transform.
        interval=.25 if surface=='minimap' and stamp-self.last_absolute>=.75 else .65
        if self.future is None and (updated is None or stamp-self.last_submit>=interval):
            self.anchor_frame=image.copy()
            self.anchor_stamp=stamp
            self.last_submit=stamp
            self.future=self.pool.submit(self.recognizer.observe,frame.copy(),stamp)
            self.anchor_motion=np.eye(3)
        self.previous=image
        self.previous_surface=surface
        if updated is not None and surface=='minimap':
            if discontinuity:self.facing.reset()
            heading,heading_confidence=self.facing.update(frame,updated.circle,stamp,updated.world_to_screen)
            updated=replace(updated,heading_screen=heading,heading_confidence=heading_confidence)
        else:self.facing.reset()
        self.current=updated or Observation("hidden",stamp,reason="Localizando no mapa selecionado…")
        if updated is not None and surface=='minimap':
            self.verified_frame=image
            self.verified_observation=updated
        status=('correction' if discontinuity else 'tracking' if updated else
                'anchor_expired' if stamp-self.last_absolute>1.5 else 'flow_lost')
        if status!=self.tracking_status:
            self.tracking_status=status
            logger.info('Tracking surface=%s state=%s anchor_age=%.3f pending_age=%.3f absolute=%s',
                        surface,status,stamp-self.last_absolute,
                        stamp-self.anchor_stamp if self.future else 0,self.absolute_reason)
        if discontinuity:
            # Keep the recovered anchor internally; never animate across a large correction.
            return Observation("hidden",stamp,reason="Recuperando alinhamento…")
        return self.current
