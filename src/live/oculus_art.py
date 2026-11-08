"""Verified personal official oculus art for the category selector only."""
from functools import lru_cache
import hashlib
import json
import io
from PIL import Image,ImageOps
from src.live.storage import bundle_dir,install_dir
from src.live.marker_art import tk_image

ORDER=('anemoculus','geoculus','electroculus','dendroculus','hydroculus','pyroculus','lunoculus','cryoculus')
LABELS=('Anemoculi','Geoculi','Electroculi','Dendroculi','Hydroculi','Pyroculi','Lunoculi','Cryoculi')

def category_for(entry):
    return next((c for c in ORDER if c in entry.members),dict(zip(LABELS,ORDER)).get(entry.label))

@lru_cache(maxsize=8)
def oculus_art(category):
    if category not in ORDER:return None
    try:
        meta=json.loads((bundle_dir()/'data/assets/oculi/SOURCE.json').read_text(encoding='utf-8'))['icons'][category]
        directory=install_dir()/'userData/assets/oculi';path=(directory/meta['file']).resolve()
        if not path.is_relative_to(directory.resolve()):return None
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:return None
        with Image.open(io.BytesIO(raw)) as source:
            if source.format!='PNG' or max(source.size)>4096:return None
            image=source.convert('RGBA')
        bounds=image.getbbox()
        return image.crop(bounds) if bounds else None
    except (OSError,ValueError,KeyError):return None

@lru_cache(maxsize=8)
def selector_image(category):
    image=oculus_art(category)
    return ImageOps.contain(image,(30,30),Image.Resampling.LANCZOS) if image is not None else None


def draw_oculus(canvas,entry,x,y):
    category=category_for(entry);image=selector_image(category)
    if image is None:
        from src.live.icons import draw_marker
        draw_marker(canvas,entry.icon,x,y,scale=1.2);return
    photo=tk_image(canvas,('oculus-selector',category,30),image)
    canvas.create_image(x,y,image=photo)
