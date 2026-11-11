"""Offline, viewport-only tile cache for the installed personal Teyvat dataset."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,math
import threading
from PIL import Image,ImageEnhance
from src.live.storage import install_dir,bundle_dir


class WorldTiles:
    def __init__(self,directory=None,*,map_id=None,layer='surface'):
        if map_id is None:
            self.meta=json.loads((bundle_dir()/'data/world_map/SOURCE.json').read_text(encoding='utf-8'))
        else:
            from src.live.map_registry import tile_metadata
            self.meta=tile_metadata(map_id,layer)
        self.directory=Path(directory) if directory else install_dir()/'userData/reference-tile-cache'/self.meta['dataset']
        self.levels=[int(p.name) for p in self.directory.iterdir() if p.is_dir() and p.name.isdecimal()] if self.directory.exists() else []
        self.levels.sort();self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='WorldTiles')
        self.pending={};self.cache=OrderedDict();self.bytes=0;self.closed=False
        self.overlay=None;self.overlay_lock=threading.Lock()
        factor=256*2**(14-self.meta['base_zoom']);a,b,c,d=self.meta['bounds_base_tiles']
        self.bounds=(a*factor,b*factor,(c+1)*factor,(d+1)*factor)
        if self.meta.get('overlay'):
            from src.live.appsample_catalog import project
            b=self.meta['overlay']['bounds']
            left,top=project(b['west'],b['north']);right,bottom=project(b['east'],b['south'])
            self.bounds=(left,top,right,bottom)
    def load(self,key):
        level,x,y,pixels=key
        for source in reversed(self.levels):
            if source>level:continue
            factor=2**(level-source);sx=x//factor;sy=y//factor
            path=self.directory/str(source)/f'{sx}_{sy}.jpg'
            if not path.is_file():continue
            with Image.open(path) as opened:
                if opened.size!=(256,256):continue
                image=opened.convert('RGB')
            if factor>1:
                ox=(x-sx*factor)*256/factor;oy=(y-sy*factor)*256/factor
                image=image.crop((round(ox),round(oy),round(ox+256/factor),round(oy+256/factor)))
            return self.apply_overlay(key,image.resize((pixels,pixels),Image.Resampling.LANCZOS))
        if self.meta.get('overlay'):
            return self.apply_overlay(key,Image.new('RGB',(pixels,pixels)))
        return None

    def apply_overlay(self,key,image):
        if not self.meta.get('overlay'):return image
        with self.overlay_lock:
            if self.closed:return None
            if self.overlay is None:
                path=install_dir()/'userData/references/appsample'/self.meta['map_id']/self.meta['layer']/'overlay.png'
                with Image.open(path) as source:self.overlay=source.convert('RGBA')
            overlay=self.overlay
        level,x,y,pixels=key
        world_side=256*2**(14-level);left,top,right,bottom=self.bounds
        sx,sy=overlay.width/(right-left),overlay.height/(bottom-top)
        transformed=overlay.transform((pixels,pixels),Image.Transform.AFFINE,
            (world_side/pixels*sx,0,(x*world_side-left)*sx,
             0,world_side/pixels*sy,(y*world_side-top)*sy),Image.Resampling.BICUBIC)
        result=ImageEnhance.Brightness(image).enhance(.5).convert('RGBA')
        result.alpha_composite(transformed)
        return result.convert('RGB')
    def get(self,key):
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        if not self.closed and key not in self.pending and len(self.pending)<32:self.pending[key]=self.pool.submit(self.load,key)
        return None
    def poll(self):
        changed=False
        for key,future in list(self.pending.items()):
            if not future.done():continue
            del self.pending[key]
            try:image=future.result()
            except (OSError,ValueError):image=None
            size=image.width*image.height*3 if image else 0
            self.cache[key]=image;self.bytes+=size;changed=True
            overlay_bytes=self.overlay.width*self.overlay.height*4 if self.overlay else 0
            while self.bytes>max(4*1024**2,32*1024**2-overlay_bytes) or len(self.cache)>512:
                _,old=self.cache.popitem(last=False)
                if old:self.bytes-=old.width*old.height*3
        return changed
    def close(self):
        self.closed=True
        for future in self.pending.values():future.cancel()
        self.pool.shutdown(wait=False,cancel_futures=True);self.pending.clear();self.cache.clear();self.bytes=0
        with self.overlay_lock:self.overlay=None


def screen_to_world(x,y,width,height,cx,cy,zoom):
    scale=2**(zoom-14)
    return cx+(x-width/2)/scale,cy+(y-height/2)/scale
