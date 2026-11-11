"""A camera-lighting change must not masquerade as terrain motion or a teleport."""
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from src.live.motion import MotionRecognizer,follow
from src.live.vision import Observation


def lighting_pair(seed=42,translation=(3.,-2.)):
    rng=np.random.default_rng(seed)
    terrain=cv2.GaussianBlur(rng.integers(0,255,(240,240),np.uint8),(3,3),0)*.3+50
    y,x=np.mgrid[:240,:240]
    theta=np.arctan2(y-120,x-120)
    cone=(np.abs(np.angle(np.exp(1j*(theta-np.pi/2))))<.5).astype(np.float32)
    transform=np.array([[1.,0.,translation[0]],[0.,1.,translation[1]]])
    current=cv2.warpAffine(terrain,transform,(240,240))+cv2.GaussianBlur(cone,(0,0),4)*90
    return terrain.astype(np.uint8),np.clip(current,0,255).astype(np.uint8),transform


def tracker():
    return MotionRecognizer(SimpleNamespace(pack=SimpleNamespace()))


def observation():
    return Observation('minimap',100.,np.eye(2,3),.95,circle=(120.,120.,90.))


@pytest.mark.parametrize('translation',[(0.,0.),(3.,-2.),(-4.,1.)])
def test_camera_lighting_recovers_real_motion_without_changing_shared_follow(translation):
    before,after,expected=lighting_pair(translation=translation)
    obs=observation();motion=tracker()
    try:
        assert follow(before,after,obs,100.05) is None
        recovered=motion._follow(before,after,obs,100.05)
        assert recovered is not None
        points=np.array([[120,120,1],[70,120,1],[170,120,1],[120,70,1],[120,170,1]])
        assert np.max(np.linalg.norm(points@recovered.world_to_screen.T-points@expected.T,axis=1))<.2
        assert recovered.captured_at==100.05
        assert recovered.position_uncertainty_px<=2.5
        assert motion.flow_attempts[-1]['image']=='terrain_contrast'
        # AutoMark calls this shared function directly: its behavior is preserved.
        assert follow(before,after,obs,100.05) is None
    finally:motion.close()


def test_lighting_recovery_does_not_match_different_terrain():
    before,_,_=lighting_pair()
    motion=tracker()
    try:
        for seed in range(10,30):
            _,unrelated,_=lighting_pair(seed=seed)
            assert motion._follow(before,unrelated,observation(),100.05) is None
    finally:motion.close()


def test_lighting_recovery_keeps_gap_age_limit_and_uncertainty_budget():
    from dataclasses import replace
    before,after,_=lighting_pair()
    motion=tracker()
    try:
        assert motion._follow(before,after,observation(),100.6) is None
        assert len(motion.flow_attempts)==1
        uncertain=replace(observation(),position_uncertainty_px=2.51)
        assert motion._follow(before,after,uncertain,100.05) is None
    finally:motion.close()
