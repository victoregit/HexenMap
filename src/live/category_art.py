"""Cached personal AppSample category art; no downloads in UI or map rendering."""
from functools import lru_cache
import hashlib
import io
import json
from PIL import Image,ImageOps,ImageTk
from src.live.storage import install_dir

@lru_cache(maxsize=1)
def manifest():
    try:
        source=json.loads((install_dir()/'userData/assets/appsample/SOURCE.json').read_text(encoding='utf-8'))
        return source['icons'] if isinstance(source.get('icons'),dict) else {}
    except (OSError,ValueError,KeyError):return {}

@lru_cache(maxsize=160)
def category_image(category,size=22,collected=False):
    entry=manifest().get(category)
    if not isinstance(entry,dict):return None
    try:
        directory=install_dir()/'userData/assets/appsample';path=(directory/entry['file']).resolve()
        if not path.is_relative_to(directory.resolve()):return None
        raw=path.read_bytes()
        if len(raw)>8*1024*1024 or hashlib.sha256(raw).hexdigest()!=entry['sha256']:return None
        with Image.open(io.BytesIO(raw)) as source:
            if max(source.size)>4096:return None
            image=source.convert('RGBA')
        bounds=image.getbbox()
        if not bounds:return None
        image=ImageOps.contain(image.crop(bounds),(size,size),Image.Resampling.LANCZOS)
        if collected:
            alpha=image.getchannel('A');image=ImageOps.grayscale(image).convert('RGBA');image.putalpha(alpha)
        return image
    except (OSError,ValueError,KeyError):return None

def draw_category_art(canvas,category,x,y,size=22,collected=False):
    root=canvas._root();key=(category,size,collected)
    if not hasattr(root,'_category_art'):root._category_art={}
    if key not in root._category_art:
        image=category_image(category,size,collected)
        root._category_art[key]=ImageTk.PhotoImage(image,master=canvas) if image is not None else None
    photo=root._category_art[key]
    if photo is None:return False
    canvas.create_image(x,y,image=photo);return True
