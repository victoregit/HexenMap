"""Install only the published floors of the permanent separate maps."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.appsample_catalog import project
from src.live.map_registry import maps
from src.live.storage import write_json


def fetch(pair):
    row,layer=pair
    directory=ROOT/'userData/reference-cave-cache/appsample'/row['map_id']
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(layer['layer_id']+'.png')
    if not path.exists():
        if not layer['source'].startswith('https://game-cdn.appsample.com/gim/overlays/'):
            raise ValueError('Invalid floor source')
        for attempt in range(3):
            try:
                request=urllib.request.Request(layer['source'],headers={'User-Agent':'HexenMap offline map preparation'})
                with urllib.request.urlopen(request,timeout=25) as response:raw=response.read(50*1024*1024)
                with Image.open(io.BytesIO(raw)) as image:
                    if min(image.size)<12 or image.width*image.height>64*1024**2:raise ValueError('Invalid floor dimensions')
                    image.verify()
                path.with_suffix('.download').write_bytes(raw)
                path.with_suffix('.download').replace(path)
                break
            except Exception:
                if attempt==2:raise
                time.sleep(1)
    return row,layer,path


def prepare(row,layer,path):
    output=ROOT/'userData/references/appsample'/row['map_id']/layer['layer_id']
    output.mkdir(parents=True,exist_ok=True)
    original=ROOT/'userData/references/appsample/as-map-2/surface'
    template=json.loads((original/'manifest.json').read_text(encoding='utf-8'))
    b=layer['bounds'];left,top=project(b['west'],b['north']);right,bottom=project(b['east'],b['south'])
    with Image.open(path) as source:image=source.convert('RGBA')
    sx,sy=image.width/(right-left),image.height/(bottom-top)
    atlas=image.copy();atlas.thumbnail((2048,2048),Image.Resampling.LANCZOS);atlas.save(output/'overlay.png')
    def entry(img,name):
        img.save(output/name)
        return {'file':name,'sha256':hashlib.sha256((output/name).read_bytes()).hexdigest()}
    rgb=Image.new('RGB',atlas.size);rgb.paste(atlas,mask=atlas.getchannel('A'))
    primary=entry(rgb,'terrain.png')
    matrix=[[rgb.width/(right-left),0,-left*rgb.width/(right-left)],
            [0,rgb.height/(bottom-top),-top*rgb.height/(bottom-top)]]
    _,desc=cv2.SIFT_create(nfeatures=300,contrastThreshold=.025).detectAndCompute(np.asarray(rgb.convert('L')),None)
    if desc is None:raise ValueError('Floor reference has insufficient visual detail')
    np.savez_compressed(output/'routing.npz',descriptors=desc[:300])
    extras=[]
    for x in range(0,image.width,896):
        for y in range(0,image.height,896):
            crop=image.crop((x,y,min(x+1024,image.width),min(y+1024,image.height)))
            if min(crop.size)<12:continue
            part=Image.new('RGB',crop.size);part.paste(crop,mask=crop.getchannel('A'))
            part=part.resize((round(part.width*1.25),round(part.height*1.25)),Image.Resampling.BICUBIC)
            e=entry(part,f'detail-{x}-{y}.png')
            e.update(world_to_image=[[sx*1.25,0,(-left*sx-x)*1.25],[0,sy*1.25,(-top*sy-y)*1.25]],surface='minimap',map_compatible=True)
            extras.append(e);part.close();crop.close()
    manifest=dict(region='appsample',map_id=row['map_id'],layer=layer['layer_id'],
                  coordinate_system=row['coordinate_system'],source=layer['source'],
                  permission=copy.deepcopy(template['permission']),validation='image_candidate_not_live_validated',
                  world_to_image=matrix,terrain=primary,extra_terrain=extras,
                  routing={'file':'routing.npz','sha256':hashlib.sha256((output/'routing.npz').read_bytes()).hexdigest()},
                  atlas={'file':'overlay.png','sha256':hashlib.sha256((output/'overlay.png').read_bytes()).hexdigest()})
    for key in ('map_ui','gameplay_ui'):
        manifest[key]=copy.deepcopy(template[key]);shutil.copy2(original/template[key]['file'],output/template[key]['file'])
    write_json(output/'manifest.json',manifest)
    image.close();atlas.close();rgb.close()
    print(row['map_id'],layer['layer_id'],'ready for in-game validation',flush=True)


def main():
    pairs=[(r,l) for r in maps().values() for l in r.get('layers',[])]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row,layer,path in pool.map(fetch,pairs):prepare(row,layer,path)


if __name__=='__main__':main()
