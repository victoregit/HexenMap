from concurrent.futures import Future
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from src.live.automatic_maps import AutomaticMapSearch, Confirmation
from src.live.catalog import Item
from src.live.map_registry import maps, tile_metadata
from src.live.session import Session
from src.live.storage import read_settings, write_json
from src.live.vision import Observation
from src.live.world_index import WorldIndex
from src.live.world_tiles import WorldTiles
from src.progress.progress_manager import ProgressManager


def observation(stamp=1.,map_id='as-map-7'):
    return Observation('map',stamp,np.eye(2,3),.9,.2,map_id=map_id,layer_id='surface')


def test_published_map_identities_and_extents_do_not_depend_on_markers():
    assert set(maps())=={'as-map-2','as-map-7','as-map-9','as-map-34','as-map-36','as-map-37','as-map-40'}
    for map_id,row in maps().items():
        meta=tile_metadata(map_id)
        a,b,c,d=meta['bounds_base_tiles']
        source=row['tile_bounds']['12']
        assert (a,c)==(source['minX'],source['maxX'])
        assert (b,d)==(-source['maxY']-1,-source['minY']-1)
        assert row['names']['pt-BR'] and row['names']['en-US']
    assert tile_metadata('as-map-2')['bounds_base_tiles']==[-8,-12,7,7]


def test_confirmation_requires_three_distinct_frames_and_rejects_failures():
    gate=Confirmation()
    assert gate.accept(observation(1)) is None
    assert gate.accept(observation(1)) is None and gate.count==1
    assert gate.accept(observation(2)) is None
    assert gate.accept(Observation('hidden',3)) is None and gate.count==0
    for stamp in (4,5):assert gate.accept(observation(stamp)) is None
    assert gate.accept(observation(6))==('as-map-7','surface')
    assert gate.accept(observation(7,'as-map-9')) is None and gate.count==1
    assert gate.accept(replace(observation(8),confidence=.1)) is None and gate.count==0


def test_stable_tracking_does_not_start_search_or_load_indices(tmp_path):
    search=AutomaticMapSearch([('as-map-2','surface'),('as-map-7','surface')],
                              ('as-map-2','surface'),tmp_path,tmp_path,None)
    try:
        for stamp in range(100):assert search.tick(None,stamp,observation(stamp,'as-map-2')) is None
        assert search.future is None and search.router is None and not search.searching
    finally:search.close()


def test_coarse_false_positive_cannot_starve_other_maps(tmp_path):
    scopes=[('as-map-2','surface'),('as-map-7','surface'),('as-map-9','surface')]
    search=AutomaticMapSearch(scopes,scopes[0],tmp_path,tmp_path,None)
    try:
        assert search._next_scope([scopes[1]])==scopes[1]
        assert search._next_scope([scopes[1]])==scopes[2]
    finally:search.close()


def test_normal_minimap_alignment_gaps_never_launch_other_map_indices(tmp_path):
    scopes=[('as-map-2','surface'),('as-map-7','surface')]
    search=AutomaticMapSearch(scopes,scopes[0],tmp_path,tmp_path,None)
    frame=np.zeros((20,20,3),np.uint8)
    try:
        search.tick(frame,0,observation(0,'as-map-2'),surface='minimap')
        for stamp in range(1,31):search.tick(frame,stamp,Observation('hidden',stamp),surface='minimap')
        assert search.future is None and search.router is None and not search.searching
    finally:search.close()


def test_chest_reward_wave_pauses_map_discovery_without_loading_references(tmp_path):
    scopes=[('as-map-2','surface'),('as-map-7','surface')]
    search=AutomaticMapSearch(scopes,scopes[0],tmp_path,tmp_path,None)
    frame=np.zeros((20,20,3),np.uint8)
    try:
        for stamp in range(20):search.tick(frame,stamp,Observation('hidden',stamp),surface='map',paused=True)
        assert search.future is None and not search.searching
    finally:search.close()


def test_search_waits_for_loss_and_rejects_stale_context_and_old_frames(tmp_path):
    search=AutomaticMapSearch([('as-map-2','surface'),('as-map-7','surface')],
                              ('as-map-2','surface'),tmp_path,tmp_path,None)
    search.loss_grace=1.
    frame=np.zeros((20,20,3),np.uint8)
    calls=[]
    def probe(image,stamp,generation):
        calls.append(stamp)
        return generation,None,stamp
    search._probe=probe
    try:
        search.tick(frame,1,Observation('hidden',1))
        search.tick(frame,1.99,Observation('hidden',1.99))
        assert not calls and not search.searching
        search.tick(frame,2,Observation('hidden',2));search.future.result(timeout=2)
        search.tick(frame,2.5,Observation('hidden',2.5))
        assert calls==[2]
        old_generation=search.generation
        search.reset()
        search.future=Future();search.future.set_result((old_generation,('as-map-7','surface'),3))
        search.lost_since=2
        assert search.tick(frame,3,Observation('hidden',3)) is None
        if search.future:search.future.result(timeout=2)
        search.future=Future();search.future.set_result((search.generation,('as-map-7','surface'),3))
        assert search.tick(frame,10,Observation('hidden',10)) is None
        if search.future:search.future.result(timeout=2)
        search.future=Future();search.future.set_result((search.generation,('as-map-7','surface'),10))
        assert search.tick(frame,10.1,Observation('hidden',10.1))==('as-map-7','surface')
    finally:search.close()


def test_atlas_scope_keeps_coordinates_and_collections_separate(tmp_path):
    items=[Item('a','Chest','common-chest',10,10,map_id='as-map-2'),
           Item('b','Chest','common-chest',10,10,map_id='as-map-7')]
    session=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    session.map_id='as-map-2';session.layer_id='surface'
    a=WorldIndex(items,'as-map-2');b=WorldIndex(items,'as-map-7')
    assert [i.id for i in a.items]==['a'] and [i.id for i in b.items]==['b']
    assert not session.set_collected('a',True,map_scope=('as-map-7','surface'))
    assert session.set_collected('b',True,map_scope=('as-map-7','surface'))
    assert session.map_id=='as-map-2' and not session.is_collected('a')
    assert not session.undo(map_scope=('as-map-2','surface'))
    assert session.undo(map_scope=('as-map-7','surface'))


def test_tracking_mode_and_independent_atlas_survive_settings_roundtrip(tmp_path):
    path=tmp_path/'settings.json'
    write_json(path,{'categories':[],'tracking_mode':'manual','resolved_scope':['as-map-9','surface'],
                     'world_map':{'scope':['as-map-7','surface']}})
    settings=read_settings(path)
    assert settings['tracking_mode']=='manual'
    assert settings['resolved_scope']==['as-map-9','surface']
    assert settings['world_map']['scope']==['as-map-7','surface']
    write_json(path,{'categories':[]})
    assert read_settings(path)['tracking_mode']=='auto'


def test_map_change_rejects_old_epoch_and_resets_collection_context(tmp_path,monkeypatch):
    from src.live import desktop
    calls=[]
    monkeypatch.setattr(desktop,'installed_scopes',lambda root:[('as-map-7','surface')])
    session=Session([],ProgressManager(str(tmp_path/'progress.json')))
    session.map_id='as-map-2';session.layer_id='surface';session.pending_ids={'old'}
    app=SimpleNamespace(selection_epoch=3,settings={'tracking_mode':'auto'},reference_root=tmp_path,
        session=session,close_marker_menu=lambda **kw:calls.append('close'),
        automark_snapshot=object(),resync_automark=lambda:calls.append('resync'),
        territory_path=SimpleNamespace(set=lambda text:calls.append('caption')),
        reload_reference=lambda:calls.append('reload'),persist_settings=lambda:calls.append('save'))
    assert not desktop.DesktopApp.accept_discovered_map(app,2,('as-map-7','surface'))
    assert not calls and session.pending_ids=={'old'}
    assert desktop.DesktopApp.accept_discovered_map(app,3,('as-map-7','surface'))
    assert (session.map_id,session.layer_id)==('as-map-7','surface')
    assert not session.pending_ids and app.automark_snapshot is None
    assert calls==['close','resync','caption','reload','save']
    assert not desktop.DesktopApp.accept_discovered_map(app,3,('as-map-7','surface'))
    app.settings['tracking_mode']='manual'
    assert not desktop.DesktopApp.accept_discovered_map(app,3,('as-map-9','surface'))


def test_floor_overlay_uses_its_own_world_bounds_and_releases_cache(tmp_path,monkeypatch):
    from PIL import Image
    from src.live import world_tiles
    directory=tmp_path/'userData/references/appsample/as-map-7/floor'
    directory.mkdir(parents=True)
    Image.new('RGBA',(64,64),(255,0,0,255)).save(directory/'overlay.png')
    monkeypatch.setattr(world_tiles,'install_dir',lambda:tmp_path)
    tiles=WorldTiles(tmp_path/'empty')
    tiles.meta.update(map_id='as-map-7',layer='floor',overlay={'bounds':{}})
    tiles.bounds=(0,0,256,256)
    try:
        image=tiles.load((14,0,0,64))
        assert image.getpixel((32,32))==(255,0,0)
        assert tiles.overlay is not None
    finally:tiles.close()
    assert tiles.overlay is None and not tiles.cache


def test_many_floors_do_not_multiply_routing_descriptor_budget(tmp_path):
    import hashlib
    from collections import Counter
    from src.live.automatic_maps import MapRouter
    scopes=[]
    for n in range(8):
        scope=('as-map-7',f'floor-{n}');scopes.append(scope)
        directory=tmp_path/scope[0]/scope[1];directory.mkdir(parents=True)
        path=directory/'routing.npz'
        np.savez_compressed(path,descriptors=np.random.default_rng(n).random((300,128)).astype(np.float32))
        (directory/'manifest.json').write_text(json.dumps({'routing':{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}))
    router=MapRouter(scopes,tmp_path)
    assert Counter(s[0] for s in router.owners)['as-map-7']<=1200


def test_atlas_browsing_is_independent_and_releases_previous_map(tmp_path):
    code=f'''
import gc;gc.disable()
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scripts.preview_lunar import PreviewApp
from src.live import world_map
from src.live.catalog import Item
from src.live.session import Session
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager
import numpy as np,time
closed=[]
class Tiles:
 def __init__(self,**kw):
  self.scope=(kw['map_id'],kw['layer']);self.bounds=(-100,-100,100,100)
  self.pool=ThreadPoolExecutor(max_workers=1);self.levels=[];self.pending={{}}
 def get(self,key):return None
 def poll(self):return False
 def close(self):closed.append(self.scope);self.pool.shutdown(wait=True,cancel_futures=True)
world_map.WorldTiles=Tiles
world_map.installed_scopes=lambda:[('as-map-2','surface'),('as-map-7','surface')]
world_map.place_dialog=lambda window,parent,size:window.withdraw()
app=PreviewApp();app.persist_settings=lambda:None
app.settings['world_map']={{'scope':['as-map-7','surface']}}
app.session=Session([Item('a','A','common-chest',0,0,map_id='as-map-2'),Item('b','B','common-chest',0,0,map_id='as-map-7')],ProgressManager({str(tmp_path/'progress.json')!r}))
app.session.map_id='as-map-2';app.session.layer_id='surface'
view=world_map.WorldMap(app);view.window.withdraw()
assert view.scope==('as-map-7','surface')
view.select_scope(('as-map-2','surface'))
assert closed==[('as-map-7','surface')]
view.select_scope(('as-map-7','surface'))
assert app.session.map_id=='as-map-2'
app.session.observation=Observation('map',time.monotonic(),np.eye(2,3),.9,.1,map_id='as-map-2',layer_id='surface')
view.current_area()
assert view.scope==('as-map-2','surface') and app.session.map_id=='as-map-2'
view.select_scope(('as-map-7','surface'))
app.session.observation=Observation('hidden',time.monotonic())
app.last_recognized_scope=('as-map-2','surface')
view.current_area()
assert view.scope==('as-map-2','surface') and app.session.map_id=='as-map-2'
view.close();assert closed[-1]==('as-map-2','surface')
app.compact.stop();app.root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                   text=True,capture_output=True,check=True,timeout=25)


def test_router_ranks_all_seven_maps_without_false_ambiguity():
    import cv2
    from src.live.automatic_maps import MapRouter
    from src.live.map_registry import installed_scopes
    from src.live.reference_store import read_spec

    root = Path('userData/references/appsample').resolve()
    scopes = installed_scopes(root)
    active = read_spec(root / 'as-map-2/surface', 'appsample', 'as-map-2', 'surface', 'appsample-webmercator-z14', 0)
    router = MapRouter(scopes, root)

    all_maps = [
        ('as-map-2', 1800, 2200),
        ('as-map-7', None, None),
        ('as-map-9', None, None),
        ('as-map-34', None, None),
        ('as-map-36', None, None),
        ('as-map-37', None, None),
        ('as-map-40', None, None),
    ]
    for target, fixed_y, fixed_x in all_maps:
        p = root / target / 'surface/manifest.json'
        m = json.loads(p.read_text(encoding='utf-8'))
        terrain = cv2.imread(str(p.parent / m['terrain']['file']))
        if fixed_y is not None:
            cy, cx = fixed_y, fixed_x
        else:
            gray = cv2.cvtColor(terrain, cv2.COLOR_BGR2GRAY)
            nz = np.where(gray > 8)
            cy, cx = int(np.median(nz[0])), int(np.median(nz[1]))
        x = max(0, min(terrain.shape[1] - 768, cx - 384))
        y = max(0, min(terrain.shape[0] - 512, cy - 256))
        scene = np.zeros((1080, 1920, 3), np.uint8)
        scene[250:762, 576:1344] = terrain[y:y+512, x:x+768]
        hud = active.map_ui
        scene[10:10+hud.shape[0], 1650:1650+hud.shape[1]] = hud

        ranked, ambiguous = router.rank(scene, active)
        assert ranked, f"No scopes ranked for {target}"
        assert not ambiguous, f"False ambiguity detected for {target}"
        assert ranked[0][0] == target, f"Expected top rank {target}, got {ranked[0][0]}"


def test_teyvat_underground_layers_explicitly_classified_reference_missing():
    from src.live.tracking_diagnostics import classify_scope_support, REFERENCE_MISSING
    supported, code, reason = classify_scope_support('as-map-2', 'as-layer-101-200')
    assert not supported
    assert code == REFERENCE_MISSING
    assert 'não possuem pacotes de referência' in reason

    supported_surf, code_surf, _ = classify_scope_support('as-map-2', 'surface')
    assert supported_surf and code_surf is None


def test_underground_layer_detected_over_dimmed_surface_and_strictly_single_layer(tmp_path):
    import cv2
    from src.live.reference_store import read_spec
    from src.live.budget_vision import BudgetRecognizer

    root = Path('userData/references/appsample').resolve()
    surf_spec = read_spec(root / 'as-map-34/surface', 'appsample', 'as-map-34', 'surface', 'appsample-webmercator-z14', 0)
    layer_spec = read_spec(root / 'as-map-34/as-layer-125-157', 'appsample', 'as-map-34', 'as-layer-125-157', 'appsample-webmercator-z14', 1)

    H, W = 1080, 1920
    surf_img = cv2.imread(str(surf_spec.rasters[0].path))
    layer_img = cv2.imread(str(layer_spec.rasters[0].path))

    M_world_to_screen = np.array([[0.25, 0.0, W/2 - 0.25 * (-2069.306)],
                                  [0.0, 0.25, H/2 - 0.25 * (-709.129)]], dtype=np.float32)

    M_surf_to_screen = M_world_to_screen @ np.vstack([cv2.invertAffineTransform(surf_spec.rasters[0].matrix), [0, 0, 1]])
    dimmed_surf = cv2.warpAffine(surf_img, M_surf_to_screen, (W, H)) // 2

    M_layer_to_screen = M_world_to_screen @ np.vstack([cv2.invertAffineTransform(layer_spec.rasters[0].matrix), [0, 0, 1]])
    cave_overlay = cv2.warpAffine(layer_img, M_layer_to_screen, (W, H))

    mask = (cave_overlay > 10).any(axis=2, keepdims=True)
    composed = np.where(mask, cave_overlay, dimmed_surf)

    ui = surf_spec.map_ui
    uh, uw = ui.shape[:2]
    composed[round(0.02*H):round(0.02*H)+uh, round(0.88*W):round(0.88*W)+uw] = ui

    recognizer = BudgetRecognizer([surf_spec, layer_spec], tmp_path / 'cache')
    obs = recognizer.observe(composed, 10.0)
    if obs.layer_id != 'as-layer-125-157':
        obs = recognizer.observe(composed, 10.1)

    assert obs.surface == 'map'
    assert obs.map_id == 'as-map-34'
    assert obs.layer_id == 'as-layer-125-157'
    assert obs.confidence >= 0.80
    assert obs.layer_id is not None
    assert obs.layer_id != 'surface'


def test_multimap_consecutive_transitions_invalidation():
    import cv2, time
    from src.live.map_registry import installed_scopes
    from src.live.reference_store import read_spec
    from src.live.automatic_maps import AutomaticMapSearch
    from src.live.vision import Observation

    root = Path('userData/references/appsample').resolve()
    scopes = installed_scopes(root)
    active = read_spec(root / 'as-map-2/surface', 'appsample', 'as-map-2', 'surface', 'appsample-webmercator-z14', 0)

    def make_scene(target, cy_cx=None):
        p = root / target / 'surface/manifest.json'
        m = json.loads(p.read_text(encoding='utf-8'))
        terrain = cv2.imread(str(p.parent / m['terrain']['file']))
        if cy_cx is not None:
            cy, cx = cy_cx
        else:
            gray = cv2.cvtColor(terrain, cv2.COLOR_BGR2GRAY)
            nz = np.where(gray > 8)
            cy, cx = int(np.median(nz[0])), int(np.median(nz[1]))
        x = max(0, min(terrain.shape[1] - 768, cx - 384))
        y = max(0, min(terrain.shape[0] - 512, cy - 256))
        scene = np.zeros((1080, 1920, 3), np.uint8)
        scene[250:762, 576:1344] = terrain[y:y+512, x:x+768]
        hud = active.map_ui
        scene[10:10+hud.shape[0], 1650:1650+hud.shape[1]] = hud
        return scene

    current_scope = ('as-map-2', 'surface')
    chain = [('as-map-7', None), ('as-map-34', None), ('as-map-2', (1800, 2200))]

    for target_map, coords in chain:
        expected = (target_map, 'surface')
        scene = make_scene(target_map, coords)
        search = AutomaticMapSearch(scopes, current_scope, root, Path('userData/cache/references'), active)
        search.loss_grace = 0.5
        found = None
        for _ in range(40):
            now = time.monotonic()
            found = search.tick(scene, now, Observation('hidden', now), surface='map')
            if found:
                break
            time.sleep(0.2)
        search.close()
        assert found == expected, f"Failed transition from {current_scope} to {expected}, got {found}"
        current_scope = found


def test_same_map_underground_layer_monitoring_tick():
    import cv2, time
    from src.live.map_registry import installed_scopes
    from src.live.reference_store import read_spec
    from src.live.automatic_maps import AutomaticMapSearch
    from src.live.vision import Observation

    root = Path('userData/references/appsample').resolve()
    scopes = installed_scopes(root)
    active = read_spec(root / 'as-map-34/surface', 'appsample', 'as-map-34', 'surface', 'appsample-webmercator-z14', 0)
    layer_spec = read_spec(root / 'as-map-34/as-layer-125-157', 'appsample', 'as-map-34', 'as-layer-125-157', 'appsample-webmercator-z14', 1)

    H, W = 1080, 1920
    surf_img = cv2.imread(str(active.rasters[0].path))
    layer_img = cv2.imread(str(layer_spec.rasters[0].path))

    M_world_to_screen = np.array([[0.25, 0.0, W/2 - 0.25 * (-2069.306)],
                                  [0.0, 0.25, H/2 - 0.25 * (-709.129)]], dtype=np.float32)

    M_surf_to_screen = M_world_to_screen @ np.vstack([cv2.invertAffineTransform(active.rasters[0].matrix), [0, 0, 1]])
    dimmed_surf = cv2.warpAffine(surf_img, M_surf_to_screen, (W, H)) // 2

    M_layer_to_screen = M_world_to_screen @ np.vstack([cv2.invertAffineTransform(layer_spec.rasters[0].matrix), [0, 0, 1]])
    cave_overlay = cv2.warpAffine(layer_img, M_layer_to_screen, (W, H))

    mask = (cave_overlay > 10).any(axis=2, keepdims=True)
    composed = np.where(mask, cave_overlay, dimmed_surf)

    ui = active.map_ui
    uh, uw = ui.shape[:2]
    composed[round(0.02*H):round(0.02*H)+uh, round(0.88*W):round(0.88*W)+uw] = ui

    search = AutomaticMapSearch(scopes, ('as-map-34', 'surface'), root, Path('userData/cache/references'), active)
    try:
        new_layer = None
        for step in range(30):
            now = time.monotonic()
            fresh_obs = Observation('map', now, M_world_to_screen, 0.99, 0.5, None, (-2069.3, -709.1),
                                    'Explorando', 'as-map-34', 'surface')
            res = search.tick(composed, now, fresh_obs, surface='map')
            if res:
                new_layer = res
                break
            time.sleep(0.15)
        assert new_layer == ('as-map-34', 'as-layer-125-157')
    finally:
        search.close()


