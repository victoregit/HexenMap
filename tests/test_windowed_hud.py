import cv2
import numpy as np
import pytest
from src.live.vision import detect_circle,template_visible
from src.live.automark import ChestSignals


@pytest.mark.parametrize('size',[(1366,768),(1920,1080),(1920,1200),(1904,1161)])
def test_minimap_geometry_handles_client_height_or_width_without_monitor_coordinates(size):
    width,height=size;effective=min(height,width*768/1366)
    cx,cy,r=effective*.154,effective*.115,effective*.1
    frame=np.zeros((height,width,3),np.uint8)
    scale=effective/768
    arrow=np.asarray([[0,-7],[-6,5],[0,2],[6,5]],float)*scale+[cx,cy]
    cv2.fillPoly(frame,[np.round(arrow).astype(np.int32)],(255,200,0))
    circle=detect_circle(frame)
    assert circle is not None
    assert circle==pytest.approx((cx,cy,r),abs=.6)


@pytest.mark.parametrize('size',[(1920,1080),(1920,1200),(1904,1161)])
@pytest.mark.parametrize('surface',['map','gameplay'])
def test_exact_hud_template_scale_recognizes_map_and_gameplay_cues(size,surface):
    width,height=size;scale=min(width/1366,height/768)
    template=np.zeros((25,48,3),np.uint8)
    cv2.putText(template,'HUD',(1,19),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1,cv2.LINE_AA)
    frame=np.zeros((height,width,3),np.uint8)
    patch=cv2.resize(template,None,fx=scale,fy=scale)
    left=20 if surface=='gameplay' else width-20-patch.shape[1]
    frame[20:20+patch.shape[0],left:left+patch.shape[1]]=patch
    assert template_visible(frame,template,(0 if surface=='gameplay' else .85,0,.15,.15))


def test_chest_width_scaled_16_10_layout_remains_locked_during_reward(tmp_path):
    signals=ChestSignals(tmp_path);signals.ready=True
    signals.reference_size=(1366,768)
    template=np.zeros((25,60),np.uint8)
    cv2.putText(template,'BAU',(2,19),cv2.FONT_HERSHEY_SIMPLEX,.6,255,1,cv2.LINE_AA)
    signals.templates={'opening':(template,(.5,.2,.45,.55),.88),'loot':(template,(0,.2,.4,.6),.88)}
    frame=np.zeros((1200,1920,3),np.uint8);factor=1920/1366
    patch=cv2.resize(template,None,fx=factor,fy=factor)
    color=cv2.cvtColor(patch,cv2.COLOR_GRAY2BGR)
    frame[450:450+patch.shape[0],1100:1100+patch.shape[1]]=color
    assert signals.measure(frame)['opening']
    expected=1920*768/1366
    assert signals.detected_hud_height==pytest.approx(expected)
    frame[:]=0;signals.measure(frame)
    assert signals.hud_scale==pytest.approx(expected/1080)
