"""Prepare reviewed official chest art in the personal installation only."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Verify installed images without network or writes')
    args=parser.parse_args()
    source=json.loads((ROOT/'data/assets/chests/SOURCE.json').read_text(encoding='utf-8'))
    output=ROOT/'userData/assets/chests'
    prepared=[]
    for category,entry in source['icons'].items():
        path=(output/entry['file']).resolve()
        if not path.is_relative_to(output.resolve()):raise ValueError('Invalid asset destination')
        raw=path.read_bytes() if args.check else urllib.request.urlopen(entry['url'],timeout=30).read()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError(f'Hash mismatch: {category}')
        with Image.open(io.BytesIO(raw)) as image:
            if image.format!='PNG' or not image.convert('RGBA').getbbox():raise ValueError(f'Invalid image: {category}')
        prepared.append((path,raw))
    if not args.check:
        output.mkdir(parents=True,exist_ok=True)
        for path,raw in prepared:
            temporary=path.with_suffix('.png.tmp');temporary.write_bytes(raw);temporary.replace(path)
    print(f'{len(prepared)} official chest images verified; personal use only')


if __name__=='__main__':main()
