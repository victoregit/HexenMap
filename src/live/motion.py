"""Track current terrain between absolute registrations, without stale pin positions."""
from __future__ import annotations

from src.live.i18n import tr as _tr
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from contextvars import ContextVar
from dataclasses import replace
import math
import logging

import cv2
import numpy as np

from src.live.vision import Observation, ScreenRecognizer, gray, template_visible, detect_circle, foreground_ui_visible,steady_circle
from src.live.minimap_glyph import pointer_shape
from src.live.gameplay import GameplayGate

logger=logging.getLogger(__name__)
_flow_diagnostic=ContextVar('flow_diagnostic',default=None)


def _flow_rejected(reason,**values):
    diagnostic=_flow_diagnostic.get()
    if diagnostic is not None:diagnostic.update(reason=reason,**values)
    return None


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
        return _flow_rejected('geometry_or_pose')
    mask=terrain_mask(previous,observation)
    bounds=cv2.findNonZero(mask)
    if bounds is None:return _flow_rejected('empty_terrain_mask')
    x,y,w,h=cv2.boundingRect(bounds)
    # LK builds pyramids for its entire input. Crop to terrain, never the whole HUD.
    before=previous[y:y+h,x:x+w]
    after=current[y:y+h,x:x+w]
    mask=mask[y:y+h,x:x+w]
    if float(before.std())<25:
        contrast=cv2.createCLAHE(clipLimit=2.,tileGridSize=(4,4))
        before=contrast.apply(before);after=contrast.apply(after)
    factor=.5 if observation.surface=='map' and w>600 else 1.
    if factor!=1:
        before=cv2.resize(before,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA)
        after=cv2.resize(after,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA)
        mask=cv2.resize(mask,(before.shape[1],before.shape[0]),interpolation=cv2.INTER_NEAREST)
    points=cv2.goodFeaturesToTrack(before,maxCorners=180,qualityLevel=.015,minDistance=5*factor,mask=mask)
    if points is None or len(points)<16:
        return _flow_rejected('features',features=0 if points is None else len(points))
    target,status,error=cv2.calcOpticalFlowPyrLK(before,after,points,None,
                                                winSize=(21,21),maxLevel=3)
    if target is None or status is None:
        return _flow_rejected('forward_lk')
    back,back_status,_=cv2.calcOpticalFlowPyrLK(after,before,target,None,
                                             winSize=(21,21),maxLevel=3)
    if back is None:
        return _flow_rejected('backward_lk')
    good=(status.ravel()>0)&(back_status.ravel()>0)&(error.ravel()<25)
    good&=np.linalg.norm(points[:,0]-back[:,0],axis=1)<factor
    source=points[good,0]/factor+np.array([x,y],dtype=np.float32)
    destination=target[good,0]/factor+np.array([x,y],dtype=np.float32)
    if len(source)<16 or len(source)<len(points)*.55:
        return _flow_rejected('forward_backward_consistency',features=len(points),surviving=len(source))
    delta,inliers=cv2.estimateAffinePartial2D(source,destination,method=cv2.RANSAC,
                                             ransacReprojThreshold=1.5,maxIters=1000)
    if delta is None or inliers is None or not np.isfinite(delta).all():
        return _flow_rejected('ransac_model')
    accepted=inliers.ravel().astype(bool)
    if accepted.sum()<14 or accepted.mean()<.8:
        return _flow_rejected('ransac_inliers',inliers=int(accepted.sum()),ratio=float(accepted.mean()))
    coverage=cv2.contourArea(cv2.convexHull(source[accepted]))/(cv2.countNonZero(mask)/factor**2)
    if coverage<.10:
        return _flow_rejected('spatial_coverage',coverage=coverage)
    scale=float(np.linalg.norm(delta[:,0]))
    rotation=math.degrees(math.atan2(delta[1,0],delta[0,0]))
    if not .75<scale<1.33 or abs(rotation)>25:
        return _flow_rejected('motion_bounds',scale=scale,rotation=rotation)
    predicted=cv2.transform(source[accepted].reshape(1,-1,2),delta)[0]
    residual=float(np.percentile(np.linalg.norm(predicted-destination[accepted],axis=1),95))
    if residual>1.5:
        return _flow_rejected('residual',residual=residual)
    uncertainty=math.hypot(observation.position_uncertainty_px,residual)
    if uncertainty>2.5:return _flow_rejected('uncertainty',uncertainty=uncertainty,residual=residual,previous_uncertainty=observation.position_uncertainty_px)
    matrix=delta@np.vstack([observation.world_to_screen,[0,0,1]])
    player=None
    if observation.circle:
        x,y,_=observation.circle
        p=cv2.invertAffineTransform(matrix)@np.array([x,y,1])
        player=(float(p[0]),float(p[1]))
    diagnostic=_flow_diagnostic.get()
    if diagnostic is not None:diagnostic.update(reason='accepted',features=len(points),inliers=int(accepted.sum()),coverage=coverage,residual=residual,uncertainty=uncertainty)
    return replace(observation,captured_at=stamp,world_to_screen=matrix,confidence=min(observation.confidence,.95),
                   error_px=residual,player=player,
                   position_uncertainty_px=uncertainty)


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
        self.previous_observation=None
        self.current=Observation("hidden",0)
        self.anchor_motion=None
        self.previous_surface='hidden'
        self.circle=None
        self.tracking_status=None
        self.verified_frame=None
        self.verified_observation=None
        self.last_diagnostic={}
        self.flow_attempts=[]
        self.absolute_status='pending'
        self.absolute_reason='pending'
        self.gameplay=GameplayGate();self.continuity_id=0
        self.recent=deque(maxlen=3)
        self.circle_checked=-math.inf
        self.circle_hint=None;self.image_shape=None
        packs=getattr(recognizer,'packs',(recognizer.pack,))
        self.expected_scopes={(p.map_id,p.layer_id) for p in packs
                              if getattr(p,'map_id',None) is not None and getattr(p,'layer_id',None) is not None}

    def _follow(self,previous,current,observation,stamp):
        diagnostic={'source_age_s':round(stamp-observation.captured_at,4)}
        token=_flow_diagnostic.set(diagnostic)
        try:return follow(previous,current,observation,stamp)
        finally:
            _flow_diagnostic.reset(token)
            self.flow_attempts.append(diagnostic)

    def diagnostics(self):
        return dict(self.last_diagnostic)

    def reset(self):
        self.continuity_id+=1;self.gameplay.reset()
        self.recent.clear()
        self.circle_checked=-math.inf
        self.previous=None
        self.previous_observation=None
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

    def close(self,wait=False):
        self.pool.shutdown(wait=wait,cancel_futures=True)

    def observe(self, frame: np.ndarray | None, stamp: float) -> Observation:
        if frame is None or frame.size==0:
            self.reset()
            self.last_diagnostic={'surface':'hidden','state':'capture_unavailable','published':False,'flow':[]}
            return Observation("hidden",stamp,reason=_tr("Captura indisponível"),continuity_id=self.continuity_id)
        self.flow_attempts=[]
        self.absolute_status='pending' if self.future is not None else 'idle'
        image=gray(frame)
        if frame.shape!=self.image_shape:
            if self.image_shape is not None:self.reset()
            self.circle_hint=None;self.image_shape=frame.shape
        pack=self.recognizer.pack
        is_map=template_visible(frame,pack.map_ui,pack.map_ui_roi)
        is_gameplay=not is_map and (template_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi) or
                                   foreground_ui_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi))
        if not is_map and not is_gameplay and frame.ndim==3:
            hint=self.circle or self.circle_hint
            if hint is not None and pointer_shape(frame,hint) is not None:
                self.circle=hint;is_gameplay=True
            elif hint is None and stamp-self.circle_checked>=1:
                self.circle_checked=stamp
                detected=detect_circle(frame)
                if detected is not None:
                    self.circle=detected;self.circle_hint=detected;is_gameplay=True
        # A single missing HUD glyph is tolerated only with a current player pointer.
        circle=self.circle
        tentative=None
        if circle is not None and frame.ndim==3:
            if (not is_map and not is_gameplay and 0<=stamp-self.gameplay.confirmed<=.35
                    and self.previous is not None and self.current.surface=='minimap'):
                tentative=self._follow(self.previous,image,self.current,stamp)
            is_gameplay=self.gameplay.accept(stamp,map_open=is_map,hud=is_gameplay,
                                             pointer=is_gameplay or tentative is not None or pointer_shape(frame,circle) is not None)
        elif is_gameplay:self.gameplay.confirmed=stamp
        surface="map" if is_map else "minimap" if is_gameplay else "hidden"
        if surface=="hidden":
            self.reset()
            self.last_diagnostic={'surface':'hidden','state':'hud_not_recognized','published':False,'flow':[],
                                  'hud_visible':bool(is_gameplay),'map_visible':bool(is_map)}
            return Observation("hidden",stamp,reason=_tr("Menu, carregamento ou tela não reconhecida"),continuity_id=self.continuity_id)
        if surface=='minimap':
            if self.circle is None or self.previous_surface!='minimap':
                self.circle=self.circle or detect_circle(frame)
            if self.circle is not None:self.circle_hint=self.circle
        else:self.circle=None
        updated=tentative
        discontinuity=False
        # Continue solving the current image while its uncertainty remains
        # bounded. This is verified relative motion, never a held screen pose.
        internal=self.current if self.current.surface==surface else self.verified_observation
        previous_obs=self.current if self.current.surface==surface else self.previous_observation
        age_limit=5. if (surface=='minimap' and internal is not None and internal.confidence>=.9
                         and internal.position_uncertainty_px<=2.) else 1.5
        if (updated is None and self.previous is not None and previous_obs is not None
                and previous_obs.surface==surface and stamp-self.last_absolute<=age_limit):
            updated=self._follow(self.previous,image,previous_obs,stamp)
        if (updated is None and surface=='minimap' and self.verified_frame is not None
                and self.verified_observation is not None and stamp-self.last_absolute<=age_limit
                and 0<stamp-self.verified_observation.captured_at<=.25):
            # A brief occlusion can defeat one LK step. Re-register against the
            # last verified image; never reuse its old screen coordinates.
            updated=self._follow(self.verified_frame,image,self.verified_observation,stamp)
        if updated is None and surface=='minimap' and stamp-self.last_absolute<=age_limit:
            for recent_frame,recent_obs in reversed(self.recent):
                if 0<stamp-recent_obs.captured_at<=.5:
                    recovered=self._follow(recent_frame,image,recent_obs,stamp)
                    if recovered is not None:
                        probes=comparison_points(recovered,image.shape[1],image.shape[0])
                        relative=recovered.world_to_screen@np.vstack([cv2.invertAffineTransform(recent_obs.world_to_screen),[0,0,1]])
                        if np.max(np.linalg.norm(probes@relative.T-probes[:,:2],axis=1))<=max(12,recovered.circle[2]*.25):
                            updated=recovered;break
        if self.future is not None and self.anchor_motion is not None:
            step=None
            if updated is not None and previous_obs is not None and previous_obs.world_to_screen is not None:
                step=updated.world_to_screen@np.vstack([
                    cv2.invertAffineTransform(previous_obs.world_to_screen),[0,0,1]])
            elif (self.previous is not None and self.previous_surface==surface and
                  (surface=='map' or self.circle is not None)):
                # Bootstrap tracking while the first absolute result is still pending.
                identity=Observation(surface,stamp,np.eye(2,3),.95,circle=self.circle)
                relative=self._follow(self.previous,image,identity,stamp)
                if relative is not None: step=relative.world_to_screen
            if step is None:
                self.anchor_motion=None
            else:
                self.anchor_motion=np.vstack([step,[0,0,1]])@self.anchor_motion
        if self.future is not None and self.future.done():
            try:
                absolute=self.future.result()
                self.absolute_reason=absolute.reason
                self.absolute_status=('accepted_surface' if absolute.surface==surface else 'surface_mismatch')
                if stamp-self.anchor_stamp>1.5:self.absolute_status='expired'
                scope_valid=not self.expected_scopes or (absolute.map_id,absolute.layer_id) in self.expected_scopes
                if not scope_valid:self.absolute_status='context_mismatch'
                if absolute.surface==surface and stamp-self.anchor_stamp<=1.5 and scope_valid:
                    if self.anchor_motion is not None:
                        matrix=(self.anchor_motion@np.vstack([absolute.world_to_screen,[0,0,1]]))[:2]
                        circle=self.circle if surface=='minimap' and self.circle else absolute.circle
                        player=absolute.player
                        if circle:
                            cx,cy,_=circle
                            player=tuple(cv2.invertAffineTransform(matrix)@np.array([cx,cy,1]))
                        rebased=replace(absolute,captured_at=stamp,world_to_screen=matrix,player=player,circle=circle)
                    else:
                        rebased=self._follow(self.anchor_frame,image,absolute,stamp)
                    self.absolute_status='reprojected' if rebased is not None else 'reprojection_failed'
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
                                uncertainty=max(discrepancy,rebased.error_px)
                                if surface=='minimap':
                                    # The midpoint is only half the discrepancy
                                    # from the newly verified absolute estimate.
                                    # Include its existing error; never clamp a
                                    # genuinely uncertain result to the LK limit.
                                    uncertainty=max(rebased.position_uncertainty_px,rebased.error_px)+discrepancy/2
                                if surface!='minimap' or uncertainty<=2.5:
                                    blended=(rebased.world_to_screen+updated.world_to_screen)/2
                                    player=tuple(cv2.invertAffineTransform(blended)@np.array([*rebased.circle[:2],1])) if rebased.circle else rebased.player
                                    rebased=replace(rebased,world_to_screen=blended,player=player,
                                                    position_uncertainty_px=uncertainty)
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
        self.previous_observation=updated
        self.previous_surface=surface
        self.current=updated or Observation("hidden",stamp,reason=_tr("Localizando no mapa selecionado…"))
        if updated is not None and surface=='minimap':
            self.verified_frame=image
            self.verified_observation=updated
            if not self.recent or stamp-self.recent[-1][1].captured_at>=.12:
                self.recent.append((image.copy(),updated))
        status=(_tr('correction') if discontinuity else _tr('tracking') if updated else
                _tr('anchor_expired') if stamp-self.last_absolute>age_limit else _tr('flow_lost'))
        self.last_diagnostic={'surface':surface,'state':status,'absolute':self.absolute_status,
            'anchor_age_s':round(stamp-self.last_absolute,4) if math.isfinite(self.last_absolute) else None,
            'pending_age_s':round(stamp-self.anchor_stamp,4) if self.future else None,
            'hud_visible':bool(is_gameplay),'flow':list(self.flow_attempts),
            'published':updated is not None and not discontinuity,'continuity_id':self.continuity_id}
        if status!=self.tracking_status:
            self.tracking_status=status
            logger.info('Tracking surface=%s state=%s anchor_age=%.3f pending_age=%.3f absolute=%s flow=%s absolute_state=%s',
                        surface,status,stamp-self.last_absolute,
                        stamp-self.anchor_stamp if self.future else 0,self.absolute_reason,
                        self.flow_attempts[-1].get('reason','external_follow') if self.flow_attempts else 'not_attempted',self.absolute_status)
        if discontinuity:
            self.continuity_id+=1
            self.recent.clear()
            # Keep the recovered anchor internally; never animate across a large correction.
            return Observation("hidden",stamp,reason=_tr("Recuperando alinhamento…"),continuity_id=self.continuity_id)
        self.current=replace(self.current,continuity_id=self.continuity_id)
        return self.current
