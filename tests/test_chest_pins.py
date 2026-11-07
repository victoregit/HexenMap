import hashlib
import json
from types import SimpleNamespace

from PIL import Image
import pytest

from src.live import marker_art as art
from src.live.presentation import MarkerCanvas,outside_controls


@pytest.fixture
def artwork(monkeypatch):
    image=Image.new('RGBA',(80,60),'#d6a957')
    monkeypatch.setattr(art,'chest_art',lambda category:image if category in art.CHESTS else None)
    art.pin_image.cache_clear()
    yield
    art.pin_image.cache_clear()


@pytest.mark.parametrize('surface,size',[('minimap',(24,32)),('map',(28,36))])
def test_tip_anchor_and_transparent_corners_match_input(surface,size,artwork):
    g=art.marker_geometry('common-chest',surface)
    assert g.size==size and g.bottom==1
    image=art.pin_image('common-chest',*size)
    alpha=image.getchannel('A')
    assert g.contains(100,100,100,100)
    assert not g.contains(100,100,100+g.left,100+g.top)
    for y in range(size[1]):
        for x in range(size[0]):
            px,py=100+g.left+x,100+g.top+y
            assert g.contains(100,100,px,py)==bool(alpha.getpixel((x,y)))
            assert any(a<=px<b and c<=py<d for a,c,b,d in g.rectangles(100,100))==bool(alpha.getpixel((x,y)))


def test_scaled_pin_has_same_world_anchor(artwork):
    g=art.marker_geometry('luxurious-chest','map',1.5)
    assert g.size==(42,54) and g.bounds(250,200)[3]==201
    assert g.contains(250,200,250,200)


def test_collected_art_preserves_shape_and_cache(artwork):
    image=art.pin_image('common-chest',28,36)
    collected=art.pin_image('common-chest',28,36,True)
    assert image is art.pin_image('common-chest',28,36)
    assert image.getchannel('A').tobytes()==collected.getchannel('A').tobytes()
    assert image.convert('RGB').tobytes()!=collected.convert('RGB').tobytes()
    assert set(image.getchannel('A').tobytes())=={0,255}


def test_head_above_anchor_is_clipped_by_controls_and_circle(artwork):
    g=art.marker_geometry('common-chest','minimap')
    pin=SimpleNamespace(x=100,y=100,geometry=g)
    assert outside_controls([pin],[(90,72,110,80)])==[]
    assert not g.inside_circle(100,80,100,100,40) # Tip is inside; head is outside.
    assert g.inside_circle(100,110,100,100,40)
    assert outside_controls([pin],[(130,72,140,80)])==[pin]


def test_missing_or_modified_personal_asset_falls_back_without_wrong_art(tmp_path,monkeypatch):
    directory=tmp_path/'data/assets/chests';directory.mkdir(parents=True)
    personal=tmp_path/'userData/assets/chests';personal.mkdir(parents=True)
    file=personal/'common.png';Image.new('RGBA',(32,32),'gold').save(file)
    meta={'icons':{'common-chest':{'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}}}
    (directory/'SOURCE.json').write_text(json.dumps(meta),encoding='utf-8')
    monkeypatch.setattr(art,'bundle_dir',lambda:tmp_path)
    monkeypatch.setattr(art,'install_dir',lambda:tmp_path)
    art._load_chest_art.cache_clear()
    assert art.chest_art('common-chest') is not None
    file.write_bytes(b'changed')
    art._load_chest_art.cache_clear()
    assert art.marker_geometry('common-chest') is art.LEGACY
    file.unlink();art._load_chest_art.cache_clear()
    assert art.marker_geometry('common-chest') is art.LEGACY
    art._load_chest_art.cache_clear()


def test_surface_change_rebuilds_pin_but_motion_reuses_it(artwork):
    class Canvas:
        def __init__(self):self.items={};self.n=0;self.moves=[]
        def find_all(self):return tuple(self.items)
        def addtag_withtag(self,tag,i):self.items[i]=tag
        def delete(self,tag):self.items={i:t for i,t in self.items.items() if t!=tag}
        def move(self,*args):self.moves.append(args)
    canvas=Canvas();draws=[]
    def draw(*args,**kwargs):
        canvas.n+=1;canvas.items[canvas.n]=None;draws.append(kwargs)
    renderer=MarkerCanvas(canvas,draw)
    pin=SimpleNamespace(item=SimpleNamespace(id='chest',category='common-chest'),x=100.4,y=100.4,
                        geometry=art.marker_geometry('common-chest','minimap'))
    renderer.render([pin],lambda _:False)
    pin.x=100.6;pin.y=101.2;renderer.render([pin],lambda _:False)
    assert len(draws)==1 and canvas.moves[-1][1:]==(1,1)
    pin.geometry=art.marker_geometry('common-chest','map');renderer.render([pin],lambda _:False)
    assert len(draws)==2 and draws[-1]['geometry'].size==(28,36)


@pytest.mark.parametrize('apply_success',[True,False])
def test_batched_native_mask_unions_overlaps_and_transfers_handle(apply_success):
    import ctypes as ct
    import struct
    from src.live.native import Windows
    native=Windows.__new__(Windows);payload=[];deleted=[]
    def create(transform,size,buffer):
        raw=ct.string_at(buffer,size)
        header=struct.unpack('<IIIIiiii',raw[:32])
        payload.extend(struct.unpack('<iiii',raw[i:i+16]) for i in range(32,len(raw),16))
        assert header[:4]==(32,1,len(payload),len(payload)*16)
        return 42
    native.g=SimpleNamespace(ExtCreateRegion=create,DeleteObject=lambda handle:deleted.append(handle))
    native.u=SimpleNamespace(SetWindowRgn=lambda *args:apply_success)
    boxes=[(-2,0,3,3),(1,1,5,4),(8,1,9,2)]
    if apply_success:native.input_region(1,boxes)
    else:
        with pytest.raises(OSError):native.input_region(1,boxes)
    expected={(x,y) for a,b,c,d in boxes for x in range(a,c) for y in range(b,d)}
    actual=[(x,y) for a,b,c,d in payload for x in range(a,c) for y in range(b,d)]
    assert set(actual)==expected and len(actual)==len(expected)
    assert deleted==([] if apply_success else [42])
