"""Display-only compensation must be bounded and clicks must match what was drawn."""
from dataclasses import replace
from types import SimpleNamespace
import time

import pytest
import numpy as np

from src.live.presentation import DisplayMotion, MarkerCanvas, DisplayTelemetry, outside_controls
from src.live.vision import Observation
from src.live.desktop import DesktopApp
from src.live.storage import read_settings, write_json, DEFAULT_KEYS


def observation(stamp, x, surface='map', layer='surface'):
    return Observation(surface, stamp, np.array([[1.,0.,x],[0.,1.,0.]]), .95,
                       .3, map_id='teyvat', layer_id=layer)


def moving():
    display=DisplayMotion()
    for stamp,x in [(1.,0),(1.05,10),(1.10,20)]:
        display.present(observation(stamp,x), stamp)
    return display


def test_reacquired_map_does_not_inherit_previous_pan_prediction():
    display=moving()
    obs=replace(observation(1.15,30),continuity_id=1)
    assert np.array_equal(display.present(obs,1.175).world_to_screen,obs.world_to_screen)
    assert display.velocity is None


def test_translation_prediction_reduces_sample_hold_error_without_extending_freshness():
    display=moving()
    obs=observation(1.10,20)
    predicted=display.present(obs,1.125)
    assert predicted.world_to_screen[0,2]==pytest.approx(25)
    assert obs.world_to_screen[0,2]==20
    assert predicted.captured_at==obs.captured_at
    assert not display.present(obs,1.8).fresh(1.8)
    assert display.velocity is None


def test_prediction_limits_stop_reverse_zoom_layer_and_minimap():
    display=moving()
    assert display.present(observation(1.10,20),1.16).world_to_screen[0,2]<=28
    assert display.present(observation(1.10,20),1.23).world_to_screen[0,2]==20
    assert display.present(observation(1.15,20),1.17).world_to_screen[0,2]==20
    display=moving()
    assert display.present(observation(1.15,10),1.17).world_to_screen[0,2]==10
    display=moving()
    zoom=observation(1.15,30)
    zoom.world_to_screen[0,0]=1.1
    assert display.present(zoom,1.17).world_to_screen[0,2]==30
    display=moving()
    assert display.present(observation(1.15,30,layer='cave'),1.17).world_to_screen[0,2]==30
    assert display.present(observation(1.2,40,surface='minimap'),1.22).world_to_screen[0,2]==40


def test_area_migration_preserves_bytes_progress_preferences_and_old_hotkeys(tmp_path):
    path=tmp_path/'settings.json'
    old={'categories':['anemoculus'],'package':'appsample','regional':{'appsample':{
        'area':'old-hidden-area','categories':['anemoculus'],'layer':'as-map-2 / surface'}},
        'hotkeys':{'visibility':'F8','collect':'F9','undo':'F10'}}
    write_json(path,old); original=path.read_bytes()
    settings=read_settings(path)
    assert settings['regional']['appsample']['area'] is None
    assert settings['regional']['appsample']['categories']==['anemoculus']
    assert settings['hotkeys']['visibility']=='F8' and settings['hotkeys']['panel']=='F7'
    backup=path.with_name(path.name+'.pre-nation-layer.bak')
    assert backup.read_bytes()==original
    assert read_settings(path)==settings
    assert backup.read_bytes()==original


def test_displayed_position_hit_does_not_reproject_old_observation(monkeypatch):
    calls=[]
    monkeypatch.setattr('src.live.desktop.MarkerMenu',lambda *args:calls.append(args))
    app=DesktopApp.__new__(DesktopApp)
    rect=SimpleNamespace(hwnd=1,x=0,y=0,width=600,height=400)
    app.native=SimpleNamespace(game=lambda:rect,pointer=lambda:(True,0,0),menu_foreground=lambda r:True,
                               interactive=lambda *a:None,hide=lambda *a:None)
    app.control_listener=SimpleNamespace(is_down=True)
    app.menu_open=False;app.input_hwnd=2;app.root=object()
    app.geometry_key=app.rect_key(rect);app.displayed_at=time.monotonic()
    app.displayed_observation=SimpleNamespace(fresh=lambda now:True)
    item=SimpleNamespace(id='chest')
    app.visible_pins=[SimpleNamespace(item=item,x=108,y=100)]
    app.session=SimpleNamespace(hit_test=lambda *a: (_ for _ in ()).throw(AssertionError('must use displayed pins')))
    app.open_marker_menu(SimpleNamespace(x=119,y=100,x_root=119,y_root=100))
    assert calls[0][3]==[item]
    app.menu_open=False;app.displayed_at-=1
    app.open_marker_menu(SimpleNamespace(x=108,y=100,x_root=108,y_root=100))
    assert len(calls)==1


def test_canvas_retains_primitives_until_state_or_membership_changes():
    class Canvas:
        def __init__(self): self.items={};self.moves=[];self.deleted=[];self.n=0
        def find_all(self): return list(self.items)
        def create_image(self,*args,**kwargs):self.n+=1;self.items[self.n]=None;return self.n
        def addtag_withtag(self,tag,i): self.items[i]=tag
        def move(self,*args): self.moves.append(args)
        def delete(self,tag):
            self.deleted.append(tag)
            self.items.pop(tag,None)
            self.items={i:t for i,t in self.items.items() if t!=tag and tag!='all'}
    canvas=Canvas()
    def draw(target,*args,**kwargs):target.create_image(0,0)
    renderer=MarkerCanvas(canvas,draw)
    pin=SimpleNamespace(item=SimpleNamespace(id='a',category='common-chest'),x=100,y=100)
    renderer.render([pin],lambda i:False)
    pin.x=104;renderer.render([pin],lambda i:False)
    assert canvas.n==1 and canvas.moves[-1][1:]==(4,0)
    renderer.render([pin],lambda i:True)
    assert canvas.n==2
    renderer.render([],lambda i:False)
    assert not canvas.items and not renderer.entries


def test_display_telemetry_records_submission_age_without_claiming_game_latency(tmp_path):
    import csv
    path=tmp_path/'display.csv'
    log=DisplayTelemetry(path)
    now=time.monotonic()
    obs=observation(now-.025,20)
    shown=replace(obs,world_to_screen=obs.world_to_screen.copy())
    shown.world_to_screen[0,2]+=4
    log.record('mondstadt',obs,shown,[object()],now)
    log.close()
    with path.open() as handle: row=next(csv.DictReader(handle))
    assert float(row['capture_to_submit_ms'])>=25
    assert float(row['prediction_px'])==4 and row['pins']=='1'
    assert 'end_to_end_latency' not in row


def test_control_exclusion_removes_entire_symbol_and_click_target_at_edges():
    pins=[SimpleNamespace(x=x,y=50) for x in (20,39,40,50,111,112,113,150)]
    # Panel occupies x=52..100. A symbol whose 12 px margin touches it is hidden.
    visible=outside_controls(pins,[(52,30,100,70)])
    assert [p.x for p in visible]==[20,39,113,150]
    assert outside_controls(pins,[])==pins
    assert outside_controls(pins,[(0,0,200,100)])==[]
