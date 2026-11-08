from dataclasses import replace
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytest

from src.live.reference_store import Raster,Block,PackSpec,blocks,FeatureCache,ReferenceStore,read_spec,CACHE_BYTES,TILE_SIDE
from src.live.reference import ReferenceUnavailable,ReferenceCancelled
from src.live.budget_vision import BudgetRecognizer


@pytest.fixture
def raster(tmp_path):
    image=np.random.default_rng(19).integers(0,256,(512,512),dtype=np.uint8)
    image=cv2.GaussianBlur(image,(3,3),0)
    path=tmp_path/'terrain.png';Image.fromarray(image).save(path)
    return Raster(path,hashlib.sha256(path.read_bytes()).hexdigest(),np.eye(2,3),512,512,'map',0)


def test_partition_limits_overlap_and_world_coordinates(raster):
    raster=replace(raster,width=4200,height=2240,matrix=np.array([[2.,0,400],[0,2.,900]]))
    tiles=list(blocks(raster))
    assert len(tiles)==6
    assert all(b.box[2]-b.box[0]<=2048 and b.box[3]-b.box[1]<=2048 for b in tiles)
    assert tiles[0].box[2]-tiles[1].box[0]==128
    for y in range(0,2240,20):
        for x in range(0,4200,20):assert any(a<=x<c and b<=y<d for a,b,c,d in (t.box for t in tiles))
    block=tiles[-1];world=np.array([1200.,800.,1.])
    assert block.matrix@world==pytest.approx(raster.matrix@world-np.array(block.box[:2]))
    assert len(list(blocks(replace(raster,width=TILE_SIDE-127,height=512))))==1


def test_metadata_does_not_decode_terrain_and_rejects_bad_geometry(tmp_path,raster,monkeypatch):
    template={'file':'terrain.png','sha256':raster.digest,'roi':[0,0,.2,.2]}
    data={'region':'test','map_id':'map','layer':'surface','coordinate_system':'pixels',
          'permission':{'evidence':'provided','usage':'personal'},'terrain':template,'world_to_image':[[1,0,0],[0,1,0]],
          'map_ui':template,'gameplay_ui':template}
    (tmp_path/'manifest.json').write_text(json.dumps(data))
    calls=[];decode=cv2.imdecode
    def track(*args):calls.append(1);return decode(*args)
    monkeypatch.setattr(cv2,'imdecode',track)
    spec=read_spec(tmp_path,'test','map','surface','pixels')
    assert len(calls)==2 and spec.rasters[0].width==512
    data['world_to_image']=[[0,0,0],[0,0,0]]
    (tmp_path/'manifest.json').write_text(json.dumps(data))
    with pytest.raises(ReferenceUnavailable):read_spec(tmp_path,'test','map','surface','pixels')


def test_indices_persist_rebuild_corruption_and_verify_original(raster,tmp_path):
    cache=FeatureCache(tmp_path/'cache');block=Block(raster,(0,0,512,512))
    points,desc=cache.features(block);assert len(points)>20 and cache.builds==1
    second=FeatureCache(tmp_path/'cache');p,d=second.features(block)
    assert second.builds==0 and np.array_equal(desc,d)
    (tmp_path/'cache'/(block.key+'.npz')).write_bytes(b'broken')
    second.features(block);assert second.builds==1
    raster.path.write_bytes(b'changed')
    with pytest.raises(ReferenceUnavailable):second.features(block)


def test_light_evicts_before_third_block_global_retains_selected_blocks(raster,tmp_path):
    features=FeatureCache(tmp_path/'cache')
    tiles=[Block(raster,box) for box in ((0,0,320,320),(128,0,448,320),(0,128,320,448))]
    light=ReferenceStore(features)
    for tile in tiles:light.get(tile)
    assert len(light.cache)==2 and tiles[0].key not in light.cache and light.bytes<CACHE_BYTES
    light.get(tiles[0]);assert features.hits>=1
    light.close();assert light.bytes==0 and not light.cache
    global_store=ReferenceStore(features,'global')
    for tile in tiles:global_store.get(tile)
    assert len(global_store.cache)==3


def pack_for(raster,layer='surface'):
    return PackSpec(np.ones((16,16,3),np.uint8),np.zeros((16,16,3),np.uint8),
                    (.8,0,.2,.2),(0,0,.2,.2),'test','map',layer,'pixels',(raster,))


def configure_gameplay(monkeypatch):
    import src.live.budget_vision as module
    monkeypatch.setattr(module,'template_visible',lambda frame,template,roi:False)
    monkeypatch.setattr(module,'foreground_ui_visible',lambda *a:True)
    monkeypatch.setattr(module,'confirmed_circle',lambda *a:(256.,256.,110.))


def test_cached_block_preserves_independent_geometry_and_current_timestamps(raster,tmp_path,monkeypatch):
    configure_gameplay(monkeypatch)
    recognizer=BudgetRecognizer([pack_for(raster)],tmp_path/'cache')
    frame=cv2.imread(str(raster.path))
    # The observation crop is not used to create/reference-calibrate the raster.
    observed=cv2.warpAffine(frame,np.array([[1.,0,11],[0,1.,-7]]),(512,512))
    observation=recognizer.observe(observed,10.)
    assert observation.surface=='minimap' and observation.captured_at==10.
    probes=np.array([[200,200,1],[280,200,1],[240,300,1.]])
    assert np.max(np.linalg.norm(probes@observation.world_to_screen.T-(probes[:,:2]+[11,-7]),axis=1))<2
    assert observation.fresh(10.1) and not observation.fresh(11.)
    assert recognizer.diagnostics()['resident_blocks']<=2


def test_identical_different_layers_are_ambiguous(raster,tmp_path,monkeypatch):
    configure_gameplay(monkeypatch)
    other=replace(raster,pack_index=1)
    recognizer=BudgetRecognizer([pack_for(raster),pack_for(other,'cave')],tmp_path/'cache')
    observation=recognizer.observe(cv2.imread(str(raster.path)),10.)
    assert observation.surface=='hidden' and observation.reason=='Camada ambígua'


def test_cancelled_reference_does_not_build_or_publish(raster,tmp_path):
    with pytest.raises(ReferenceCancelled):BudgetRecognizer([pack_for(raster)],tmp_path/'cache',cancelled=lambda:True)


def test_overlap_copies_do_not_disqualify_a_valid_native_minimap_location(raster,tmp_path,monkeypatch):
    configure_gameplay(monkeypatch)
    native=replace(raster,surface='minimap',map_compatible=True)
    duplicate=replace(native)
    recognizer=BudgetRecognizer([replace(pack_for(native),rasters=(native,duplicate))],tmp_path/'cache')
    frame=cv2.imread(str(raster.path))
    observation=recognizer.observe(frame,10.)
    assert observation.surface=='minimap' and observation.error_px<2
    assert recognizer.diagnostics()['resident_blocks']<=2


def test_global_memory_guard_releases_partial_store(raster,tmp_path,monkeypatch):
    import psutil
    from types import SimpleNamespace
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=1024))
    with pytest.raises(MemoryError):BudgetRecognizer([pack_for(raster)],tmp_path/'cache','global')


def test_global_automatic_map_choice_does_not_load_all_maps(raster,tmp_path,monkeypatch):
    configure_gameplay(monkeypatch)
    other_path=tmp_path/'other.png'
    Image.fromarray(np.random.default_rng(800).integers(0,256,(512,512),dtype=np.uint8)).save(other_path)
    other=replace(raster,path=other_path,digest=hashlib.sha256(other_path.read_bytes()).hexdigest(),pack_index=1)
    other_pack=replace(pack_for(other),map_id='other-map')
    recognizer=BudgetRecognizer([pack_for(raster),other_pack],tmp_path/'cache','global')
    assert recognizer.global_map is None and not recognizer.store.cache
    obs=recognizer.observe(cv2.imread(str(raster.path)),10.)
    assert obs.surface=='minimap' and obs.map_id=='map'
    assert recognizer.global_map=='map'
    assert {value.block.raster.pack_index for value in recognizer.store.cache.values()}=={0}
