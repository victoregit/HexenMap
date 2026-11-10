from concurrent.futures import CancelledError
from types import SimpleNamespace
import struct
import time
import numpy as np
import pytest
from src.live.input_regions import region_data,placement_data,InputRegions
from src.live.marker_art import MarkerGeometry
from src.live.presentation import MarkerCanvas


def pixels(raw):
    if not raw:return set()
    return {(x,y) for left,top,right,bottom in np.frombuffer(raw[32:],np.int32).reshape(-1,4)
            for x in range(left,right) for y in range(top,bottom)}


def test_bands_preserve_transparent_holes_and_compress_identical_rows():
    boxes=[(0,0,3,5),(2,0,5,5),(7,1,8,3)]
    raw=region_data(boxes)
    expected={(x,y) for a,c,b,d in boxes for x in range(a,b) for y in range(c,d)}
    assert pixels(raw)==expected
    assert struct.unpack('<IIIIiiii',raw[:32])[2]==4
    assert region_data([])==b''
    with pytest.raises(CancelledError):region_data(boxes,lambda:True)


def test_region_builder_discards_old_geometry_and_cancelled_results():
    builder=InputRegions();geometry=MarkerGeometry()
    try:
        builder.get('old',[(0,0,geometry)])
        deadline=time.monotonic()+3
        raw=None
        while raw is None and time.monotonic()<deadline:
            raw=builder.get('new',[(100,100,geometry)]);time.sleep(.001)
        assert raw is not None and (100,100) in pixels(raw) and (0,0) not in pixels(raw)
        builder.cancel();assert builder.future is None and builder.key is None
    finally:builder.close()


def test_raster_mask_matches_exact_union_including_negative_origins_and_holes():
    geometry=MarkerGeometry(-2,-2,3,3,((-2,-2,3,-1),(-2,-1,-1,2),(2,-1,3,2),(-2,2,3,3)),(5,5))
    placements=[(-10,-20,geometry),(0,0,geometry),(3,0,geometry)]
    assert pixels(placement_data(placements))==pixels(region_data(b for x,y,g in placements for b in g.rectangles(x,y)))
    assert (0,0) not in pixels(placement_data(placements))


def test_completed_partial_mask_is_reused_only_at_identical_current_positions():
    builder=InputRegions();g=MarkerGeometry();points=[(0,0,g)]
    try:
        deadline=time.monotonic()+3;raw=None
        while raw is None and time.monotonic()<deadline:
            raw=builder.get('one',points,scope=1);time.sleep(.001)
        assert raw is not None
        assert builder.get('more',points+[(100,100,g)],scope=1)==raw
        assert builder.get('moved',[(1,0,g),(100,100,g)],scope=1) is None
        assert builder.get('new-map',points,scope=2) is None
    finally:builder.close()


def test_prepared_region_is_accepted_by_windows_gdi():
    import sys,ctypes as ct
    if sys.platform!='win32':pytest.skip('Windows GDI')
    g=ct.WinDLL('gdi32')
    g.ExtCreateRegion.argtypes=[ct.c_void_p,ct.c_uint32,ct.c_void_p];g.ExtCreateRegion.restype=ct.c_void_p
    g.PtInRegion.argtypes=[ct.c_void_p,ct.c_int,ct.c_int];g.PtInRegion.restype=ct.c_int
    g.DeleteObject.argtypes=[ct.c_void_p]
    shape=MarkerGeometry(-2,-2,3,3,((-2,-2,3,-1),(-2,-1,-1,2),(2,-1,3,2),(-2,2,3,3)),(5,5))
    raw=placement_data([(10,10,shape),(20,20,shape)]);buffer=ct.create_string_buffer(raw)
    handle=g.ExtCreateRegion(None,len(raw),buffer)
    assert handle
    try:
        assert g.PtInRegion(handle,8,8) and not g.PtInRegion(handle,10,10)
        assert g.PtInRegion(handle,18,18) and not g.PtInRegion(handle,20,20)
    finally:g.DeleteObject(handle)


def test_input_window_is_not_reconfigured_for_unchanged_drawn_pins():
    from src.live.desktop import DesktopApp
    calls=[];rect=SimpleNamespace(hwnd=1,x=0,y=0,width=1920,height=1080)
    pin=SimpleNamespace(x=30,y=40,geometry=MarkerGeometry())
    app=DesktopApp.__new__(DesktopApp)
    app.input_hwnd=2;app.control_down=True;app.visible_pins=[pin];app.selection_epoch=1
    app.session=SimpleNamespace(observation=SimpleNamespace(fresh=lambda _:True))
    key=(app.rect_key(rect),1,((30,40,pin.geometry),))
    app.input_boxes=None;app.input_active=False;app.input_placement=None
    app.input_regions=SimpleNamespace(get=lambda *a,**k:b'prepared',ready_key=key)
    app.native=SimpleNamespace(input_region_data=lambda *a:calls.append('mask'),
        interactive=lambda *a:calls.append('interactive'),place=lambda *a:calls.append('place'),hide=lambda *a:calls.append('hide'))
    app.input_canvas=SimpleNamespace(configure=lambda **k:calls.append('configure'))
    app._sync_input(rect);before=list(calls);app._sync_input(rect)
    assert calls==before==['mask','configure','interactive','place']
    app.control_down=False;app._sync_input(rect)
    assert not app.input_active and calls[-2:]==['interactive','hide']


def test_large_reveal_never_enumerates_existing_canvas_items():
    class Canvas:
        def __init__(self):self.n=0;self.tags=[]
        def create_image(self,*a,**kw):self.n+=1;return self.n
        def addtag_withtag(self,*a):self.tags.append(a)
        def find_all(self):raise AssertionError('Quadratic canvas enumeration')
    canvas=Canvas();renderer=MarkerCanvas(canvas,lambda target,*a,**kw:target.create_image(0,0))
    pins=[SimpleNamespace(item=SimpleNamespace(id=str(n),category='common-chest'),x=n,y=0) for n in range(2000)]
    renderer.render(pins,lambda _:True)
    assert canvas.n==len(canvas.tags)==2000


def test_render_budget_defers_creation_and_never_exposes_undrawn_pins(monkeypatch):
    import src.live.presentation as module
    clock=[0.]
    monkeypatch.setattr(module.time,'perf_counter',lambda:clock[0])
    class Canvas:
        def create_image(self,*a,**kw):clock[0]+=.004;return int(clock[0]*1000)
        def addtag_withtag(self,*a):pass
    renderer=MarkerCanvas(Canvas(),lambda target,*a,**kw:target.create_image(0,0))
    pins=[SimpleNamespace(item=SimpleNamespace(id=str(n),category='common-chest'),x=n,y=0) for n in range(10)]
    first=renderer.render(pins,lambda _:False,budget_ms=6.)
    assert len(first)==2 and len(renderer.entries)==2
    for _ in range(5):shown=renderer.render(pins,lambda _:False,budget_ms=6.)
    assert shown==pins and len(renderer.entries)==10
