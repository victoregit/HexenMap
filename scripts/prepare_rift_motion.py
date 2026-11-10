"""Separate the approved moving rift from its independently rotating emblem."""
import hashlib
import json
from PIL import Image
from scripts import render_electro_rift_climax as approved


def main():
    texture=approved.prepare()
    blank=Image.new('RGBA',(84,82))
    atlas=Image.new('RGBA',(8*192,15*192))
    for index in range(120):
        frame=approved.render(index/24,texture,blank).resize((192,192),Image.Resampling.LANCZOS)
        atlas.paste(frame,(index%8*192,index//8*192))
    assets=approved.ROOT/'data/assets/brand'
    atlas.save(assets/'minimized-rift.png')
    with Image.open(approved.REF/'electro-symbol-master.png') as symbol:
        symbol.convert('RGBA').save(assets/'electro-symbol.png')
    manifest=assets/'SOURCE.json'
    metadata=json.loads(manifest.read_text(encoding='utf-8'))
    for name in ('minimized-rift.png','electro-symbol.png'):
        metadata['files'][name]={'sha256':hashlib.sha256((assets/name).read_bytes()).hexdigest()}
    manifest.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


if __name__=='__main__':main()
