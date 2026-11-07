"""Prepare a personal source package and surface references, without changing saves."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.appsample_import import parse_catalog
from src.live.appsample_catalog import normalized_package,project,source_layer,SPACE,MAP_NAMES
from src.live.storage import write_json

TILE_BASE='https://game-cdn.appsample.com/gim/map-teyvat/v72-rc1'


def prepare_reference(points,zoom,detailed=False):
    points=[p for p in points if p.map_id==2 and (p.marker_type=='o833' if detailed else source_layer(p.layer_meta)=='surface')]
    xy=[project(p.x,p.y,zoom) for p in points]
    bounds=[math.floor(min(v[a] for v in xy)/256) for a in (0,1)]+[math.floor(max(v[a] for v in xy)/256) for a in (0,1)]
    x0,y0,x1,y1=bounds
    if (x1-x0+1)*(y1-y0+1)>600:raise ValueError('Referência excede o orçamento; particionar antes de ampliar')
    cache=ROOT/'userData/reference-tile-cache/appsample-teyvat-v72'/str(zoom);cache.mkdir(parents=True,exist_ok=True)
    def tile(pair):
        x,y=pair;path=cache/f'{x}_{y}.jpg'
        if not path.exists():
            # The published centered scheme reverses the tile Y index.
            url=f'{TILE_BASE}/{zoom}/tile-{x}_{-y-1}.jpg'
            with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
            with Image.open(io.BytesIO(raw)) as test:
                if test.size!=(256,256):raise ValueError('Dimensão do tile incompatível')
            path.write_bytes(raw)
        with Image.open(path) as image:return x,y,image.convert('RGB')
    image=Image.new('RGB',((x1-x0+1)*256,(y1-y0+1)*256))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for x,y,part in pool.map(tile,[(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]):
            image.paste(part,((x-x0)*256,(y-y0)*256))
    output=ROOT/'userData/references/appsample/as-map-2/surface';output.mkdir(parents=True,exist_ok=True)
    file=f'terrain-z{zoom}-{x0}-{y0}-{x1}-{y1}.png';image.save(output/file)
    scale=2**(zoom-14);matrix=[[scale,0,-x0*256],[0,scale,-y0*256]]
    entry={'file':file,'sha256':hashlib.sha256((output/file).read_bytes()).hexdigest()}
    if detailed:
        manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        if zoom>=14:
            # Small overlapping rasters retain local SIFT extrema that a global
            # feature budget would discard. Pre-sample once, never while drawing.
            entries=[e for e in manifest.get('extra_terrain',[]) if e.get('surface')!='minimap']
            for left in range(0,image.width,5*256):
                for top in range(0,image.height,5*256):
                    crop=image.crop((left,top,min(image.width,left+7*256),min(image.height,top+7*256)))
                    factor=1.25
                    crop=crop.resize((round(crop.width*factor),round(crop.height*factor)),Image.Resampling.BICUBIC)
                    name=f'minimap-z{zoom}-{x0+left//256}-{y0+top//256}.png';crop.save(output/name)
                    transform=[[scale*factor,0,(-x0*256-left)*factor],[0,scale*factor,(-y0*256-top)*factor]]
                    entries.append({'file':name,'sha256':hashlib.sha256((output/name).read_bytes()).hexdigest(),
                                    'world_to_image':transform,'surface':'minimap'})
            manifest['extra_terrain']=entries
        else:
            manifest['extra_terrain']=[{**entry,'world_to_image':matrix}]
    else:
        ui=ROOT/'userData/references/mondstadt';templates=json.loads((ui/'manifest.json').read_text(encoding='utf-8'))
        for key in ('map_ui','gameplay_ui'):shutil.copy2(ui/templates[key]['file'],output/templates[key]['file'])
        manifest={'region':'appsample','map_id':'as-map-2','layer':'surface','coordinate_system':SPACE,
            'source':TILE_BASE+'; default Leaflet EPSG3857; centered tile scheme from public source',
            'world_to_image':matrix,'terrain':entry,'map_ui':templates['map_ui'],'gameplay_ui':templates['gameplay_ui'],
            'permission':{'usage':'Personal local use only; do not redistribute game artwork',
                          'evidence':'https://genshin-impact-map.appsample.com/help/embed/; original game artwork belongs to HoYoverse; no general redistribution license assumed'},
            'validation':'image_candidate_not_live_validated'}
    write_json(output/'manifest.json',manifest)
    print(f'Reference z{zoom}: {image.size}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--labels',type=Path,required=True)
    parser.add_argument('--references',action='store_true')
    args=parser.parse_args()
    raw=args.catalog.read_bytes();points=parse_catalog(json.loads(raw))
    labels=json.loads(args.labels.read_text(encoding='utf-8'))['labels']
    items,categories=normalized_package(points,labels)
    out=ROOT/'userData/catalogs/appsample';out.mkdir(parents=True,exist_ok=True)
    write_json(out/'markers.json',{'items':items})
    write_json(out/'SOURCE.json',{'project':'AppSample personal catalog','region_id':'appsample','coordinate_system':SPACE,
        'catalog_sha256':hashlib.sha256(raw).hexdigest(),'source':'User-provided public catalog URL, archived in userData/imports/appsample',
        'usage':'Personal local use only; no general redistribution permission established',
        'map_names':MAP_NAMES,'categories':categories,'files':[{'file':'markers.json','format':'normalized-v1',
            'sha256':hashlib.sha256((out/'markers.json').read_bytes()).hexdigest()}]})
    print('Personal catalog:',len(items),'points;',len(categories),'categories',flush=True)
    if args.references:
        prepare_reference(points,12)
        prepare_reference(points,13,True)
        prepare_reference(points,14,True)


if __name__=='__main__':main()
