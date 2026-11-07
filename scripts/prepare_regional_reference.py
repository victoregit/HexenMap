"""Prepare a personal-use Kongying tile reference; artwork never enters the bundle.

The exact source CRS and tile formula are pinned in docs/REGIONAL_COVERAGE.md.
This produces an image-test candidate, not proof of live game validation.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import io
import http.client
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def partition_bounds(bounds, side=16, overlap=1):
    """Bound raster memory while retaining common terrain at chunk seams."""
    if side <= overlap or overlap < 0:
        raise ValueError('Invalid tile partition size')
    x0,y0,x1,y1=bounds
    if x1<x0 or y1<y0:
        raise ValueError('Empty tile rectangle')
    result=[]
    x=x0
    while x<=x1:
        right=min(x+side-1,x1);y=y0
        while y<=y1:
            bottom=min(y+side-1,y1)
            result.append((x,y,right,bottom))
            if bottom==y1: break
            y=bottom-overlap+1
        if right==x1: break
        x=right-overlap+1
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region',required=True)
    parser.add_argument('--map',default='teyvat')
    parser.add_argument('--zoom',type=int,choices=[-3,-2,-1,0],default=-1)
    parser.add_argument('--bounds',type=int,nargs=4,metavar=('X0','Y0','X1','Y1'),help='Tile rectangle, inclusive')
    parser.add_argument('--append',action='store_true',help='Add terrain at another scale without replacing the primary reference')
    parser.add_argument('--partition',action='store_true',help='Prepare large maps as overlapping bounded rasters')
    args=parser.parse_args()
    catalog=ROOT/'data/community/kongying'
    inventory=json.loads((catalog/'inventory.json').read_text(encoding='utf-8'))
    meta=next(m for m in inventory['maps'] if m['region_id']==args.region and m['id']==args.map)
    config_url='https://assets.yuanshen.site/webapp.json'
    config=json.loads((catalog/'source-map-config.json').read_text(encoding='utf-8'))['tiles']
    area=config[meta['source_area_codes'][0]]
    options={'center':[3568,6286],'size':[12288,15360],'tilesOffset':[0,0],
             'extension':'png',**config.get(area.get('extend'),{}),**area}
    center=options['center'];code=options['code'];scale=2**args.zoom
    points=json.loads((catalog/args.region/'markers.json').read_text(encoding='utf-8'))['items']
    points=[p for p in points if p['map_id']==args.map and p['layer_id']=='surface']
    if not points: raise ValueError('No classified surface points')
    if args.bounds:
        x0,y0,x1,y1=args.bounds
    else:
        xs=[scale*(p['x']+center[0])/256 for p in points]
        ys=[scale*(p['y']+center[1])/256 for p in points]
        margin=1 if args.map=='teyvat' else 0
        x0,y0,x1,y1=math.floor(min(xs))-margin,math.floor(min(ys))-margin,math.floor(max(xs))+margin,math.floor(max(ys))+margin
        offset=options['tilesOffset'];size=options['size']
        x0=max(x0,math.floor(offset[0]*scale/256));y0=max(y0,math.floor(offset[1]*scale/256))
        x1=min(x1,math.ceil((offset[0]+size[0])*scale/256)-1)
        y1=min(y1,math.ceil((offset[1]+size[1])*scale/256)-1)
    if x1<x0 or y1<y0: raise ValueError('No points within the published map bounds')
    if args.partition:
        # Keep the proven coarse reference and add detailed chunks. Never create
        # one enormous raster or silently omit a failed download.
        for bounds in partition_bounds((x0,y0,x1,y1)):
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--region',args.region,
                            '--map',args.map,'--zoom',str(args.zoom),'--append',
                            '--bounds',*(str(v) for v in bounds)],check=True)
        return
    if (x1-x0+1)*(y1-y0+1)>600: raise ValueError('Reference too large; use lower zoom or an explicit tile rectangle')
    cache=ROOT/'userData/reference-tile-cache'/code/str(args.zoom+13)
    cache.mkdir(parents=True,exist_ok=True)
    def tile(pair):
        x,y=pair;path=cache/f'{x}_{y}.{options["extension"]}'
        url=f'https://assets.yuanshen.site/tiles_{code}/{args.zoom+13}/{path.name}'
        if not path.exists():
            for attempt in range(3):
                try:
                    request=urllib.request.Request(url if attempt==0 else f'{url}?retry={attempt}',
                                                   headers={'Cache-Control':'no-cache'} if attempt else {})
                    with urllib.request.urlopen(request,timeout=25) as response: raw=response.read()
                    break
                except (OSError,http.client.HTTPException) as exc:
                    if attempt==2: raise RuntimeError(f'Could not read source tile {url}: {exc}') from exc
                    time.sleep(1+attempt)
            with Image.open(io.BytesIO(raw)) as test:
                if test.size!=(256,256): raise ValueError(f'Unexpected tile size: {url}')
            path.write_bytes(raw)
        with Image.open(path) as image: return x,y,image.convert('RGB')
    image=Image.new('RGB',((x1-x0+1)*256,(y1-y0+1)*256))
    with ThreadPoolExecutor(max_workers=4) as pool:
        # Any missing tile aborts; no synthetic terrain substitutes for missing data.
        for x,y,part in pool.map(tile,[(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]):
            image.paste(part,((x-x0)*256,(y-y0)*256))
    output=ROOT/'userData/references/kongying'/args.region/args.map/'surface'
    output.mkdir(parents=True,exist_ok=True)
    terrain_name=f'terrain-z{args.zoom}-{x0}-{y0}-{x1}-{y1}.png'
    image.save(output/terrain_name)
    legacy=ROOT/'userData/references/mondstadt'
    ui=json.loads((legacy/'manifest.json').read_text(encoding='utf-8'))
    for key in ['map_ui','gameplay_ui']:
        shutil.copy2(legacy/ui[key]['file'],output/ui[key]['file'])
    manifest=dict(region=args.region,map_id=args.map,layer='surface',coordinate_system='kongying-world',
        world_to_image=[[scale,0,scale*center[0]-x0*256],[0,scale,scale*center[1]-y0*256]],
        source=f'{config_url}; tiles_{code}; zoom {args.zoom+13}; source CRS pinned in REGIONAL_COVERAGE.md',
        permission={'usage':'Personal local validation only; do not redistribute original game artwork',
                    'evidence':'https://yuanshen.site/docs/en/disclaimer; game artwork belongs to HoYoverse; user-owned local UI captures'},
        validation='image_candidate_not_live_validated',coverage={'tile_bounds':[x0,y0,x1,y1],'zoom':args.zoom},
        terrain={'file':terrain_name,'sha256':hashlib.sha256((output/terrain_name).read_bytes()).hexdigest()},
        map_ui=ui['map_ui'],gameplay_ui=ui['gameplay_ui'])
    if args.append and (output/'manifest.json').exists():
        original=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        entry={**manifest['terrain'],'world_to_image':manifest['world_to_image']}
        extras=[e for e in original.get('extra_terrain',[]) if e['file']!=terrain_name]
        original['extra_terrain']=extras+[entry]
        original['coverage_extension']=manifest['coverage']
        manifest=original
    temporary=output/'manifest.json.tmp'
    temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(output/'manifest.json')
    print(f'Prepared {args.region}/{args.map}: {image.size}; live validation still required')


if __name__=='__main__': main()
