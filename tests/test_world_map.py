import json
from types import SimpleNamespace
import numpy as np
from PIL import Image
from src.live.world_tiles import WorldTiles,screen_to_world
from src.live.world_index import WorldIndex
from src.live.catalog import Item
from src.live.session import Session
from src.progress.progress_manager import ProgressManager


def test_world_index_filters_source_map_layer_categories_and_collection():
    items=[Item('surface','Baú','common-chest',10,20,map_id='as-map-2'),
           Item('cave','Baú','common-chest',10,20,map_id='as-map-2',layer_id='cave'),
           Item('other','Baú','common-chest',10,20,map_id='another')]
    index=WorldIndex(items)
    assert [i.id for i in index.items]==['surface']
    assert index.query((0,0,30,30),set()).size==0
    assert index.query((0,0,30,30),{'common-chest'}).tolist()==[0]
    assert index.query((0,0,30,30),{'common-chest'},{'surface'}).size==0
    assert index.query((0,0,5,5),{'common-chest'}).size==0


def test_zoom_anchoring_and_tile_coordinate_units():
    assert screen_to_world(500,300,1000,600,100,-200,14)==(100,-200)
    assert screen_to_world(600,300,1000,600,100,-200,15)==(150,-200)
    from src.live.world_map import WorldMap
    canvas=SimpleNamespace(winfo_width=lambda:1000,winfo_height=lambda:600)
    view=SimpleNamespace(canvas=canvas,cx=100.,cy=-200.,zoom=14.,close_card=lambda:None,
        invalidate=lambda:None,tiles=SimpleNamespace(bounds=(-10000,-10000,10000,10000)))
    view.clamp=lambda:WorldMap.clamp(view)
    before=screen_to_world(600,350,1000,600,view.cx,view.cy,view.zoom)
    WorldMap.zoom_at(view,.5,600,350)
    np.testing.assert_allclose(screen_to_world(600,350,1000,600,view.cx,view.cy,view.zoom),before)


def test_local_tiles_use_parent_fallback_and_correct_y_without_network(tmp_path):
    directory=tmp_path/'12';directory.mkdir()
    image=Image.new('RGB',(256,256),'red');image.paste('blue',(128,128,256,256));image.save(directory/'-1_-1.jpg')
    tiles=WorldTiles(tmp_path)
    try:
        tile=tiles.load((14,-1,-1,128))
        assert tile.size==(128,128)
        assert tile.getpixel((64,64))[2]>200
        assert tiles.load((14,20,20,128)) is None
    finally:tiles.close()


def test_world_collection_uses_explicit_map_scope_without_changing_overlay(tmp_path):
    items=[Item('surface','Baú','common-chest',10,20,map_id='as-map-2'),
           Item('cave','Baú','common-chest',10,20,map_id='as-map-2',layer_id='cave')]
    session=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    session.map_id='as-map-2';session.layer_id='cave'
    assert session.set_collected('surface',True,map_scope=('as-map-2','surface'))
    assert session.is_collected('surface') and session.layer_id=='cave'
    assert not session.set_collected('cave',True,map_scope=('as-map-2','surface'))
    assert session.undo(map_scope=('as-map-2','surface'))
    assert not session.is_collected('surface') and session.layer_id=='cave'
