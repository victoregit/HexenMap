"""Import exact source-type icons into the personal installation, never user saves."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time
import urllib.request
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.storage import write_json

OFFICIAL={'common-chest','exquisite-chest','precious-chest','luxurious-chest','remarkable-chest',
          'anemoculus','geoculus','electroculus','dendroculus','hydroculus','pyroculus','lunoculus','cryoculus'}
BASE='https://game-cdn.appsample.com/gim/markers/'

def verified_image(raw):
    if len(raw)>8*1024*1024:raise ValueError('Icon exceeds size limit')
    with Image.open(io.BytesIO(raw)) as image:
        if image.format not in {'PNG','WEBP','JPEG'} or max(image.size)>4096:raise ValueError('Invalid icon')
        extension={'PNG':'png','WEBP':'webp','JPEG':'jpg'}[image.format]
        if not image.convert('RGBA').getbbox():raise ValueError('Empty icon')
    return extension

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    output=ROOT/'userData/assets/appsample';manifest=output/'SOURCE.json'
    if args.check:
        source=json.loads(manifest.read_text(encoding='utf-8'))
        for entry in source['icons'].values():
            path=(output/entry['file']).resolve()
            if not path.is_relative_to(output.resolve()):raise ValueError('Icon path outside installation')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Icon hash mismatch')
            verified_image(raw)
        print(json.dumps({'verified':len(source['icons']),'unavailable':len(source['unavailable'])}));return
    catalog=json.loads((ROOT/'userData/catalogs/appsample/SOURCE.json').read_text(encoding='utf-8'))
    labels_path=ROOT/'userData/imports/appsample/catalog-9f0c3fe69094909c/labels-pt.json'
    labels=json.loads(labels_path.read_text(encoding='utf-8'))['labels'] if labels_path.exists() else []
    observed={re.search(r'/(o\d+)\.png',r['url']).group(1):r['url'] for r in labels if re.search(r'/(o\d+)\.png',r['url'])}
    output.mkdir(parents=True,exist_ok=True)
    previous=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'icons':{}}
    def prepare(pair):
        category,meta=pair;kind=meta.get('source_type','')
        if not re.fullmatch(r'o\d{1,6}',kind):return category,None,'Unconfirmed source type'
        url=observed.get(kind,BASE+kind+'.png?v=3')
        old=previous['icons'].get(category)
        if old and old.get('source_type')==kind:
            path=(output/old['file']).resolve()
            if path.is_relative_to(output.resolve()) and path.exists():
                raw=path.read_bytes()
                if hashlib.sha256(raw).hexdigest()==old['sha256']:
                    verified_image(raw);return category,old,None
        error='Unavailable'
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=20) as response:raw=response.read(8*1024*1024+1)
                extension=verified_image(raw);file=kind+'.'+extension
                temporary=output/(file+'.tmp');temporary.write_bytes(raw);temporary.replace(output/file)
                return category,{'source_type':kind,'file':file,'url':url,'label':meta.get('name',kind),
                                 'sha256':hashlib.sha256(raw).hexdigest(),'url_observed_in_selector':kind in observed},None
            except Exception as exc:
                error=str(exc)
                if getattr(exc,'code',None) in (403,404):break
                time.sleep(.2*(attempt+1))
        return category,None,error
    pairs=[p for p in catalog['categories'].items() if p[0] not in OFFICIAL]
    icons={};unavailable={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index,(category,entry,error) in enumerate(pool.map(prepare,pairs),1):
            if entry:icons[category]=entry
            else:unavailable[category]={'source_type':catalog['categories'][category].get('source_type'),'reason':error}
            if index%100==0:print(f'{index}/{len(pairs)} checked',flush=True)
    if manifest.exists():
        digest=hashlib.sha256(manifest.read_bytes()).hexdigest()[:20]
        backup=manifest.with_name('SOURCE.'+digest+'.bak.json')
        if not backup.exists():backup.write_bytes(manifest.read_bytes())
    write_json(manifest,{'source':'AppSample public marker images','page':'https://genshin-impact-map.appsample.com/pt/',
        'checked_at':datetime.now(timezone.utc).isoformat(),'catalog_sha256':catalog['catalog_sha256'],
        'usage':'Personal local installation only; redistribution permission not established; original rights remain with their owners',
        'icons':icons,'unavailable':unavailable,'official_preserved':sorted(OFFICIAL & catalog['categories'].keys())})
    print(json.dumps({'imported':len(icons),'unavailable':len(unavailable),'official_preserved':len(OFFICIAL & catalog['categories'].keys())}),flush=True)

if __name__=='__main__':main()
