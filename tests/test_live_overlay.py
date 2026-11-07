"""Real behavioral gates, synthetic geometry only; not live-game acceptance."""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.live.catalog import Item, load_catalog, map_pixel
from src.live.reference import ReferenceUnavailable, Terrain, load_pack
from src.live.session import Session
from src.live.storage import DEFAULT_KEYS, read_settings, write_json
from src.live.vision import Observation, TerrainMatcher, template_visible
from src.live.motion import follow, MotionRecognizer
from src.progress.progress_manager import ProgressManager


def observation(matrix=None, surface="minimap", stamp=100):
    return Observation(surface,stamp,np.array([[1,0,0],[0,1,0]],dtype=float) if matrix is None else matrix,
                       .95,.2,(100,100,70),(100,100))


@pytest.fixture
def session(tmp_path):
    items=[Item("real:a","A","anemoculus",105,100),Item("real:b","B","common-chest",118,100),
           Item("real:c","C","anemoculus",165,100)]
    obj=Session(items,ProgressManager(str(tmp_path/"progress.json")))
    obj.observation=observation()
    return obj


def test_catalog_is_real_pinned_and_uses_simple_projection():
    items=load_catalog(Path(__file__).resolve().parents[1]/"data/community/mondstadt")
    assert len(items)==561
    assert all(i.id.startswith("teyvat.moe:mondstadt:") for i in items)
    assert map_pixel(-20,40)==(5120,2560)
    assert all(math.isfinite(i.x+i.y) for i in items)


def test_empty_selection_both_surfaces(session):
    assert session.pins(600,400,100)==[]
    session.observation=observation(surface="map")
    assert session.pins(600,400,100)==[]


@pytest.mark.parametrize("age",[-.01,.651,5])
def test_stale_and_future_estimates_hidden(session,age):
    session.selected={"anemoculus"}
    assert session.pins(600,400,100+age)==[]
    assert session.collect(100+age) is False


def test_entire_minimap_icon_clipped(session):
    session.selected={"anemoculus"}
    pins=session.pins(600,400,100.1)
    assert [p.item.id for p in pins]==["real:a"]


def test_rotation_zoom_pan_transform_same_world_items(session):
    session.selected={"anemoculus"}
    session.observation=observation(np.array([[0,-2,350],[2,0,-100]],dtype=float),"map")
    pins=session.pins(600,400,100)
    assert pins[0].x==150 and pins[0].y==110
    assert session.items[0].x==105


def test_collect_undo_persistence_does_not_touch_legacy_ids(session):
    session.progress.mark_collected("demo_001");session.progress.save()
    session.selected={"anemoculus"}
    assert session.collect(100.1)
    assert ProgressManager(session.progress.filepath).is_collected("real:a")
    assert session.undo()
    restored=ProgressManager(session.progress.filepath)
    assert restored.is_collected("demo_001") and not restored.is_collected("real:a")


def test_ambiguous_collection_requires_explicit_selection(session):
    session.selected={"anemoculus","common-chest"}
    assert not session.collect(100.1)
    assert session.progress.collected_count==0
    assert session.pending_ids=={"real:a","real:b"}
    assert session.confirm("real:b",100.2)
    assert session.progress.get_collected_ids()=={"real:b"}


def test_ambiguous_panel_confirmation_expires(session):
    session.selected={"anemoculus","common-chest"}
    session.collect(100)
    assert not session.confirm("real:b",131)
    session.invalidate("focus lost")
    assert not session.confirm("real:b",101)


def test_pending_manual_selection_survives_switch_to_panel(session):
    session.selected={"anemoculus","common-chest"}
    assert not session.collect(100)
    session.invalidate("panel focus",clear_pending=False)
    assert session.pins(600,400,101)==[]
    assert session.confirm("real:b",101)


def test_invalid_hidden_state_and_hidden_toggle_reject_collection(session):
    session.selected={"anemoculus"}
    session.hidden=True
    assert not session.collect(100)
    assert not session.pins(600,400,100)
    session.hidden=False
    session.invalidate("teleport")
    assert not session.collect(100)


def test_collection_failure_rolls_back_memory(session,monkeypatch):
    session.selected={"anemoculus"}
    monkeypatch.setattr(session.progress,"save",lambda:(_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError): session.collect(100)
    assert not session.progress.is_collected("real:a")
    assert session.undo_ids==[]


def test_settings_empty_selection_and_duplicate_keys(tmp_path):
    path=tmp_path/"settings.json"
    write_json(path,{"categories":[],"hotkeys":dict(DEFAULT_KEYS)})
    assert read_settings(path)["categories"]==[]
    write_json(path,{"categories":[],"hotkeys":{k:"F9" for k in DEFAULT_KEYS}})
    assert read_settings(path)["hotkeys"]==DEFAULT_KEYS
    path.write_text("bad json")
    assert read_settings(path)["hotkeys"]==DEFAULT_KEYS


def test_missing_reference_never_becomes_synthetic(tmp_path):
    with pytest.raises(ReferenceUnavailable): load_pack(tmp_path)


def test_reference_requires_permissions_and_matching_coordinates(tmp_path):
    (tmp_path/"manifest.json").write_text(json.dumps({"region":"mondstadt","layer":"surface",
                                                  "coordinate_system":"leaflet-simple-z7"}))
    with pytest.raises(ReferenceUnavailable): load_pack(tmp_path)


def test_low_detail_template_cannot_classify_menu():
    assert not template_visible(np.zeros((200,200,3),np.uint8),np.zeros((20,20,3),np.uint8),(0,0,1,1))


@pytest.fixture
def textured_reference():
    # Synthetic image used ONLY for deterministic geometry assertions.
    rng=np.random.default_rng(19)
    image=np.zeros((700,700,3),np.uint8)
    for _ in range(800):
        x,y=rng.integers(8,692,2)
        color=tuple(int(v) for v in rng.integers(40,255,3))
        cv2.circle(image,(int(x),int(y)),int(rng.integers(2,8)),color,-1)
    return image


def test_matching_reacquires_zoom_and_teleport_without_previous_transform(textured_reference):
    matcher=TerrainMatcher(Terrain(textured_reference,np.array([[1,0,0],[0,1,0]],dtype=float),"test"))
    for tx,ty in [(-50,-40),(-230,-200)]:
        truth=np.array([[1.1,0,tx],[0,1.1,ty]],dtype=float)
        frame=cv2.warpAffine(textured_reference,truth,(480,400))
        result=matcher.match(frame)
        assert result is not None
        # Held-out point never passed as a calibration/control point.
        point=np.array([300,300,1])
        assert np.linalg.norm(result[0]@point-truth@point)<2
    assert matcher.match(np.zeros((400,480,3),np.uint8)) is None


def test_minimap_crop_mask_preserves_global_screen_coordinates(textured_reference):
    matcher=TerrainMatcher(Terrain(textured_reference,np.array([[1,0,0],[0,1,0]],dtype=float),"test"))
    frame=textured_reference.copy()
    mask=np.zeros(frame.shape[:2],np.uint8);cv2.circle(mask,(250,230),80,255,-1)
    result=matcher.match(frame,mask)
    assert result is not None
    assert np.linalg.norm(result[0]@np.array([250,230,1])-[250,230])<1


def test_motion_tracks_drag_zoom_without_waiting_for_absolute_match(textured_reference):
    image=cv2.cvtColor(textured_reference,cv2.COLOR_BGR2GRAY)
    matrix=cv2.getRotationMatrix2D((350,350),1.5,1.03)
    matrix[:,2]+=[12,-8]
    moved=cv2.warpAffine(image,matrix,(700,700))
    current=observation(surface="map")
    result=follow(image,moved,current,100.05)
    assert result is not None and result.fresh(100.1)
    point=np.array([330,310,1])
    assert np.linalg.norm(result.world_to_screen@point-matrix@point)<1.5


def test_motion_rejects_teleport_instead_of_retaining_old_coordinates(textured_reference):
    image=cv2.cvtColor(textured_reference,cv2.COLOR_BGR2GRAY)
    blank=np.zeros_like(image)
    assert follow(image,blank,observation(surface="map"),100.05) is None


def test_settings_unhashable_key_value_recovers_defaults(tmp_path):
    path=tmp_path/"settings.json"
    write_json(path,{"categories":[],"hotkeys":{"visibility":[],"collect":"F9","undo":"F10"}})
    assert read_settings(path)["hotkeys"]==DEFAULT_KEYS


def test_ctrl_reveals_collected_for_hit_testing_and_unmark(session):
    session.selected={"anemoculus"}
    assert session.set_collected("real:a",True)
    assert session.pins(600,400,100)==[]
    revealed=session.pins(600,400,100,include_collected=True)
    assert [p.item.id for p in revealed]==["real:a"]
    assert [i.id for i in session.hit_test(600,400,105,100,100)]==["real:a"]
    assert session.set_collected("real:a",False)
    assert [p.item.id for p in session.pins(600,400,100)]==["real:a"]
    assert not ProgressManager(session.progress.filepath).is_collected("real:a")


def test_hit_testing_rejects_stale_hidden_and_unselected_markers(session):
    assert session.hit_test(600,400,105,100,100)==[]
    session.selected={"anemoculus"}
    assert session.hit_test(600,400,105,100,101)==[]
    session.hidden=True
    assert session.hit_test(600,400,105,100,100)==[]


def test_overlapping_marker_hit_returns_each_id_without_changing_progress(session):
    # Two overlapping legacy symbols: independent of personal chest artwork.
    session.items.append(Item('real:overlap','Overlap','anemoculus',110,100))
    session.selected={"anemoculus"}
    hits=session.hit_test(600,400,112,100,100)
    assert {i.id for i in hits}=={"real:a","real:overlap"}
    assert session.progress.collected_count==0


def test_menu_collection_works_on_map_away_from_player(session):
    session.selected={"anemoculus"}
    session.observation=observation(surface="map")
    assert session.collect(100) is False
    assert session.set_collected("real:c",True)
    assert not session.set_collected("real:c",True)
    assert not session.set_collected("unknown",True)
    assert session.undo()
    assert not session.progress.is_collected("real:c")


def test_unmark_failure_restores_exact_record(session,monkeypatch):
    session.set_collected("real:a",True)
    record=dict(session.progress.get_collection_record("real:a"))
    monkeypatch.setattr(session.progress,"save",lambda:(_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError): session.set_collected("real:a",False)
    assert session.progress.get_collection_record("real:a")==record


def test_detailed_minimap_blocks_preserve_world_projection_and_skip_empty_edges(textured_reference,monkeypatch):
    from src.live.reference import ReferencePack
    from src.live.vision import ScreenRecognizer
    import src.live.vision as vision
    matrix=np.array([[2.,0,-50],[0,2.,-40]])
    coarse=Terrain(textured_reference,np.array([[1.,0,0],[0,1.,0]]),'coarse')
    detail=Terrain(textured_reference,matrix,'detail')
    blank=Terrain(np.zeros((100,100,3),np.uint8),matrix,'empty edge')
    pack=ReferencePack(coarse,textured_reference,textured_reference,(0,0,1,1),(0,0,1,1),minimap_terrain=(blank,detail))
    recognizer=ScreenRecognizer(pack)
    monkeypatch.setattr(vision,'template_visible',lambda frame,template,roi:template is pack.gameplay_ui)
    # Distinct UI arrays so the map check cannot classify gameplay.
    object.__setattr__(pack,'map_ui',textured_reference.copy())
    monkeypatch.setattr(vision,'detect_circle',lambda frame:(350.,350.,280.))
    result=recognizer.observe(textured_reference,100)
    assert len(recognizer.minimap_matchers)==1 and result.surface=='minimap'
    assert result.world_to_screen==pytest.approx(matrix,abs=.1)
    assert result.player==pytest.approx((200,195),abs=.1)
    assert recognizer.last_minimap_matcher is recognizer.minimap_matchers[0]
    monkeypatch.setattr(vision,'template_visible',lambda *args:True)
    result=recognizer.observe(textured_reference,101)
    assert result.surface=='map'
    assert result.world_to_screen==pytest.approx(np.array([[1.,0,0],[0,1.,0]]),abs=.1)


def test_manifest_keeps_minimap_rasters_separate_and_checks_their_hash(tmp_path,textured_reference):
    image=cv2.imencode('.png',textured_reference)[1].tobytes()
    (tmp_path/'terrain.png').write_bytes(image)
    entry={'file':'terrain.png','sha256':hashlib.sha256(image).hexdigest()}
    matrix=[[1,0,0],[0,1,0]]
    data={'region':'mondstadt','map_id':'teyvat','layer':'surface','coordinate_system':'leaflet-simple-z7',
          'source':'test','permission':{'usage':'test','evidence':'test'},'world_to_image':matrix,
          'terrain':entry,'map_ui':{**entry,'roi':[0,0,1,1]},'gameplay_ui':{**entry,'roi':[0,0,1,1]},
          'extra_terrain':[{**entry,'world_to_image':matrix,'surface':'minimap'}]}
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(data))
    pack=load_pack(tmp_path)
    assert len(pack.minimap_terrain)==1 and pack.extra_terrain==()
    data['extra_terrain'][0]['sha256']='0'*64;manifest.write_text(json.dumps(data))
    with pytest.raises(ReferenceUnavailable):load_pack(tmp_path)


def test_white_hud_confirmation_rejects_empty_or_unrelated_shapes():
    from src.live.vision import foreground_ui_visible
    rng=np.random.default_rng(801)
    template=np.zeros((40,40,3),np.uint8);template[:]=(70,80,50)
    for x,y in rng.integers(5,35,(15,2)):cv2.circle(template,(int(x),int(y)),3,(250,250,250),-1)
    frame=np.zeros((160,200,3),np.uint8);frame[:]=(150,90,20)
    frame[20:60,20:60]=template
    # Replace the old scene behind the glyph, preserving its white foreground.
    patch=frame[20:60,20:60];patch[np.any(patch<205,axis=2)]=(170,30,100)
    assert foreground_ui_visible(frame,template,(0,0,1,1))
    assert not foreground_ui_visible(np.zeros_like(frame),template,(0,0,1,1))
    assert not foreground_ui_visible(np.full_like(frame,250),template,(0,0,1,1))
    other=np.zeros_like(frame);cv2.rectangle(other,(20,20),(60,60),(250,250,250),-1)
    assert not foreground_ui_visible(other,template,(0,0,1,1))
