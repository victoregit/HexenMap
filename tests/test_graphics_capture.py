import threading
import time
from types import SimpleNamespace

import numpy as np

from src.live.graphics_capture import WindowGraphicsCapture,client_image


def test_window_frame_crops_title_bar_and_borders_without_scaling():
    rect=SimpleNamespace(x=108,y=131,width=1920,height=1200)
    image=np.zeros((1239,1936,3),np.uint8);image[31:1231,8:1928]=80
    result=client_image(image,rect,(100,100,2036,1339))
    assert result.shape==(1200,1920,3) and (result==80).all()
    assert client_image(image,rect,(100,100,2035,1339)) is None


def test_graphics_rejects_stale_frames_and_preserves_partial_frame_geometry():
    capture=WindowGraphicsCapture.__new__(WindowGraphicsCapture)
    capture.lock=threading.Lock();capture.latest=np.full((1200,1920,3),80,np.uint8)
    capture.received=time.monotonic()-1
    rect=SimpleNamespace(x=0,y=0,width=1920,height=1200)
    assert capture.read(rect,(0,0,1920,1200)) is None
    capture.received=time.monotonic()
    frame=capture.read(rect,(0,0,1920,1200),.35)
    assert frame.shape==(1200,1920,3)
    assert (frame[:420]==80).all() and not frame[420:].any()
    crop=capture.read(rect,(0,0,1920,1200),region=(20,30,100,80))
    assert crop.shape==(80,100,3) and (crop==80).all()
    assert capture.read(rect,(0,0,1920,1200),region=(-1,0,10,10)) is None
