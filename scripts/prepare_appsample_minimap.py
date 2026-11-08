"""Personal AppSample surface atlas, spatially partitioned without loading a world image."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.storage import write_json
from src.live.appsample_catalog import SPACE


def atlas_cells(items):
    # Overlapping 4x4-tile rasters. Selection never depends on item filters or type.
    return sorted({(math.floor(float(i['x'])/768)*3,math.floor(float(i['y'])/768)*3)
                   for i in items if i['map_id']=='as-map-2' and i.get('layer_id')=='surface'})


def known_rectangles(a,b,failures):
    remaining={(x,y) for x in range(a,a+4) for y in range(b,b+4) if (x,y) not in failures}
    result=[]
    while remaining:
        choices=[]
        for x,y in remaining:
            for w in range(1,5):
                for h in range(1,5):
                    cells={(xx,yy) for xx in range(x,x+w) for yy in range(y,y+h)}
                    if cells<=remaining:choices.append((w*h,x,y,w,h,cells))
        _,x,y,w,h,cells=max(choices,key=lambda v:v[:5]);result.append((x,y,w,h));remaining-=cells
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(argv)
    directory=ROOT/'userData/references/appsample/as-map-2/surface'
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest['coordinate_system']!=SPACE:raise ValueError('Projeção incompatível')
    base=manifest['source'].split(';')[0].rstrip('/')
    if not base.startswith('https://game-cdn.appsample.com/gim/'):raise ValueError('Origem AppSample não qualificada')
    source=ROOT/'userData/catalogs/appsample'
    metadata=json.loads((source/'SOURCE.json').read_text(encoding='utf-8'))
    items=[]
    for entry in metadata['files']:
        path=(source/entry['file']).resolve()
        if not path.is_relative_to(source.resolve()):raise ValueError('Arquivo fora do catálogo')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Catálogo alterado')
        items.extend(json.loads(raw)['items'])
    cells=atlas_cells(items)
    tiles=sorted({(x,y) for a,b in cells for x in range(a,a+4) for y in range(b,b+4)})
    cache=ROOT/'userData/reference-tile-cache/appsample-teyvat-v72/14'
    missing=[(x,y) for x,y in tiles if not (cache/f'{x}_{y}.jpg').exists()]
    print(json.dumps({'cells':len(cells),'tiles':len(tiles),'missing_tiles':len(missing)}),flush=True)
    if args.dry_run:return
    cache.mkdir(parents=True,exist_ok=True)
    failures={}
    def fetch(pair):
        x,y=pair;path=cache/f'{x}_{y}.jpg';url=f'{base}/14/tile-{x}_{-y-1}.jpg'
        if path.exists():raw=path.read_bytes()
        else:
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=25) as response:raw=response.read()
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code==404:return pair,'404'
                    if attempt==2:raise
                    time.sleep(.5)
                except (OSError,TimeoutError):
                    if attempt==2:raise
                    time.sleep(.5)
            with Image.open(io.BytesIO(raw)) as image:
                if image.size!=(256,256):raise ValueError('Tile incompatível')
            path.write_bytes(raw)
        return pair,None
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch,p):p for p in tiles}
        for n,future in enumerate(as_completed(futures),1):
            try:
                pair,error=future.result()
                if error:failures[pair]=error
            except Exception as exc:failures[futures[future]]=str(exc)
            if n%100==0:print(json.dumps({'downloaded_or_cached':n,'total':len(tiles),'failures':len(failures)}),flush=True)
    entries=[];unavailable=[];partial=[]
    for n,(a,b) in enumerate(cells):
        rects=known_rectangles(a,b,failures)
        if not rects:unavailable.append([a,b]);continue
        if rects!=[(a,b,4,4)]:partial.append([a,b])
        for part,(left,top,width,height) in enumerate(rects):
            image=Image.new('RGB',(width*256,height*256))
            for x in range(left,left+width):
                for y in range(top,top+height):
                    with Image.open(cache/f'{x}_{y}.jpg') as tile:image.paste(tile.convert('RGB'),((x-left)*256,(y-top)*256))
            image=image.resize((width*320,height*320),Image.Resampling.BICUBIC)
            suffix='' if len(rects)==1 and width==height==4 else '-part'+str(part)
            name=f'minimap-atlas-z14-{a}-{b}{suffix}.png';path=directory/name;image.save(path)
            entries.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'world_to_image':[[1.25,0,-left*256*1.25],[0,1.25,-top*256*1.25]],
                            'surface':'minimap','map_compatible':True,'source_url':f'{base}/14',
                            'atlas_cell':[a,b],'validation':'reference_prepared_not_live_validated'})
    uncovered=[i['id'] for i in items if i['map_id']=='as-map-2' and i.get('layer_id')=='surface'
               and (math.floor(float(i['x'])/256),math.floor(float(i['y'])/256)) in failures]
    previous=directory/'manifest.pre-global-minimap.json'
    if not previous.exists():previous.write_bytes((directory/'manifest.json').read_bytes())
    manifest['extra_terrain']=[e for e in manifest.get('extra_terrain',[]) if e.get('surface')!='minimap']+entries
    manifest['minimap_coverage']={'source':'appsample','scope':'all_imported_map2_surface_points','cells':len(cells),
                                  'prepared_rasters':len(entries),'unavailable_cells':unavailable,'partial_cells':partial,'uncovered_marker_ids':uncovered,'not_live_validated':True}
    write_json(directory/'manifest.json',manifest)
    report={'prepared':len(entries),'unavailable':unavailable,'partial_cells':partial,'uncovered_marker_ids':uncovered,'failed_tiles':{f'{a},{b}':v for (a,b),v in failures.items()}}
    write_json(ROOT/'build/appsample-surface-atlas-report.json',report)
    print(json.dumps({'prepared':len(entries),'unavailable':len(unavailable),'partial_cells':len(partial),'uncovered_points':len(uncovered)}),flush=True)


if __name__=='__main__':main()
