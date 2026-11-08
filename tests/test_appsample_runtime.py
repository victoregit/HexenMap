import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.live.appsample_catalog import project,source_layer,normalized_package,SPACE
from src.live.appsample_import import AppSamplePoint
from src.live.appsample_runtime import import_records
from src.live.catalog import Item
from src.live.regions import RegionalCatalog
from src.live.session import Session
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager,ProgressStorageError


def item(identifier='1',**kwargs):
    return Item('appsample:marker:'+identifier,'Baú','common-chest',300,200,
                region_id='appsample',map_id='as-map-2',rule_id='permanent',**kwargs)


def test_projection_uses_the_published_centered_webmercator_tile_scheme():
    zoom=12;x_tile=-4;y_tile=-10
    lng=(x_tile+.5)*360/2**zoom
    latitude=math.degrees(math.atan(math.sinh(-2*math.pi*(y_tile+.5)/2**zoom)))
    x,y=project(lng,latitude,zoom)
    assert x==pytest.approx((x_tile+.5)*256)
    assert y==pytest.approx((y_tile+.5)*256)
    assert project(0,0)==pytest.approx((0,0),abs=1e-8)
    # URL source-Y is -1 minus the top-down centered tile index.
    assert -math.floor(y/256)-1==9


def test_layer_without_floor_stays_underground_and_package_retains_source_ids():
    assert source_layer('l=35795|45|')=='as-layer-45-0'
    points=[AppSamplePoint('1','o17',2,6,.5,.2,''),
            AppSamplePoint('2','o17',7,6,.4,.1,'l=123|45|5')]
    items,categories=normalized_package(points,[])
    assert [i['id'] for i in items]==['appsample:marker:1','appsample:marker:2']
    assert items[1]['layer_id']=='as-layer-45-5' and items[1]['map_id']=='as-map-7'
    assert items[0]['x']!=.5 and categories['common-chest']['name']=='Baús comuns'


def test_personal_catalog_is_opt_in_and_validates_source_hash(tmp_path):
    community=Path(__file__).resolve().parents[1]/'data/community'
    catalog=RegionalCatalog(community,tmp_path)
    assert not catalog.accepts('appsample')
    directory=tmp_path/'appsample';directory.mkdir()
    row={'id':'appsample:marker:1','name':'Baú','category':'common-chest','x':10,'y':20,
         'region_id':'appsample','map_id':'as-map-2'}
    raw=json.dumps({'items':[row]}).encode();(directory/'markers.json').write_bytes(raw)
    source={'region_id':'appsample','coordinate_system':SPACE,'map_names':{'as-map-2':'Teyvat'},
            'categories':{'common-chest':{'name':'Baús comuns','group':'Baús'}},
            'files':[{'file':'markers.json','format':'normalized-v1','sha256':hashlib.sha256(raw).hexdigest()}]}
    (directory/'SOURCE.json').write_text(json.dumps(source))
    assert catalog.accepts('appsample')
    loaded=catalog.load_package('appsample')
    assert loaded.coordinate_system==SPACE and loaded.items[0].region_id=='appsample'
    assert set(catalog.regions)=={'appsample'} # Single operational package, no borrowed nations.
    (directory/'markers.json').write_text('{}')
    with pytest.raises(ValueError):catalog.load_package('appsample')


def test_import_resolves_exact_namespace_without_inventing_collection_times():
    records,missing,key=import_records(['1','2','3'],[item(),Item('kongying:marker:2','Other','common-chest',0,0)])
    assert list(records)==['appsample:marker:1'] and missing==['2','3']
    assert records['appsample:marker:1']['collected_at']==''
    assert 'ready_at' not in records['appsample:marker:1']
    assert key!=import_records(['1','2','3'],[item(),item('2')])[2]


def test_merge_preserves_old_records_and_keeps_immutable_backup(tmp_path):
    manager=ProgressManager(str(tmp_path/'progress.json'))
    old={'collected_at':'2020-01-01T00:00:00+00:00','rule_id':'elapsed','ready_at':'2030-01-01T00:00:00+00:00','notes':'Original'}
    manager.replace_record('kongying:old',old);manager.replace_record('appsample:marker:2',old);manager.save()
    before=Path(manager.filepath).read_bytes()
    records,missing,key=import_records(['1','2','9'],[item(),item('2')])
    result=manager.merge_imported_records(records,key,'appsample')
    assert result['added']==1 and Path(result['backup']).read_bytes()==before
    reloaded=ProgressManager(manager.filepath)
    assert reloaded.get_collection_record('kongying:old')==old
    assert reloaded.get_collection_record('appsample:marker:2')==old
    assert not reloaded.is_collected('appsample:marker:9') and missing==['9']


def test_reimport_and_later_catalog_resolution_do_not_recollect_manual_unmarks(tmp_path):
    manager=ProgressManager(str(tmp_path/'progress.json'))
    records,_,key=import_records(['1','2'],[item()])
    manager.merge_imported_records(records,key,'appsample')
    manager.mark_uncollected('appsample:marker:1');manager.save()
    assert manager.merge_imported_records(records,key,'appsample')['repeated']
    manager=ProgressManager(manager.filepath)
    records,_,new_key=import_records(['1','2'],[item(),item('2')])
    result=manager.merge_imported_records(records,new_key,'appsample')
    assert result['added']==1 and manager.is_collected('appsample:marker:2')
    assert not manager.is_collected('appsample:marker:1')


def test_save_failure_restores_memory_and_original_file(tmp_path,monkeypatch):
    manager=ProgressManager(str(tmp_path/'progress.json'));manager.mark_collected('legacy');manager.save()
    original=Path(manager.filepath).read_bytes();metadata=copy.deepcopy(manager._metadata)
    records,_,key=import_records(['1'],[item()])
    def fail():raise ProgressStorageError('Write failed')
    monkeypatch.setattr(manager,'save',fail)
    with pytest.raises(ProgressStorageError):manager.merge_imported_records(records,key,'appsample')
    assert manager.get_collected_ids()=={'legacy'} and manager._metadata==metadata
    assert Path(manager.filepath).read_bytes()==original


def test_imported_items_hide_normally_and_reappear_with_ctrl_in_the_same_scope(tmp_path):
    manager=ProgressManager(str(tmp_path/'progress.json'))
    records,_,key=import_records(['1'],[item()]);manager.merge_imported_records(records,key,'appsample')
    session=Session([item(),Item('kongying:other','Other','common-chest',300,200,region_id='snezhnaya')],manager)
    session.region_id='appsample';session.map_id='as-map-2';session.layer_id='surface';session.selected={'common-chest'}
    session.observation=Observation('map',100,np.array([[1.,0,0],[0,1.,0]]),.95,.2,map_id='as-map-2',layer_id='surface')
    assert session.pins(600,400,100)==[]
    assert [pin.item.id for pin in session.pins(600,400,100,include_collected=True)]==['appsample:marker:1']
    session.selected=set();assert session.pins(600,400,100,include_collected=True)==[]
