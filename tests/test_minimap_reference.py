from dataclasses import replace
import math

import cv2
import numpy as np

from src.live.minimap_reference import RegisteredMinimapFrames
from src.live.motion import follow
from src.live.vision import Observation


def pose(stamp=100.):
    return Observation('minimap',stamp,np.eye(2,3),.9,.5,circle=(120.,120.,90.),
                       map_id='as-map-2',layer_id='surface')


def test_reference_registration_uses_fresh_pixels_without_self_training():
    image=cv2.GaussianBlur(np.random.default_rng(27).integers(0,256,(240,240),np.uint8),(3,3),0)
    cache=RegisteredMinimapFrames();assert cache.remember(image,pose())
    assert cache.locate(image,99.,follow) is None
    for stamp,dx in [(100.7,3.),(101.4,6.),(102.1,9.)]:
        transform=np.array([[1.,0.,dx],[0.,1.,-2.]])
        current=cv2.warpAffine(image,transform,(240,240))
        result=cache.locate(current,stamp,follow)
        assert result is not None and result.captured_at==stamp
        assert np.max(np.abs(result.world_to_screen-transform))<.2
        assert result.position_uncertainty_px>=.5
        assert len(cache.frames)==1 and cache.frames[0][1].captured_at==100.
        assert cache.frames[0][0] is image


def test_unrelated_pixels_and_changed_geometry_never_reuse_reference_position():
    rng=np.random.default_rng(27);image=rng.integers(0,256,(240,240),np.uint8)
    cache=RegisteredMinimapFrames();cache.remember(image,pose())
    assert cache.locate(np.zeros((200,200),np.uint8),101.,follow) is None
    for _ in range(10):assert cache.locate(rng.integers(0,256,image.shape,np.uint8),101.,follow) is None
    cache.clear();assert not cache.frames


def test_reference_requires_independent_quality_and_is_bounded_per_context():
    image=np.zeros((240,240),np.uint8);cache=RegisteredMinimapFrames()
    for invalid in [replace(pose(),surface='hidden'),replace(pose(),confidence=.79),
                    replace(pose(),error_px=1.6),replace(pose(),position_uncertainty_px=math.inf),
                    replace(pose(),world_to_screen=None),replace(pose(),map_id=None)]:
        assert not cache.remember(image,invalid)
    for i in range(5):assert cache.remember(image,pose(100.+i))
    assert len(cache.frames)==3
    assert cache.remember(image,replace(pose(106.),map_id='as-map-7'))
    assert len(cache.frames)==1 and cache.frames[0][1].map_id=='as-map-7'

