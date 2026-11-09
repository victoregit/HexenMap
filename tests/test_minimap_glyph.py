import cv2
import numpy as np
import pytest
from src.live.minimap_glyph import pointer_shape
from src.live.vision import confirmed_circle,detect_circle


def scene():
    frame=np.zeros((768,1366,3),np.uint8)
    cv2.fillPoly(frame,[np.array([[114,83],[108,95],[114,92],[120,95]],np.int32)],(255,200,0))
    return frame


@pytest.mark.parametrize('radius',[45,65,85])
def test_player_arrow_size_is_independent_of_map_radius_and_faint_cone(radius):
    frame=scene()
    assert pointer_shape(frame,(114,90,radius)) is not None
    assert confirmed_circle(frame,(114,90,radius))==(114,90,radius)


def test_circle_detection_accepts_real_small_arrow_in_large_minimap(monkeypatch):
    frame=scene()[:,:1200] # Nonstandard aspect: exercise circumference recovery.
    monkeypatch.setattr(cv2,'HoughCircles',lambda *a,**k:np.array([[[114,90,85]]],np.float32))
    circle=detect_circle(frame)
    assert circle is not None and circle[0]==pytest.approx(114,abs=.6) and circle[2]>80


def test_small_coloured_noise_or_missing_player_cannot_confirm_old_geometry(monkeypatch):
    frame=scene()*0;frame[90,114]=(255,200,0)
    monkeypatch.setattr(cv2,'HoughCircles',lambda *a,**k:np.array([[[114,90,85]]],np.float32))
    assert pointer_shape(frame,(114,90,85)) is None
    assert confirmed_circle(frame,(114,90,85)) is None


def test_cyan_water_connected_to_arrow_does_not_swallow_player_glyph():
    frame=scene()*0
    cv2.circle(frame,(114,90),76,(190,165,80),-1)
    cv2.fillPoly(frame,[np.array([[114,83],[108,95],[114,92],[120,95]],np.int32)],(255,200,0))
    old_mask=cv2.inRange(cv2.cvtColor(frame,cv2.COLOR_BGR2HSV),(80,100,160),(110,255,255))
    count,_,stats,_=cv2.connectedComponentsWithStats(old_mask)
    assert max(stats[1:,4])>1000 # The old mask merges lake and native arrow.
    pointer=pointer_shape(frame,(114,90,76))
    assert pointer is not None and cv2.countNonZero(pointer[0])<150
    assert confirmed_circle(frame,(114,90,76))==(114,90,76)
    circle=detect_circle(frame)
    assert circle is not None and circle[2]==pytest.approx(76.8)


@pytest.mark.parametrize('level',[.65,.8,1.])
def test_arrow_recognition_survives_hud_brightness_change(level):
    frame=(scene().astype(float)*level).astype(np.uint8)
    assert pointer_shape(frame,(114,90,76)) is not None
