from datetime import datetime,timedelta,timezone
import json
from pathlib import Path

import numpy as np
import pytest

from src.live.catalog import Item
from src.live.regions import RegionalCatalog
from src.live.respawn import RespawnRule,parse_utc
from src.live.session import Session
from src.live.storage import read_settings,write_json
from src.live.territory import Territory,TerritoryIndex
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager

UTC=timezone.utc
NOW=datetime(2026,11,6,8,59,59,tzinfo=UTC)


def rule(kind='elapsed',seconds=24*3600):
    return RespawnRule('verified',kind,seconds=seconds,source='https://example.org/verified',checked_at='2026-11-06')


def session(tmp_path):
    s=Session([Item('resource','Ore','ore',210,100,area_id='locality',rule_id='verified'),
               Item('permanent','Chest','common-chest',220,100,area_id='area'),
               Item('unknown','Plant','plant',230,100,rule_id='unknown'),
               Item('other','Chest','common-chest',220,100,region_id='liyue')],
              ProgressManager(str(tmp_path/'progress.json')))
    s.clock=lambda:NOW
    s.rules['verified']=rule()
    s.region_id='mondstadt';s.map_id='teyvat';s.layer_id='surface'
    s.selected={'ore','common-chest','plant'}
    s.territories=TerritoryIndex([Territory('area','Area',None,'mondstadt'),
                                Territory('locality','Locality','area','mondstadt')])
    return s


def test_descendants_deduplicate_multiarea_and_unknown_is_explicit(tmp_path):
    s=session(tmp_path)
    s.items.append(Item('multiple','Chest','common-chest',220,100,area_id='area',area_ids=('area','locality')))
    s.area_id='area'
    assert {i.id for i in s.scoped_items()}=={'resource','permanent','multiple'}
    assert s.collection_counts()['common-chest'].total==2
    s.area_id='locality'
    assert {i.id for i in s.scoped_items()}=={'resource','multiple'}
    s.area_id='unclassified'
    assert {i.id for i in s.scoped_items()}=={'unknown'}


def test_utc_expiry_at_boundary_after_restart_and_timezone_change(tmp_path):
    s=session(tmp_path);s.set_collected('resource',True);s.set_collected('permanent',True)
    record=s.get_collection_record('resource')
    end=parse_utc(record['ready_at'])
    for offset in [-7,0,9]:
        restarted=session(tmp_path)
        restarted.clock=lambda:end.astimezone(timezone(timedelta(hours=offset)))-timedelta(microseconds=1)
        assert restarted.is_collected('resource')
        restarted.clock=lambda:end.astimezone(timezone(timedelta(hours=offset)))
        assert not restarted.is_collected('resource')
        assert restarted.is_collected('permanent')
        assert 'estimada' in restarted.respawn_text(restarted.items[0])


def test_unknown_and_permanent_never_get_invented_timers(tmp_path):
    s=session(tmp_path)
    s.set_collected('unknown',True)
    assert 'ready_at' not in s.get_collection_record('unknown')
    s.clock=lambda:NOW+timedelta(days=1000)
    assert s.is_collected('unknown')
    assert s.respawn_text(s.items[2])=='Reposição não confirmada'


def test_unmark_and_undo_restore_exact_original_deadline(tmp_path):
    s=session(tmp_path);s.set_collected('resource',True)
    old=dict(s.get_collection_record('resource'))
    s.clock=lambda:NOW+timedelta(hours=3)
    s.set_collected('resource',False)
    assert s.get_collection_record('resource') is None
    assert s.undo()
    assert s.get_collection_record('resource')==old
    s.clock=lambda:NOW+timedelta(days=2)
    s.set_collected('resource',True)
    assert s.get_collection_record('resource')['ready_at']!=old['ready_at']
    s.undo()
    assert s.get_collection_record('resource')==old
    assert not s.is_collected('resource')


def test_america_reset_and_elapsed_have_distinct_policies():
    reset=rule('server_reset')
    assert reset.deadline(NOW)==datetime(2026,11,6,9,tzinfo=UTC)
    assert reset.deadline(NOW+timedelta(seconds=1))==datetime(2026,11,7,9,tzinfo=UTC)
    assert rule(seconds=12*3600).deadline(NOW)==NOW+timedelta(hours=12)
    assert rule(seconds=46*3600).deadline(NOW)==NOW+timedelta(hours=46)
    with pytest.raises(ValueError): RespawnRule('bad','elapsed',seconds=72*3600)


def test_different_map_or_layer_never_draws_or_collects(tmp_path):
    s=session(tmp_path)
    s.observation=Observation('minimap',10,np.array([[1,0,0],[0,1,0]]),1,0,(210,100,70),(210,100),map_id='chasm',layer_id='surface')
    assert s.pins(600,400,now=10)==[]
    assert s.candidates(10)==[]
    s.observation=Observation('minimap',10,np.array([[1,0,0],[0,1,0]]),1,0,(210,100,70),(210,100),map_id='teyvat',layer_id='underground')
    assert s.pins(600,400,now=10)==[]
    assert s.candidates(10)==[]


def test_migration_keeps_original_backup_and_unmapped_ids(tmp_path):
    path=tmp_path/'progress.json'
    original=json.dumps({'version':1,'records':{'legacy:unmapped':{'collected_at':NOW.isoformat(),'notes':'keep'}}})
    path.write_text(original,encoding='utf-8')
    s=session(tmp_path);s.set_collected('resource',True)
    backup=Path(str(path)+'.pre-v2.bak')
    assert backup.read_text(encoding='utf-8')==original
    s.set_collected('resource',False)
    assert backup.read_text(encoding='utf-8')==original
    assert ProgressManager(str(path)).is_collected('legacy:unmapped')


def test_settings_archive_retired_provider_presets_without_cross_source_transfer(tmp_path):
    path=tmp_path/'settings.json';data={'package':'liyue','categories':['ore'],'regional':{'liyue':{'layer':'chasm / surface','categories':['ore']}}}
    write_json(path,data);original=path.read_bytes();loaded=read_settings(path)
    assert loaded['package']=='appsample' and loaded['regional']=={} and loaded['categories']==[]
    assert path.with_name('settings.json.pre-appsample-only.bak').read_bytes()==original


def test_only_appsample_catalog_defines_inventory_maps_and_rules(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path);items,_,_=catalogs.load('appsample')
    assert len({i.id for i in items})==len(items)
    assert {m['id'] for m in catalogs.inventory['maps']}=={'as-map-2','as-map-3'}
    assert all(i.rule_id in catalogs.rules for i in items)
    assert set(catalogs.rules)=={'permanent','unknown'} and catalogs.inventory['coverage_complete'] is False


def test_undo_respects_selected_region_and_area(tmp_path):
    s=session(tmp_path);s.set_collected('resource',True)
    s.region_id='liyue';s.set_collected('other',True)
    s.region_id='mondstadt';s.area_id='locality'
    assert s.undo()
    assert not s.is_collected('resource') and s.is_collected('other')
    assert not s.undo()
    s.region_id='liyue';s.area_id=None
    assert s.undo() and not s.is_collected('other')


def test_retired_package_ids_are_rejected_instead_of_falling_back(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path)
    for provider in ('mondstadt','liyue','sumeru','legacy-mondstadt'):
        assert not catalogs.accepts(provider)
        with pytest.raises(ValueError):catalogs.load_package(provider)


def test_appsample_native_layers_are_preserved_without_borrowed_territories(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path);items,_,_=catalogs.load('appsample')
    cave=next(i for i in items if i.layer_id!='surface')
    assert cave.map_id=='as-map-3' and cave.layer_ids==('as-layer-1-1',)
    assert not catalogs.territories.nodes


def test_automatic_layers_use_visual_evidence_and_reject_ambiguous_artwork():
    from src.live.reference import ReferencePack,Terrain
    from src.live.vision import LayerRecognizer
    rng=np.random.default_rng(49)
    images=[rng.integers(0,256,(320,320,3),dtype=np.uint8) for _ in range(2)]
    ui=rng.integers(0,256,(24,24,3),dtype=np.uint8)
    def pack(index,layer):
        return ReferencePack(Terrain(images[index],np.array([[1,0,0],[0,1,0.]]),'synthetic'),ui,ui,
                             (.85,0,.15,.15),(0,0,.1,.1),map_id='teyvat',layer_id=layer)
    a,b=pack(0,'floor-a'),pack(1,'floor-b')
    recognizer=LayerRecognizer([lambda:a,lambda:b])
    def frame(index):
        value=np.zeros((400,600,3),dtype=np.uint8)
        value[40:360,140:460]=images[index]
        value[5:29,550:574]=ui
        return value
    assert recognizer.observe(frame(0),10).layer_id=='floor-a'
    assert recognizer.observe(frame(1),11).layer_id=='floor-b'
    ambiguous=LayerRecognizer([lambda:a,lambda:pack(0,'floor-duplicate')])
    assert ambiguous.observe(frame(0),12).surface=='hidden'


def test_occluded_minimap_anchors_to_arrow_and_only_uses_inscribed_disk(monkeypatch):
    import cv2
    from src.live.vision import detect_circle
    frame=np.zeros((400,600,3),dtype=np.uint8)
    cv2.fillConvexPoly(frame,np.array([[65,41],[59,53],[71,53]]), (255,255,0))
    monkeypatch.setattr(cv2,'HoughCircles',lambda *a,**k:np.array([[[52.,45.,45.]]],dtype=np.float32))
    circle=detect_circle(frame)
    assert circle is not None
    x,y,r=circle
    assert abs(x-65)<1 and 41<y<54
    assert r+np.hypot(x-52,y-45)<=45.0001
    assert detect_circle(np.zeros_like(frame)) is None


def test_automatic_map_selection_never_projects_a_different_map(tmp_path):
    s=session(tmp_path)
    s.items.append(Item('chasm','Ore','ore',210,100,map_id='chasm'))
    s.map_id=None;s.layer_id=None
    s.observation=Observation('minimap',10,np.array([[1,0,0],[0,1,0]]),1,0,(210,100,70),(210,100),map_id='chasm',layer_id='surface')
    assert [p.item.id for p in s.pins(600,400,now=10)]==['chasm']
    assert [i.id for i in s.candidates(10)]==['chasm']


def test_appsample_unknown_resources_never_inherit_another_provider_timer(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path);items,_,_=catalogs.load('appsample')
    resource=next(i for i in items if i.category=='flower')
    assert catalogs.rules[resource.rule_id].kind=='unknown'
    assert catalogs.rules[resource.rule_id].deadline(NOW) is None


def test_permanent_and_unconfirmed_rules_ignore_old_predicted_deadlines(tmp_path):
    s=session(tmp_path)
    for identifier in ['permanent','unknown']:
        s.progress.replace_record(identifier,{'collected_at':NOW.isoformat(),'ready_at':(NOW-timedelta(days=1)).isoformat(),'rule_id':'verified'})
        assert s.is_collected(identifier)
    assert s.respawn_text(s.items[2])=='Reposição não confirmada'


def test_catalog_has_no_runtime_dependency_on_community_files(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path)
    assert not catalogs.community.exists()
    assert catalogs.load_package('appsample').items
    assert catalogs.default_package(tmp_path/'references')=='appsample'
