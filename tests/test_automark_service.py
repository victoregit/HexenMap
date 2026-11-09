from dataclasses import replace
from types import SimpleNamespace
import threading
import numpy as np
import pytest

from src.live.automark import ChestSignals
from src.live.automark_service import AutoMarkService
from src.live.vision import Observation


def service(tmp_path,monkeypatch):
    import src.live.automark_service as module
    clock=[10.];snapshot=[None];enabled=[True];epoch=[1];focused=[True];output=[]
    rect=SimpleNamespace(hwnd=99,x=8,y=31,width=1366,height=768,is_found=True)
    native=SimpleNamespace(game=lambda:rect,foreground=lambda rect:focused[0],
        capture=lambda *a,**kw:np.zeros((768,1366,3),np.uint8),close_capture=lambda:None)
    pack=SimpleNamespace(gameplay_ui=np.ones((10,10,3),np.uint8),gameplay_ui_roi=(0,0,.2,.2))
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(module,'template_visible',lambda *a:True)
    monkeypatch.setattr(module,'confirmed_circle',lambda *a:(100,100,60))
    monkeypatch.setattr(module,'pointer_shape',lambda *a:True)
    signals=ChestSignals(tmp_path);signals.ready=True;reading=[{}]
    signals.capture_signals=lambda *a:reading[0]
    context=lambda:(enabled[0],0,epoch[0],pack,snapshot[0])
    worker=AutoMarkService(signals,lambda:native,context,output.append,threading.Event())
    obs=Observation('minimap',10,np.eye(2,3),.95,.3,(100,100,60),(100,100),map_id='as-map-2',layer_id='surface')
    geometry=(99,8,31,1366,768)
    def tick(t,values,located=True):
        clock[0]=t;reading[0]=values
        current=replace(obs,captured_at=t) if located else Observation('hidden',t,reason='Recuperando alinhamento…')
        snapshot[0]=(geometry,current,epoch[0]);worker.poll(t)
    return worker,signals,tick,output,enabled,epoch,focused


def test_reward_sampling_survives_short_tracking_loss_after_a_located_opening(tmp_path,monkeypatch):
    worker,signals,tick,events,*_=service(tmp_path,monkeypatch)
    tick(10,{'opening':True});tick(10.125,{'opening':True})
    tick(10.25,{'loot':True},located=False)
    tick(10.375,{'adventure_exp':True},located=False)
    assert len(events)==1 and events[0][2].stamp==10.125


def test_unknown_position_never_arms_and_selection_change_discards_pending_chest(tmp_path,monkeypatch):
    worker,signals,tick,events,enabled,epoch,focused=service(tmp_path,monkeypatch)
    tick(10,{'opening':True},False);tick(10.125,{'opening':True},False)
    tick(10.25,{'loot':True,'adventure_exp':True},False)
    assert not events
    tick(10.375,{'opening':True});tick(10.5,{'opening':True})
    epoch[0]+=1
    tick(10.625,{'loot':True,'adventure_exp':True})
    assert not events


def test_disabled_worker_allocates_no_capture_and_focus_loss_cancels_sequence(tmp_path,monkeypatch):
    worker,signals,tick,events,enabled,epoch,focused=service(tmp_path,monkeypatch)
    enabled[0]=False;tick(10,{})
    assert worker.native is None
    enabled[0]=True;tick(10.125,{'opening':True});tick(10.25,{'opening':True})
    focused[0]=False;tick(10.375,{})
    focused[0]=True;tick(10.5,{'loot':True,'adventure_exp':True})
    assert not events


@pytest.mark.parametrize('changed_scope',[False,True])
def test_service_recovers_original_opening_from_exact_capture_not_new_position(tmp_path,monkeypatch,changed_scope):
    import cv2
    from src.live.opening_recovery import minimap_frame
    worker,signals,_,events,*_=service(tmp_path,monkeypatch)
    clock=[10.];epoch=[1];snapshot=[None];image=[None];values=[{}]
    monkeypatch.setattr('src.live.automark_service.time.monotonic',lambda:clock[0])
    rng=np.random.default_rng(42)
    terrain=cv2.GaussianBlur(rng.integers(0,255,(768,1366,3),dtype=np.uint8),(3,3),0)
    rect=SimpleNamespace(hwnd=99,x=8,y=31,width=1366,height=768,is_found=True)
    native=SimpleNamespace(game=lambda:rect,foreground=lambda r:True,capture=lambda *a,**k:image[0],close_capture=lambda:None)
    worker.native_factory=lambda:native
    pack=SimpleNamespace(gameplay_ui=np.ones((10,10,3),np.uint8),gameplay_ui_roi=(0,0,.2,.2))
    worker.context=lambda:(True,0,epoch[0],pack,snapshot[0])
    signals.capture_signals=lambda *a:values[0]
    for n in range(4):
        stamp=10+n*.125;clock[0]=stamp
        image[0]=cv2.warpAffine(terrain,np.array([[1.,0,n*2.],[0,1.,0]]),(1366,768))
        if n==3:
            if changed_scope:epoch[0]+=1
            obs=Observation('minimap',stamp,np.array([[1.,0,n*2.],[0,1.,0]]),.95,.2,(100,100,60),(100-n*2,100),map_id='as-map-2',layer_id='surface')
            anchor=minimap_frame(image[0],obs.circle,stamp)
        else:obs=Observation('hidden',stamp);anchor=None
        snapshot[0]=((99,8,31,1366,768),obs,epoch[0],anchor)
        values[0]={'opening':True} if n<2 else {'loot':True,'adventure_exp':True}
        worker.poll(stamp)
    if changed_scope:assert not events
    else:
        assert len(events)==1 and events[0][2].stamp==10.125
        assert events[0][2].observation.player==pytest.approx((98,100),abs=.5)


def test_blue_water_does_not_reset_chest_sequence_when_hud_glyph_is_faint(tmp_path,monkeypatch):
    import cv2
    from src.live.minimap_glyph import pointer_shape
    from src.live.vision import confirmed_circle
    from src.live.opening_recovery import minimap_frame
    import src.live.automark_service as module
    worker,signals,_,events,*_=service(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'pointer_shape',pointer_shape)
    monkeypatch.setattr(module,'confirmed_circle',confirmed_circle)
    monkeypatch.setattr(module,'template_visible',lambda *a:False)
    monkeypatch.setattr(module,'foreground_ui_visible',lambda *a:False)
    frame=np.zeros((768,1366,3),np.uint8)
    cv2.circle(frame,(118,88),76,(190,165,80),-1)
    cv2.fillPoly(frame,[np.array([[118,81],[112,93],[118,90],[124,93]],np.int32)],(255,200,0))
    rect=SimpleNamespace(hwnd=99,x=8,y=31,width=1366,height=768,is_found=True)
    worker.native_factory=lambda:SimpleNamespace(game=lambda:rect,foreground=lambda r:True,
        capture=lambda *a,**k:frame,close_capture=lambda:None)
    pack=SimpleNamespace(gameplay_ui=None,gameplay_ui_roi=(0,0,.2,.2))
    clock=[10.];snapshot=[None];reading=[{}]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    worker.context=lambda:(True,0,1,pack,snapshot[0])
    signals.capture_signals=lambda *a:reading[0]
    for stamp,values in [(10.,{'opening':True}),(10.125,{'opening':True}),(10.25,{'loot':True,'adventure_exp':True})]:
        clock[0]=stamp;reading[0]=values;circle=(768*.154,768*.115,768*.1)
        obs=Observation('minimap',stamp,np.eye(2,3),.95,.2,circle,circle[:2],map_id='as-map-2',layer_id='surface')
        snapshot[0]=((99,8,31,1366,768),obs,1,minimap_frame(frame,circle,stamp))
        worker.poll(stamp)
    assert len(events)==1 and events[0][2].observation.fresh(10.125)
