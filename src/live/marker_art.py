"""Cached personal HoYoLAB artwork and shared pin drawing/input geometry."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageTk

from src.live.storage import bundle_dir, install_dir

LOG=logging.getLogger(__name__)
CHESTS=frozenset(('common-chest','exquisite-chest','precious-chest','luxurious-chest','remarkable-chest'))


def chest_art(category):
    if category not in CHESTS:return None
    return _load_chest_art(category)


@lru_cache(maxsize=5)
def _load_chest_art(category):
    try:
        meta=json.loads((bundle_dir()/'data/assets/chests/SOURCE.json').read_text(encoding='utf-8'))['icons'][category]
        directory=install_dir()/'userData/assets/chests'
        path=(directory/meta['file']).resolve()
        if not path.is_relative_to(directory.resolve()):raise ValueError('Asset outside personal directory')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Artwork hash mismatch')
        with Image.open(path) as source:
            image=source.convert('RGBA')
        box=image.getbbox()
        if not box or max(image.size)>4096:raise ValueError('Invalid chest artwork')
        return image.crop(box)
    except (OSError,ValueError,KeyError) as exc:
        LOG.warning('Arte pessoal de %s indisponível; usando símbolo existente: %s',category,exc)
        return None


@dataclass(frozen=True)
class MarkerGeometry:
    left: int=-12
    top: int=-12
    right: int=13
    bottom: int=13
    # Nonempty rows mean an asymmetric artwork pin, anchored at its tip.
    rows: tuple=()
    size: tuple=()

    def bounds(self,x,y):
        x,y=round(x),round(y)
        return x+self.left,y+self.top,x+self.right,y+self.bottom

    def contains(self,x,y,px,py):
        dx,dy=px-round(x),py-round(y)
        if not self.rows:return self.left<=dx<self.right and self.top<=dy<self.bottom
        return any(a<=dx<b and c<=dy<d for a,c,b,d in self.rows)

    def rectangles(self,x,y):
        x,y=round(x),round(y)
        if not self.rows:return (self.bounds(x,y),)
        return tuple((x+a,y+c,x+b,y+d) for a,c,b,d in self.rows)

    def inside_circle(self,x,y,cx,cy,radius):
        if not self.rows:
            return (x-cx)**2+(y-cy)**2<=max(0,radius-12)**2
        # Check actual opaque row endpoints, not the transparent square corners.
        x,y=round(x),round(y)
        return all((x+dx-cx)**2+(y+dy-cy)**2<=radius**2
                   for a,c,b,d in self.rows for dx in (a,b-1) for dy in (c,d-1))


LEGACY=MarkerGeometry()


@lru_cache(maxsize=32)
def pin_shell(width,height):
    factor=4
    image=Image.new('RGBA',(width*factor,height*factor))
    draw=ImageDraw.Draw(image)
    # Draw at supersampled coordinates, with a short, broad tapered tip.
    def scaled_shape(inset,fill):
        left=inset*factor;top=inset*factor;right=(width-1-inset)*factor
        diameter=right-left
        draw.polygon([(left+2*factor,top+diameter*.65),(width/2*factor,(height-1-inset)*factor),
                      (right-2*factor,top+diameter*.65)],fill=fill)
        draw.ellipse((left,top,right,top+diameter),fill=fill)
    scaled_shape(0,'#14222e')
    scaled_shape(.7,'#eee7ce')
    scaled_shape(2,'#344b59')
    image=image.resize((width,height),Image.Resampling.LANCZOS)
    # Win32 uses a color key, not per-pixel alpha. Binary outer alpha prevents
    # antialiasing against the magenta key from leaving colored fringes.
    image.putalpha(image.getchannel('A').point(lambda a:255 if a>=128 else 0))
    image.putpixel((width//2,height-1),(20,34,46,255))
    return image


@lru_cache(maxsize=32)
def shell_geometry(width,height):
    alpha=pin_shell(width,height).getchannel('A')
    left=-(width//2);top=1-height;rows=[]
    for y in range(height):
        xs=[x for x in range(width) if alpha.getpixel((x,y))]
        if not xs:continue
        a,b=left+min(xs),left+max(xs)+1;c=top+y
        if rows and rows[-1][0]==a and rows[-1][2]==b and rows[-1][3]==c:
            old=rows[-1];rows[-1]=(old[0],old[1],old[2],c+1)
        else:rows.append((a,c,b,c+1))
    return MarkerGeometry(left,top,left+width,top+height,tuple(rows),(width,height))


def marker_geometry(category,surface='map',dpi=1.):
    if chest_art(category) is None:return LEGACY
    w,h=(24,32) if surface=='minimap' else (28,36)
    dpi=max(.75,min(3.,round(dpi*4)/4))
    return shell_geometry(round(w*dpi),round(h*dpi))


@lru_cache(maxsize=160)
def pin_image(category,width,height,collected=False):
    source=chest_art(category)
    if source is None:return None
    image=pin_shell(width,height).copy()
    # Fit the original image inside the circular head, preserving its aspect.
    icon=ImageOps.contain(source,(width-8,width-10),Image.Resampling.LANCZOS)
    image.alpha_composite(icon,((width-icon.width)//2,(width-icon.height)//2))
    image.putalpha(pin_shell(width,height).getchannel('A'))
    if collected:
        alpha=image.getchannel('A')
        image=ImageOps.colorize(ImageOps.grayscale(image),'#18252e','#a6adb0').convert('RGBA')
        image.putalpha(alpha)
    return image


def tk_image(canvas,key,image):
    root=canvas._root()
    if not hasattr(root,'_chest_images'):root._chest_images={}
    if key not in root._chest_images:
        root._chest_images[key]=ImageTk.PhotoImage(image,master=canvas)
    return root._chest_images[key]


def draw_pin(canvas,category,x,y,collected=False,geometry=None):
    from src.live.icons import draw_marker
    geometry=geometry or marker_geometry(category)
    if not geometry.size:return draw_marker(canvas,category,x,y,collected=collected)
    w,h=geometry.size
    image=pin_image(category,w,h,collected)
    if image is None:return draw_marker(canvas,category,x,y,collected=collected)
    photo=tk_image(canvas,('pin',category,w,h,collected),image)
    canvas.create_image(round(x)+geometry.left,round(y)+geometry.top,image=photo,anchor='nw')


def draw_chest_legend(canvas,category,x,y,scale=1.,collected=False):
    source=chest_art(category)
    if source is None:return False
    size=max(12,round(22*scale))
    key=('legend',category,size,collected)
    root=canvas._root()
    if key not in getattr(root,'_chest_images',{}):
        image=ImageOps.contain(source,(size,size),Image.Resampling.LANCZOS)
        if collected:
            alpha=image.getchannel('A');image=ImageOps.grayscale(image).convert('RGBA');image.putalpha(alpha)
        tk_image(canvas,key,image)
    canvas.create_image(x,y,image=root._chest_images[key])
    return True
