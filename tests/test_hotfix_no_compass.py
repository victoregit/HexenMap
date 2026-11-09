from dataclasses import replace
from pathlib import Path
import json
import numpy as np

from src.live.catalog import Item
from src.live.session import Session
from src.live.vision import Observation
from src.live.storage import read_settings,DEFAULT_KEYS
from src.live.marker_art import shell_geometry
from src.progress.progress_manager import ProgressManager


def test_near_chest_stays_visible_at_player_and_rotates_without_expiring_pose(tmp_path,monkeypatch):
    monkeypatch.setattr('src.live.session.marker_geometry',lambda *a:shell_geometry(24,32))
    item=Item('appsample:marker:1','Baú','common-chest',2,1,region_id='appsample',map_id='as-map-2')
    session=Session([item],ProgressManager(str(tmp_path/'progress.json')))
    session.region_id='appsample';session.map_id='as-map-2';session.layer_id='surface';session.selected={'common-chest'}
    obs=Observation('minimap',10,np.array([[1.,0,120],[0,1.,100]]),.95,.2,(120,100,60),(0,0),map_id='as-map-2',layer_id='surface')
    pins=session.pins(600,400,10,observation=obs)
    assert len(pins)==1 and (pins[0].x,pins[0].y)==(122,101)
    rotated=replace(obs,world_to_screen=np.array([[0.,-1,120],[1,0.,100]]))
    pins=session.pins(600,400,10,observation=rotated)
    assert len(pins)==1 and (pins[0].x,pins[0].y)==(119,102)
    assert session.pins(600,400,10.7,observation=rotated)==[]


def test_removed_navigation_keys_migrate_with_backup_and_preserve_custom_shortcuts(tmp_path):
    path=tmp_path/'settings.json'
    old={'categories':['common-chest'],'hotkeys':{'visibility':'F6','collect':'F7','undo':'F8','panel':'F11',
         'farm':'Ctrl+Alt+F9','farm_next':'Ctrl+Alt+F10'},'automark':True,'performance_mode':'light'}
    original=json.dumps(old).encode();path.write_bytes(original)
    result=read_settings(path)
    assert set(result['hotkeys'])==set(DEFAULT_KEYS)=={'visibility','collect','undo','panel'}
    assert result['hotkeys']['collect']=='F7' and result['categories']==['common-chest'] and result['automark']
    assert path.with_name('settings.json.pre-no-compass.bak').read_bytes()==original
    assert read_settings(path)==result


def test_live_session_and_automark_have_no_navigation_dependency(tmp_path):
    from src.live.automark import AutoMark,OpeningEvent
    item=Item('appsample:marker:1','Baú','common-chest',101,100,region_id='appsample',map_id='as-map-2')
    session=Session([item],ProgressManager(str(tmp_path/'progress.json')))
    session.region_id='appsample';session.map_id='as-map-2';session.layer_id='surface'
    assert not hasattr(session,'farm')
    obs=Observation('minimap',10,np.eye(2,3),.95,.2,(100,100,60),(100,100),map_id='as-map-2',layer_id='surface')
    assert AutoMark().apply(OpeningEvent(1,10,obs),session,10.2)=='marked'
    session.undo();assert not session.is_collected(item.id)
