from dataclasses import replace
import cv2
import numpy as np
import pytest

from src.live.opening_recovery import OpeningRecovery,minimap_frame,MiniFrame
from src.live.vision import Observation
from src.live.automark import ChestSignals,AutoMark
from src.live.gameplay import GameplayGate


def texture():
    return cv2.GaussianBlur(np.random.default_rng(7).integers(0,255,(180,180),dtype=np.uint8),(3,3),0)


def test_reverse_recovery_uses_opening_position_not_later_player_position():
    original=texture();ring=OpeningRecovery();circle=(90,90,65)
    for n in range(5):
        frame=cv2.warpAffine(original,np.array([[1.,0,n*2.],[0,1.,0]]),(180,180))
        ring.add(minimap_frame(frame,circle,10+n*.125))
    obs=Observation('minimap',10.5,np.array([[1.,0,8.],[0,1.,0]]),.95,.2,circle,(82,90),map_id='a',layer_id='surface')
    recovered=ring.recover(10,ring.frames[-1],obs,10.5)
    assert recovered is not None and recovered.captured_at==10
    assert recovered.player==pytest.approx((90,90),abs=.3)
    assert recovered.player!=obs.player
    assert recovered.world_to_screen@np.array([90,90,1])==pytest.approx((90,90),abs=.3)
    assert ring.recover(10,ring.frames[-1],obs,13.01) is None


def test_no_reconstruction_across_unverified_gap_or_textureless_frame():
    ring=OpeningRecovery();circle=(90,90,65);a=minimap_frame(texture(),circle,10)
    ring.add(a);ring.add(replace(a,stamp=10.5))
    obs=Observation('minimap',10.5,np.eye(2,3),.95,.2,circle,(90,90))
    assert ring.recover(10,ring.frames[-1],obs,10.5) is None
    ring.clear();ring.add(a);ring.add(replace(a,stamp=10.125,pixels=np.zeros_like(a.pixels)))
    assert ring.recover(10,ring.frames[-1],replace(obs,captured_at=10.125),10.125) is None


def test_independently_cropped_hud_and_tracker_frames_use_shared_screen_pixels():
    image=texture();ring=OpeningRecovery()
    ring.add(minimap_frame(image,(90,90,65),10))
    moved=cv2.warpAffine(image,np.array([[1.,0,2.],[0,1.,0]]),(180,180))
    ring.add(minimap_frame(moved,(90,90,65),10.125))
    obs=Observation('minimap',10.125,np.array([[1.,0,2.],[0,1.,0]]),.95,.2,(90,90,63),(88,90))
    anchor=minimap_frame(moved,obs.circle,10.125)
    recovered=ring.recover(10,anchor,obs,10.125)
    assert recovered is not None and recovered.player==pytest.approx((90,90),abs=.3)


def test_ring_is_bounded_and_geometry_change_clears_evidence():
    ring=OpeningRecovery();ring.MAX_BYTES=10000
    for n in range(40):ring.add(MiniFrame(n*.125,np.zeros((50,50),np.uint8),(0,0),(25,25,20)))
    assert ring.bytes<=10000 and len(ring.frames)==4
    ring.add(MiniFrame(6,np.zeros((40,40),np.uint8),(0,0),(20,20,15)))
    assert len(ring.frames)==1
    ring.clear();assert ring.bytes==0 and not ring.frames


def test_unknown_opening_retains_rewards_until_exact_time_is_reconstructed(tmp_path):
    signals=ChestSignals(tmp_path);signals.ready=True
    hidden=Observation('hidden',10)
    signals.advance({'opening':True},hidden,10,True)
    signals.advance({'opening':True},hidden,10.125,True)
    signals.advance({'loot':True,'adventure_exp':True},hidden,10.25,True)
    assert signals.phase[0]=='opening_unlocated'
    obs=Observation('minimap',10.125,np.eye(2,3),.95,.2,(100,100,60),(100,100))
    signals.resolve_opening(replace(obs,captured_at=10.5),10.5)
    assert signals.phase[0]=='opening_unlocated' # Later position cannot replace opening.
    signals.resolve_opening(obs,10.5)
    event=signals.advance({},replace(obs,captured_at=10.5),10.5,True)
    assert event is not None and event.observation.captured_at==10.125
    assert signals.advance({'loot':True,'adventure_exp':True},obs,10.625,True) is None


def test_unlocated_event_expires_without_writing_or_accepting_loot_alone(tmp_path):
    signals=ChestSignals(tmp_path);signals.ready=True;hidden=Observation('hidden',10)
    signals.advance({'opening':True},hidden,10,True);signals.advance({'opening':True},hidden,10.125,True)
    for t in np.arange(10.25,13.25,.125):assert signals.advance({'loot':True},hidden,float(t),True) is None
    assert signals.advance({'loot':True},hidden,13.25,True) is None
    assert signals.state=='unresolved_opening' and signals.phase is None


def test_reward_evidence_is_not_lost_while_waiting_for_reconstruction(tmp_path):
    signals=ChestSignals(tmp_path);signals.ready=True;hidden=Observation('hidden',10)
    signals.advance({'opening':True},hidden,10,True);signals.advance({'opening':True},hidden,10.125,True)
    signals.advance({'loot':True,'primogem':True},hidden,10.25,True)
    for t in np.arange(10.375,12.875,.125):signals.advance({},hidden,float(t),True)
    obs=Observation('minimap',10.125,np.eye(2,3),.95,.2,(100,100,60),(100,100))
    signals.resolve_opening(obs,12.875)
    event=signals.advance({},replace(obs,captured_at=12.875),12.875,True)
    assert event is not None and event.stamp==10.125


def test_gameplay_gate_tolerates_one_missed_glyph_but_not_map_or_missing_pointer():
    gate=GameplayGate()
    assert gate.accept(10,map_open=False,hud=True,pointer=True)
    assert gate.accept(10.2,map_open=False,hud=False,pointer=True)
    assert not gate.accept(10.36,map_open=False,hud=False,pointer=True)
    assert not gate.accept(10.4,map_open=True,hud=True,pointer=True)
    assert not gate.accept(10.5,map_open=False,hud=False,pointer=True)
    assert not gate.accept(11,map_open=False,hud=True,pointer=False)
