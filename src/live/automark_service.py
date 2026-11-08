"""Independent, bounded HUD sampling; tracking delays do not drop reward frames."""
import logging
import time

from src.live.facing import pointer_shape
from src.live.vision import Observation,template_visible,foreground_ui_visible,confirmed_circle

logger=logging.getLogger(__name__)


class AutoMarkService:
    def __init__(self,signals,native_factory,context,emit,stop):
        self.signals=signals;self.native_factory=native_factory;self.context=context
        self.emit=emit;self.stop=stop;self.native=None;self.key=None;self.last_log=None;self.log_at=-float('inf')
        self.idle_at=None;self.circle=None
        self.status='idle'

    def report(self,state,now,located=False):
        self.status=state
        details=(state,self.signals.state,located,tuple((k,round(v,2)) for k,v in self.signals.scores.items()))
        # Log transitions; while armed, retain one diagnostic sample per second.
        if details[:3]!=self.last_log or state=='sampling' and now-self.log_at>=2:
            logger.info('AutoMark status=%s phase=%s localized=%s scores=%s',*details)
            self.last_log=details[:3];self.log_at=now

    def idle(self,reason,now):
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
        if key!=self.key:self.signals.reset();self.circle=None;self.key=key
        self.idle_at=None
        obs=Observation('hidden',now,reason='Aguardando posição válida para AutoMark')
        if snapshot is not None:
            geometry,observed,observed_epoch=snapshot
            if geometry==rect_key and observed_epoch==epoch:obs=observed
        # This native client capture excludes the overlay itself. Only the HUD
        # strip plus the reward/interact rectangles are read, not a full screen.
        fraction=min(1.,max(.35,pack.gameplay_ui_roi[1]+pack.gameplay_ui_roi[3])+.01)
        frame=self.native.capture(rect,fraction)
        if frame is None:self.idle('capture_failed',now);return .125
        hud=(template_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi)
             or foreground_ui_visible(frame,pack.gameplay_ui,pack.gameplay_ui_roi))
        if hud:
            if self.circle is None:
                self.circle=obs.circle if obs.surface=='minimap' and obs.fresh(now) else confirmed_circle(frame,None)
            hud=self.circle is not None and pointer_shape(frame,self.circle) is not None
        if not hud:
            self.signals.reset();self.circle=None;self.report('not_gameplay',now);return .125
        reading=self.signals.capture_signals(self.native,rect)
        stamp=time.monotonic()
        event=self.signals.advance(reading,obs,stamp,gameplay_confirmed=True)
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
