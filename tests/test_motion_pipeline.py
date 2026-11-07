"""Delayed absolute results must follow verified intermediate frames, not a giant jump."""
from concurrent.futures import Future
from dataclasses import replace
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from src.live.motion import MotionRecognizer, follow, comparison_points
from src.live.vision import Observation


def pipeline(monkeypatch,surface='map'):
    monkeypatch.setattr('src.live.motion.gray',lambda frame:frame)
    monkeypatch.setattr('src.live.motion.template_visible',lambda frame,template,roi:template==('map' if surface=='map' else 'game'))
    monkeypatch.setattr('src.live.motion.detect_circle',lambda frame:(50.,50.,40.))
    calls=[]
    def follow(previous,current,observation,stamp):
        displacement=float(current[0,0])-float(previous[0,0])
        calls.append(displacement)
        if abs(displacement)>15: return None
        matrix=observation.world_to_screen.copy()
        matrix[0,2]+=displacement
        return replace(observation,world_to_screen=matrix,captured_at=stamp)
    monkeypatch.setattr('src.live.motion.follow',follow)
    pending=[]
    recognizer=SimpleNamespace(pack=SimpleNamespace(map_ui='map',map_ui_roi=None,
                                                   gameplay_ui='game',gameplay_ui_roi=None),observe=lambda *a:None)
    motion=MotionRecognizer(recognizer)
    motion.pool.shutdown(wait=False)
    def submit(*args):
        future=Future();pending.append(future);return future
    motion.pool=SimpleNamespace(submit=submit,shutdown=lambda **kw:None)
    return motion,pending,calls


def frame(x): return np.full((100,100),x,dtype=np.uint8)


def test_pending_absolute_rebased_through_each_verified_frame(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch)
    assert motion.observe(frame(0),100).surface=='hidden'
    motion.observe(frame(10),100.05)
    motion.observe(frame(20),100.10)
    pending[0].set_result(Observation('map',100,np.eye(2,3),.95,.3,
                                      map_id='teyvat',layer_id='surface'))
    result=motion.observe(frame(30),100.15)
    assert result.surface=='map' and result.world_to_screen[0,2]==30
    assert result.captured_at==100.15
    assert calls==[10,10,10]  # No fragile direct 0 -> 30 registration.
    assert motion.last_absolute==100  # Chaining never extends the absolute anchor age.
    motion.close()


def test_flow_gap_cannot_be_bridged_by_unverified_motion(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch)
    motion.observe(frame(0),100)
    motion.observe(frame(30),100.05)  # Invalid step.
    assert motion.anchor_motion is None
    pending[0].set_result(Observation('map',100,np.eye(2,3),.95,.3,
                                      map_id='teyvat',layer_id='surface'))
    result=motion.observe(frame(40),100.1)
    assert result.surface=='hidden'
    assert calls==[30,40]
    motion.close()


def test_reset_discards_pending_chain_and_old_absolute_result(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch)
    motion.observe(frame(0),100)
    motion.observe(frame(10),100.05)
    motion.reset()
    assert pending[0].cancelled()
    assert motion.anchor_motion is None and motion.previous is None
    assert motion.observe(frame(80),100.1).surface=='hidden'
    motion.close()


@pytest.mark.parametrize('surface,circle,point',[
    ('map',None,(600,400)),('minimap',(220,180,84),(220,180))])
def test_cropped_flow_keeps_screen_coordinates_and_pixel_error_bounds(surface,circle,point):
    rng=np.random.default_rng(42)
    image=cv2.GaussianBlur(rng.integers(0,256,(800,1200),dtype=np.uint8),(3,3),0)
    transform=np.array([[1.,0.,9.],[0.,1.,-6.]])
    moved=cv2.warpAffine(image,transform,(1200,800))
    observation=Observation(surface,100,np.eye(2,3),.95,.3,circle=circle,
                            map_id='teyvat',layer_id='surface')
    tracked=follow(image,moved,observation,100.05)
    assert tracked is not None
    p=np.array([*point,1.])
    assert np.linalg.norm(tracked.world_to_screen@p-transform@p)<1.5
    assert tracked.map_id=='teyvat' and tracked.layer_id=='surface'


def test_moving_minimap_bootstraps_and_rebases_without_long_baseline_registration(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch,'minimap')
    motion.observe(frame(0),100)
    motion.observe(frame(10),100.05)
    motion.observe(frame(20),100.10)
    pending[0].set_result(Observation('minimap',100,np.eye(2,3),.95,.3,circle=(50.,50.,40.),
                                      map_id='teyvat',layer_id='surface'))
    result=motion.observe(frame(30),100.15)
    assert result.surface=='minimap' and result.world_to_screen[0,2]==30
    assert result.circle==(50.,50.,40.) and result.player==(20.,50.)
    assert calls==[10,10,10] and motion.last_absolute==100
    assert motion.observe(frame(40),100.2).world_to_screen[0,2]==40
    motion.reset()
    assert motion.circle is None
    motion.close()


def test_minimap_correction_is_judged_inside_its_circle_not_across_the_screen(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch,'minimap')
    image=np.zeros((768,1366),np.uint8)
    circle=(180.,110.,60.)
    motion.previous=image;motion.previous_surface='minimap';motion.circle=circle
    motion.current=Observation('minimap',100,np.eye(2,3),.95,.3,circle=circle,
                               map_id='teyvat',layer_id='surface')
    motion.last_absolute=100;motion.anchor_stamp=100;motion.anchor_frame=image
    motion.anchor_motion=np.eye(3)
    motion.future=Future()
    rotation=cv2.getRotationMatrix2D(circle[:2],3.,1.)
    motion.future.set_result(replace(motion.current,world_to_screen=rotation))
    local=comparison_points(motion.current,1366,768)
    assert np.max(np.linalg.norm(local[:,:2]-np.array(circle[:2]),axis=1))<circle[2]
    far=np.array([1366*.7,768*.7,1])
    assert np.linalg.norm(rotation@far-far[:2])>24
    result=motion.observe(image,100.05)
    assert result.surface=='minimap' and result.fresh(100.05)
    motion.close()


def test_menu_discards_minimap_geometry_and_pending_motion(monkeypatch):
    motion,pending,calls=pipeline(monkeypatch,'minimap')
    motion.observe(frame(0),100);motion.observe(frame(10),100.05)
    monkeypatch.setattr('src.live.motion.template_visible',lambda *args:False)
    assert motion.observe(frame(20),100.1).surface=='hidden'
    assert motion.circle is None and motion.anchor_motion is None and pending[0].cancelled()
    motion.close()
