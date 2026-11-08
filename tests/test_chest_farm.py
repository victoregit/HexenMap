from dataclasses import replace
import numpy as np
import pytest
from src.live.catalog import Item
from src.live.session import Session
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager


def setup(tmp_path):
    items=[Item('a','Baú A','common-chest',10,0),Item('b','Baú B','common-chest',30,0),
           Item('resource','Planta','plant',1,0),Item('other-map','Baú','common-chest',1,0,map_id='chasm'),
           Item('other-layer','Baú','common-chest',2,0,layer_id='cave')]
    session=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    session.region_id='mondstadt';session.map_id='teyvat';session.layer_id='surface';session.selected={'common-chest','plant'}
    observation=Observation('minimap',100,np.array([[1.,0,100],[0,1.,100]]),.95,.2,
                            (100,100,70),(0,0),map_id='teyvat',layer_id='surface',heading_screen=0.,heading_confidence=1.)
    session.farm.start(session)
    return session,observation


def test_nearest_selected_chest_is_locked_until_collected_and_origin_is_preserved(tmp_path):
    s,o=setup(tmp_path);g=s.farm.update(s,o,100)
    assert g.target_id=='a' and g.direction==(1.,0.) and s.farm.origin==(0,0)
    moved=replace(o,player=(29,0),captured_at=100.1)
    assert s.farm.update(s,moved,100.1).target_id=='a' # No oscillation between targets.
    s.set_collected('a',True)
    assert s.farm.update(s,moved,100.1).target_id=='b'
    assert s.farm.origin==(0,0) and s.is_collected('a')
    s.undo();assert not s.is_collected('a')
    assert s.farm.update(s,moved,100.1).target_id=='b'


def test_skip_is_local_and_does_not_mark_progress(tmp_path):
    s,o=setup(tmp_path);s.farm.update(s,o,100);s.farm.skip()
    assert s.farm.update(s,o,100).target_id=='b'
    assert s.progress.collected_count==0
    s.farm.skip();assert s.farm.update(s,o,100) is None
    s.farm.start(s);assert s.farm.update(s,o,100).target_id=='a'


@pytest.mark.parametrize('change',[{'surface':'map'},{'surface':'hidden'},{'captured_at':99.},
                                  {'player':None},{'map_id':'chasm'},{'layer_id':'cave'}])
def test_invalid_localization_never_draws_or_advances(change,tmp_path):
    s,o=setup(tmp_path);s.farm.update(s,o,100)
    assert s.farm.update(s,replace(o,**change),100) is None
    assert s.farm.target_id=='a' and s.progress.collected_count==0


def test_hidden_overlay_and_empty_selection_suppress_compass(tmp_path):
    s,o=setup(tmp_path);s.hidden=True
    assert s.farm.update(s,o,100) is None and s.farm.origin is None
    s.hidden=False;s.selected=set();assert s.farm.update(s,o,100) is None
    s.selected={'plant'};assert s.farm.update(s,o,100) is None


def test_direction_and_north_follow_minimap_rotation_without_claiming_camera_yaw(tmp_path):
    s,o=setup(tmp_path);matrix=np.array([[0.,-2,100],[2,0,100]])
    g=s.farm.update(s,replace(o,world_to_screen=matrix),100)
    assert g.direction==pytest.approx((0,1)) and g.north==pytest.approx((1,0))
    assert g.nearby and s.progress.collected_count==0 # Arrival never confirms collection.


def test_scope_change_stops_farm_and_source_ids_do_not_cross(tmp_path):
    s,o=setup(tmp_path);s.farm.update(s,o,100);s.items=list(s.items)
    assert s.farm.update(s,o,100) is None and not s.farm.enabled


def test_imported_collected_chest_is_excluded(tmp_path):
    s,o=setup(tmp_path);s.progress.mark_collected('a');s.progress.save()
    assert s.farm.update(s,o,100).target_id=='b'


def test_proximity_labels_use_minimap_scale_without_claiming_meters(tmp_path):
    s,o=setup(tmp_path)
    assert s.farm.update(s,o,100).proximity=='Próximo'
    assert s.farm.update(s,replace(o,player=(-40,0)),100).proximity=='Na vizinhança'
    assert s.farm.update(s,replace(o,player=(-100,0)),100).proximity=='Mais distante'


def test_legacy_hotkeys_are_preserved_when_farm_shortcuts_are_added(tmp_path):
    from src.live.storage import read_settings,write_json,DEFAULT_KEYS
    previous={'visibility':'Ctrl+Alt+F9','collect':'Ctrl+Alt+F10','undo':'F6','panel':'F7'}
    path=tmp_path/'settings.json';write_json(path,{'categories':[],'hotkeys':previous})
    updated=read_settings(path)['hotkeys']
    assert all(updated[k]==v for k,v in previous.items())
    assert set(updated)==set(DEFAULT_KEYS) and len(set(updated.values()))==len(updated)
    write_json(path,{'categories':[],'hotkeys':updated});assert read_settings(path)['hotkeys']==updated


def test_target_highlight_never_appears_without_a_visible_pin_or_over_controls(tmp_path):
    from src.live.chest_farm import TargetHighlight
    from src.live.session import Pin
    class Canvas:
        def __init__(self):self.created=0;self.state='hidden';self.box=None
        def itemconfigure(self,tag,**kw):self.state=kw.get('state',self.state)
        def find_withtag(self,tag):return [1] if self.created else []
        def create_oval(self,*a,**kw):self.created+=1
        def coords(self,tag,*box):self.box=box
        def tag_raise(self,tag):pass
    s,o=setup(tmp_path);g=s.farm.update(s,o,100);c=Canvas();highlight=TargetHighlight(c)
    highlight.render(g,[],o);assert c.created==0
    pin=Pin(s.item_by_id('a'),110,100)
    highlight.render(g,[pin],o);assert c.created==1 and c.state=='normal'
    highlight.render(g,[pin],o);assert c.created==1 # Reuse the same primitive.
    highlight.render(g,[pin],o,controls=[(90,80,130,120)]);assert c.state=='hidden'
    highlight.render(g,[replace(pin,x=165)],o);assert c.state=='hidden'
    highlight.render(None,[pin],o);assert c.state=='hidden'


@pytest.mark.parametrize('heading,expected',[(0,(1,0)),(90,(0,-1)),(180,(-1,0)),(270,(0,1))])
def test_compass_rotates_with_character_facing(tmp_path,heading,expected):
    s,o=setup(tmp_path);g=s.farm.update(s,replace(o,heading_screen=heading),100)
    assert g.direction==pytest.approx(expected,abs=1e-8)
    assert g.target_id=='a'


def test_map_rotation_and_player_facing_cancel_in_relative_guidance(tmp_path):
    s,o=setup(tmp_path)
    g=s.farm.update(s,replace(o,world_to_screen=np.array([[0.,-1,100],[1,0,100]]),heading_screen=90),100)
    assert g.direction==pytest.approx((1,0),abs=1e-8)


def test_unknown_facing_hides_only_guidance_and_keeps_the_target(tmp_path):
    s,o=setup(tmp_path);s.farm.update(s,o,100)
    assert s.farm.update(s,replace(o,heading_screen=None,heading_confidence=0),100) is None
    assert s.farm.target_id=='a' and s.progress.collected_count==0
    assert s.farm.update(s,replace(o,heading_screen=90),100).direction==pytest.approx((0,-1),abs=1e-8)


def test_arrival_has_hysteresis_and_never_marks_the_chest(tmp_path):
    s,o=setup(tmp_path)
    g=s.farm.update(s,replace(o,player=(5,0)),100)
    assert g.arrived and g.proximity=='No local'
    assert s.farm.update(s,replace(o,player=(2,0)),100).arrived
    assert not s.farm.update(s,replace(o,player=(0,0)),100).arrived
    assert s.progress.collected_count==0
