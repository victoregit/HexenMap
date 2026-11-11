"""Prepare offline maps from pinned public tile definitions, without touching saves.

Published extents include empty terrain. Missing tiles are errors, never silently
converted into evidence that a map is supported. Existing Teyvat tracking stays intact.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time
import urllib.request

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.live.map_registry import maps
from src.live.storage import write_json


def cells(row, zoom):
    b = row['tile_bounds'][str(zoom)]
    return [(x, y) for x in range(b['minX'], b['maxX']+1)
            for y in range(-b['maxY']-1, -b['minY'])]


def download(row, zoom, workers=4):
    cache = ROOT / 'userData/reference-tile-cache' / row['dataset'] / str(zoom)
    cache.mkdir(parents=True, exist_ok=True)
    def fetch(pair):
        x, y = pair
        path = cache / f'{x}_{y}.jpg'
        if path.exists():
            with Image.open(path) as image:
                if image.size == (256, 256):
                    return
        url = f"{row['source']}/{zoom}/tile-{x}_{-y-1}.jpg"
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'HexenMap offline map preparation'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    raw = response.read(2*1024*1024)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.size != (256, 256):
                        raise ValueError(f'Invalid tile size: {url}')
                temporary = path.with_suffix('.download')
                temporary.write_bytes(raw)
                temporary.replace(path)
                return
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(.5 * (attempt+1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch, cells(row, zoom)))
    return cache


def compose(cache, box):
    a, b, c, d = box
    image = Image.new('RGB', ((c-a)*256, (d-b)*256))
    for x in range(a, c):
        for y in range(b, d):
            with Image.open(cache / f'{x}_{y}.jpg') as part:
                image.paste(part.convert('RGB'), ((x-a)*256, (y-b)*256))
    return image


def prepare(row, workers=4):
    base = download(row, 12, workers)
    if row['map_id'] == 'as-map-2':
        output = ROOT / 'userData/references/appsample/as-map-2/surface'
        manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
        descriptors = []
        for e in [manifest['terrain'], *[e for e in manifest.get('extra_terrain',[]) if e.get('surface')=='minimap'][:4]]:
            image = cv2.imread(str(output / e['file']), cv2.IMREAD_GRAYSCALE)
            _, desc = cv2.SIFT_create(nfeatures=240,contrastThreshold=.025).detectAndCompute(image,None)
            if desc is not None:descriptors.append(desc)
        route = output / 'routing.npz'
        np.savez_compressed(route,descriptors=np.concatenate(descriptors)[:1200])
        manifest['routing'] = {'file':route.name,'sha256':hashlib.sha256(route.read_bytes()).hexdigest()}
        write_json(output / 'manifest.json',manifest)
        print('Teyvat: complete atlas tiles prepared; existing tracking preserved', flush=True)
        return
    detail_zoom = min(14, row['max_zoom'])
    detailed = download(row, detail_zoom, workers)
    output = ROOT / 'userData/references/appsample' / row['map_id'] / 'surface'
    output.mkdir(parents=True, exist_ok=True)
    original = ROOT / 'userData/references/appsample/as-map-2/surface'
    template = json.loads((original / 'manifest.json').read_text(encoding='utf-8'))
    b = row['tile_bounds']['12']
    x0, y0, x1, y1 = b['minX'], -b['maxY']-1, b['maxX']+1, -b['minY']
    terrain = compose(base, (x0, y0, x1, y1))
    def entry(image, name):
        path = output / name
        image.save(path)
        return {'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    primary = entry(terrain, 'terrain-z12.png')
    sift = cv2.SIFT_create(nfeatures=600, contrastThreshold=.025)
    _, descriptors = sift.detectAndCompute(cv2.cvtColor(np.asarray(terrain), cv2.COLOR_RGB2GRAY), None)
    routing = [descriptors] if descriptors is not None else []
    terrain.close()
    extras = []
    b = row['tile_bounds'][str(detail_zoom)]
    a, c, top, bottom = b['minX'], b['maxX']+1, -b['maxY']-1, -b['minY']
    for x in range(a, c, 3):
        for y in range(top, bottom, 3):
            crop = compose(detailed, (x, y, min(x+4,c), min(y+4,bottom)))
            # Match native minimap detail without allocating a whole zoom-13 raster.
            crop = crop.resize((round(crop.width*1.25), round(crop.height*1.25)), Image.Resampling.BICUBIC)
            e = entry(crop, f'minimap-{detail_zoom}-{x}-{y}.png')
            factor = 2**(detail_zoom-14)*1.25
            e.update(world_to_image=[[factor,0,-x*256*1.25],[0,factor,-y*256*1.25]], surface='minimap')
            extras.append(e)
            # A bounded sample of native-resolution terrain supplements the overview.
            if len(routing) < 13:
                _, desc = cv2.SIFT_create(nfeatures=50, contrastThreshold=.025).detectAndCompute(
                    cv2.cvtColor(np.asarray(crop), cv2.COLOR_RGB2GRAY), None)
                if desc is not None:
                    routing.append(desc)
            crop.close()
    manifest = dict(region='appsample', map_id=row['map_id'], layer='surface',
                    coordinate_system=row['coordinate_system'], source=row['source'],
                    world_to_image=[[.25,0,-x0*256],[0,.25,-y0*256]], terrain=primary,
                    extra_terrain=extras, permission=copy.deepcopy(template['permission']),
                    validation='image_candidate_not_live_validated')
    for key in ('map_ui', 'gameplay_ui'):
        manifest[key] = copy.deepcopy(template[key])
        shutil.copy2(original / template[key]['file'], output / template[key]['file'])
    # Written last: interrupted preparation cannot advertise a partial reference.
    np.savez_compressed(output / 'routing.npz', descriptors=np.concatenate(routing)[:1200])
    manifest['routing'] = {'file':'routing.npz','sha256':hashlib.sha256((output / 'routing.npz').read_bytes()).hexdigest()}
    write_json(output / 'manifest.json', manifest)
    print(row['map_id'], 'references ready for in-game validation', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maps', nargs='+', default=list(maps()))
    parser.add_argument('--workers', type=int, default=4, choices=range(1,9))
    args = parser.parse_args()
    for map_id in args.maps:
        prepare(maps()[map_id], args.workers)


if __name__ == '__main__':
    main()
