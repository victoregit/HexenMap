"""Independent, bounded HUD sampling; tracking delays do not drop reward frames."""
import logging
import time

from src.live.minimap_glyph import pointer_shape
from src.live.vision import Observation,template_visible,foreground_ui_visible,confirmed_circle,steady_circle
from src.live.gameplay import GameplayGate
from src.live.opening_recovery import OpeningRecovery,minimap_frame
from src.live.motion import follow
import numpy as np

logger=logging.getLogger(__name__)


class AutoMarkService:
    def __init__(self,signals,native_factory,context,emit,stop):
        self.signals=signals;self.native_factory=native_factory;self.context=context
        self.emit=emit;self.stop=stop;self.native=None;self.key=None;self.last_log=None;self.log_at=-float('inf')
        self.idle_at=None;self.circle=None
        self.status='idle'
        self.gameplay=GameplayGate();self.recovery=OpeningRecovery();self.continuity=None
        self.circle_checked=-float('inf')

    def report(self,state,now,located=False):
        self.status=state
        details=(state,self.signals.state,located,tuple((k,round(v,2)) for k,v in self.signals.scores.items()))
        # Log transitions; while armed, retain one diagnostic sample per second.
        if details[:3]!=self.last_log or state=='sampling' and now-self.log_at>=2:
            logger.info('AutoMark status=%s phase=%s localized=%s scores=%s',*details)
            self.last_log=details[:3];self.log_at=now

    def idle(self,reason,now):
        self.gameplay.reset();self.recovery.clear();self.continuity=None
        self.signals.reset();self.key=None;self.circle=None;self.report(reason,now)
        if self.idle_at is None:self.idle_at=now
        if self.native is not None and now-self.idle_at>=5:
            self.native.close_capture()

    def poll(self,now):
        enabled,generation,epoch,pack,snapshot=self.context()
        if not enabled or not self.signals.ready:self.idle('disabled',now);return .25
        if pack is None:self.idle('references_loading',now);return .25
        if self.native is None:
            self.native=self.native_factory();self.native.capture_visible=True
        rect=self.native.game()
        if not rect.is_found or not self.native.foreground(rect):self.idle('game_not_focused',now);return .25
        rect_key=(rect.hwnd,rect.x,rect.y,rect.width,rect.height)
        key=(generation,epoch,rect_key)
        if key!=self.key:
            self.signals.reset();self.circle=None;self.key=key
            self.gameplay.reset();self.recovery.clear();self.continuity=None
        self.idle_at=None
        obs=Observation('hidden',now,reason='Aguardando posição válida para AutoMark')
        anchor=None
        if snapshot is not None:
            geometry,observed,observed_epoch=snapshot[:3]
            if geometry==rect_key and observed_epoch==epoch:obs=observed
            if geometry==rect_key and observed_epoch==epoch and len(snapshot)>3:anchor=snapshot[3]
        if obs.surface=='minimap' or obs.continuity_id:
            if self.continuity is not None and obs.continuity_id!=self.continuity:
                self.signals.reset();self.recovery.clear()
            self.continuity=obs.continuity_id
        # This native client capture excludes the overlay itself. Only the HUD
        # strip plus the reward/interact rectangles are read, not a full screen.
        fraction=min(1.,max(.35,pack.gameplay_ui_roi[1]+pack.gameplay_ui_roi[3])+.01)
        frame=self.native.capture(rect,fraction)
        if frame is None:self.idle('capture_failed',now);return .125
        hud=(template_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi)
             or foreground_ui_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi))
        if not hud and self.circle is not None and pointer_shape(frame,self.circle) is not None:
            hud=True
        if not hud and now-self.circle_checked>=1:
            self.circle_checked=now
            detected=confirmed_circle(frame,self.circle)
            if detected is not None:self.circle=steady_circle(detected,self.circle);hud=True
        if self.circle is None:
            self.circle=obs.circle if obs.surface=='minimap' and obs.fresh(now) else confirmed_circle(frame,None)
        is_map=hasattr(pack,'map_ui') and template_visible(frame,pack.map_ui,pack.map_ui_roi)
        pointer=self.circle is not None and pointer_shape(frame,self.circle) is not None
        current_frame=minimap_frame(frame,self.circle,now)
        if (not pointer and (hud or 0<=now-self.gameplay.confirmed<=.35)
                and current_frame is not None and self.recovery.frames):
            previous=self.recovery.frames[-1]
            if 0<now-previous.stamp<=.3 and previous.origin==current_frame.origin:
                relative=Observation('minimap',previous.stamp,np.eye(2,3),.95,.2,previous.circle)
                pointer=follow(previous.pixels,current_frame.pixels,relative,now) is not None
        hud=self.gameplay.accept(now,map_open=is_map,hud=hud,pointer=pointer)
        if not hud:
            self.signals.reset();self.recovery.clear();self.report('not_gameplay',now);return .125
        reading=self.signals.capture_signals(self.native,rect)
        stamp=time.monotonic()
        self.recovery.add(minimap_frame(frame,self.circle,stamp))
        if anchor is not None and obs.surface=='minimap':
            aligned=self.recovery.recover(stamp,anchor,obs,stamp)
            if aligned is not None:obs=aligned
            else:obs=Observation('hidden',stamp,reason='AutoMark alinhando captura atual')
        if self.signals.phase and self.signals.phase[0]=='opening_unlocated':
            source=snapshot[1] if snapshot is not None else obs
            recovered=self.recovery.recover(self.signals.phase[1],anchor,source,stamp)
            if recovered is not None:
                self.signals.resolve_opening(recovered,stamp)
                logger.info('AutoMark opening_recovered age=%.3f uncertainty=%.3f',stamp-recovered.captured_at,recovered.position_uncertainty_px)
        event=self.signals.advance(reading,obs,stamp,gameplay_confirmed=True)
        if self.signals.state=='unresolved_opening':
            self.emit(('automark_unresolved',epoch))
        self.report('sampling',stamp,obs.fresh(stamp) and obs.surface=='minimap')
        if event:
            logger.info('AutoMark event=%s opening_age=%.3f',event.token,stamp-event.stamp)
            self.emit(('automark_event',epoch,event))
        return .125

    def run(self):
        try:
            while not self.stop.is_set():
                start=time.monotonic()
                try:interval=self.poll(start)
                except Exception:
                    logger.exception('Falha na leitura do AutoMark; sequência descartada')
                    self.signals.reset();interval=.5
                self.stop.wait(max(.005,interval-(time.monotonic()-start)))
        finally:
            self.signals.reset()
            if self.native is not None:self.native.close_capture()
