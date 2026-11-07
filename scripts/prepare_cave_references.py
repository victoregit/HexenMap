"""Prepare personal cave candidates from explicit source chunks and bounds.

No name-distance assignment or artwork redistribution. Missing/ambiguous source
metadata is recorded as a failure, never replaced with fabricated terrain.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import threading
import time
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.storage import write_json


def chunk_transform(bounds,width,height):
    (x0,y0),(x1,y1)=bounds
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1<=x0 or y1<=y0:
        raise ValueError('Invalid explicit chunk bounds')
    if abs(math.log((width/height)/((x1-x0)/(y1-y0))))>.12:
        raise ValueError('Chunk dimensions disagree with the source coordinate axes')
    sx,sy=width/(x1-x0),height/(y1-y0)
    return [[sx,0,-sx*x0],[0,sy,-sy*y0]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--retry-failed',action='store_true')
    args=parser.parse_args()
    base=ROOT/'data/community/kongying'
    inventory=json.loads((base/'inventory.json').read_text(encoding='utf-8'))
    source=json.loads((base/'source-map-config.json').read_text(encoding='utf-8'))
    known={node['id']:node for node in inventory['territories'] if node['kind']=='locality'}
    needed=set()
    for region in inventory['regions']:
        if args.region and args.region!=region['id']: continue
        items=json.loads((base/region['id']/'markers.json').read_text(encoding='utf-8'))['items']
        needed.update(layer for item in items for layer in item.get('layer_ids',[]))
    jobs={}
    for mapmeta in inventory['maps']:
        region,mapid=mapmeta['region_id'],mapmeta['id']
        if args.region and args.region!=region: continue
        for code in mapmeta['source_area_codes']:
            overlay=source['plugins'].get(code,{}).get('overlayConfig',{})
            template=overlay.get('urlTemplate','')
            if not template.startswith('https://tiles.yuanshen.site/d/underground/'): continue
            def walk(nodes):
                for node in nodes:
                    identifier=f"ky-level-{region}-{node['value'].lower().replace('@','at-')}"
                    chunks=node.get('chunks') or ([{'url':node['url'],'bounds':node['bounds']}]
                            if node.get('url') and node.get('bounds') else [])
                    if identifier in needed and identifier in known and chunks:
                        jobs.setdefault((region,mapid,identifier),(template,chunks))
                    walk(node.get('children',[]))
            walk(overlay.get('overlays',[]))
    if args.limit: jobs=dict(list(sorted(jobs.items()))[:args.limit])
    missing=sorted(needed-{key[2] for key in jobs})
    previous=[]
    if args.retry_failed:
        previous=json.loads((ROOT/'build/regional-audit/cave-preparation.json').read_text(encoding='utf-8'))['results']
        failed={(r['region'],r['map'],r['layer']) for r in previous if not r['prepared']}
        failed.update(key for key in jobs if key[2] in json.loads((ROOT/'build/regional-audit/cave-preparation.json').read_text(encoding='utf-8'))['without_explicit_chunks'])
        jobs={key:value for key,value in jobs.items() if key in failed}
        previous=[r for r in previous if r['prepared']]
    ui_dir=ROOT/'userData/references/mondstadt'
    ui=json.loads((ui_dir/'manifest.json').read_text(encoding='utf-8'))
    cache=ROOT/'userData/reference-cave-cache';cache.mkdir(parents=True,exist_ok=True)
    locks={};lock=threading.Lock()
    def prepare(job):
        (region,mapid,layer),(template,chunks)=job
        output=ROOT/'userData/references/kongying'/region/mapid/layer
        output.mkdir(parents=True,exist_ok=True)
        entries=[]
        for chunk in chunks:
            url=chunk.get('url') or template.replace('{{chunkValue}}',chunk['value'])
            if not url.startswith('https://tiles.yuanshen.site/d/underground/'):
                raise ValueError('Chunk URL outside the verified source')
            if '{{' in url: raise ValueError('Unresolved source template')
            name=hashlib.sha256(url.encode()).hexdigest()+'.png'
            with lock: filelock=locks.setdefault(name,threading.Lock())
            with filelock:
                path=cache/name
                if not path.exists():
                    for attempt in range(3):
                        try:
                            with urllib.request.urlopen(url,timeout=25) as response: raw=response.read()
                            with Image.open(io.BytesIO(raw)) as image: image.verify()
                            path.write_bytes(raw);break
                        except OSError:
                            if attempt==2: raise
                            time.sleep(attempt+1)
                raw=path.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                matrix=chunk_transform(chunk['bounds'],*image.size)
            shutil.copy2(path,output/name)
            entries.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),world_to_image=matrix,
                                source_url=url,source_bounds=chunk['bounds']))
        for key in ['map_ui','gameplay_ui']: shutil.copy2(ui_dir/ui[key]['file'],output/ui[key]['file'])
        primary=entries[0]
        manifest=dict(region=region,map_id=mapid,layer=layer,coordinate_system='kongying-world',
                      world_to_image=primary['world_to_image'],terrain=primary,extra_terrain=entries[1:],
                      map_ui=ui['map_ui'],gameplay_ui=ui['gameplay_ui'],
                      source=f"https://assets.yuanshen.site/webapp.json snapshot {inventory['snapshot']}; explicit underground chunks",
                      permission={'usage':'Personal local validation only; do not redistribute original game artwork',
                                  'evidence':'https://yuanshen.site/docs/en/disclaimer; HoYoverse original artwork; user-owned local UI captures'},
                      validation='source_geometry_candidate_not_live_validated')
        write_json(output/'manifest.json',manifest)
        return dict(region=region,map=mapid,layer=layer,chunks=len(entries),prepared=True)
    results=list(previous)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(prepare,job):job[0] for job in jobs.items()}
        for future in as_completed(futures):
            try: result=future.result()
            except Exception as exc:
                region,mapid,layer=futures[future]
                result=dict(region=region,map=mapid,layer=layer,prepared=False,error=str(exc))
            results.append(result)
            print(result['layer'], 'OK' if result['prepared'] else result['error'],flush=True)
    write_json(ROOT/'build/regional-audit/cave-preparation.json',dict(results=results,without_explicit_chunks=missing))
    print(f"Prepared {sum(r['prepared'] for r in results)}/{len(results)}; without explicit chunks: {len(missing)}")


if __name__=='__main__': main()
