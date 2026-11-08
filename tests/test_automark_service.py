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
