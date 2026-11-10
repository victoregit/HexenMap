"""Bundled official map artwork for the six category headings."""
from functools import lru_cache
import hashlib
import io
import json

from PIL import Image, ImageOps

from src.live.image_cache import cached_photo
from src.live.storage import bundle_dir

GROUP_ICONS = {
    'Destaques': 'anemoculus',
    'Baús': 'common-chest',
    'Enigmas': 'time-trial',
    'Recursos': 'sweet-flower',
    'Exploração': 'teleport-waypoint',
    'Inimigos': 'slime',
}


@lru_cache(maxsize=24)
def group_image(group, size=22):
    category = GROUP_ICONS.get(group)
    if category is None:
        return None
    directory = bundle_dir() / 'data/assets/groups'
    try:
        meta = json.loads((directory / 'SOURCE.json').read_text(encoding='utf-8'))['icons'][category]
        path = (directory / meta['file']).resolve()
        if not path.is_relative_to(directory.resolve()):
            return None
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta['sha256']:
            return None
        with Image.open(io.BytesIO(raw)) as source:
            if max(source.size) > 4096:
                return None
            image = source.convert('RGBA')
        bounds = image.getbbox()
        if bounds:
            return ImageOps.contain(image.crop(bounds), (size, size), Image.Resampling.LANCZOS)
    except (OSError, ValueError, KeyError):
        return None
    return None


def draw_group_art(canvas, group, x, y, size=22):
    image = group_image(group, size)
    if image is None:
        return False
    photo = cached_photo(canvas, ('group-heading', group, size), image)
    canvas.create_image(x, y, image=photo)
    return True
