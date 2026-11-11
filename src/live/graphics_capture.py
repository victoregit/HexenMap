"""Window-only Windows.Graphics.Capture fallback; no hooks or game access."""
import threading
import time

import numpy as np


def client_image(image,rect,bounds):
    """Accept exact client pixels or crop known DWM frame borders; never stretch."""
    if image.shape[:2]==(rect.height,rect.width):return image
    left,top,right,bottom=bounds
    if image.shape[:2]!=(bottom-top,right-left):return None
    x,y=rect.x-left,rect.y-top
    if x<0 or y<0 or x+rect.width>image.shape[1] or y+rect.height>image.shape[0]:return None
    return image[y:y+rect.height,x:x+rect.width]


class WindowGraphicsCapture:
    def __init__(self,hwnd):
        from windows_capture import WindowsCapture
        self.lock=threading.Lock();self.latest=None;self.received=0.;self.error=''
        # MinimumUpdateInterval is unavailable on some supported Windows builds.
        # Leave optional OS properties unset; throttle copies in Python instead.
        self.capture=WindowsCapture(window_hwnd=hwnd,cursor_capture=False,draw_border=None)
        def on_frame_arrived(frame,control):
            now=time.monotonic()
            with self.lock:
                if now-self.received<.05:return
            # Native mapped memory is only valid for the duration of this event.
            image=np.array(frame.frame_buffer[:,:,:3],copy=True,order='C')
            with self.lock:self.latest=image;self.received=now
        def on_closed():
            with self.lock:self.latest=None;self.error='A janela de captura foi fechada.'
        self.capture.frame_handler=on_frame_arrived
        self.capture.closed_handler=on_closed
        self.control=self.capture.start_free_threaded()

    def read(self,rect,bounds,fraction=1.,region=None):
        with self.lock:
            if self.latest is None or time.monotonic()-self.received>.65:return None
            image=self.latest
        image=client_image(image,rect,bounds)
        if image is None:return None
        if region is not None:
            x,y,w,h=map(int,region)
            if min(x,y)<0 or min(w,h)<1 or x+w>rect.width or y+h>rect.height:return None
            return image[y:y+h,x:x+w].copy()
        height=max(1,min(rect.height,round(rect.height*fraction)))
        result=np.zeros((rect.height,rect.width,3),np.uint8)
        result[:height]=image[:height]
        return result

    def close(self):
        self.control.stop()
        with self.lock:self.latest=None
