from dataclasses import replace
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import ctypes as ct

import numpy as np
from PIL import Image

from src.live.image_cache import image_lru,PhotoCache
from src.live.loading import ProcessCatalogSource
from src.live.native import Windows
from src.live.storage import read_settings,write_json,DEFAULT_KEYS


def test_performance_preference_defaults_and_roundtrip_preserve_selection(tmp_path):
    path=tmp_path/'settings.json'
    assert read_settings(path)['performance_mode']=='light'
    for mode,expected in [('global','global'),('light','light'),('unknown','light')]:
        write_json(path,{'categories':['plant'],'hotkeys':DEFAULT_KEYS,'performance_mode':mode})
        data=read_settings(path)
        assert data['performance_mode']==expected and data['categories']==['plant']


def test_idle_loader_retires_process_but_old_timer_cannot_stop_new_request(monkeypatch,tmp_path):
    import src.live.loading as module
    pools=[];timers=[]
    class Pool:
        def __init__(self,**kw):self.closed=False;pools.append(self)
        def submit(self,*args):return SimpleNamespace(result=lambda:args[2])
        def shutdown(self,**kw):self.closed=True
    class Timer:
        def __init__(self,seconds,fn,args=()):self.seconds=seconds;self.fn=fn;self.args=args;timers.append(self)
        def start(self):pass
        def cancel(self):pass
        def fire(self):self.fn(*self.args)
    monkeypatch.setattr(module,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(module.threading,'Timer',Timer)
    source=ProcessCatalogSource(tmp_path)
    assert source('first')=='first' and timers[-1].seconds==5
    old=timers[-1];source('second');old.fire();assert not pools[0].closed
    timers[-1].fire();assert pools[0].closed and source.pool is None
    source('third');assert len(pools)==2
    source.close();assert pools[1].closed


def test_capture_reuses_allocations_keeps_partial_pixels_blank_and_cleans_handles():
    from src.overlay.window_tracker import GameWindowRect
    native=Windows.__new__(Windows);native.foreground=lambda rect:True;calls=[]
    native.u=SimpleNamespace(GetDC=lambda source:1,ReleaseDC=lambda *a:None)
    def bits(dc,bmp,start,height,buffer,info,usage):ct.memset(buffer,80,4*height*4);return height
    native.g=SimpleNamespace(CreateCompatibleDC=lambda dc:2,CreateCompatibleBitmap=lambda *a:calls.append('allocate') or 3,
        SelectObject=lambda *a:4,BitBlt=lambda *a:True,GetDIBits=bits,
        DeleteObject=lambda *a:calls.append('free'),DeleteDC=lambda *a:None)
    rect=GameWindowRect(10,20,4,4,hwnd=99)
    one=native.capture(rect,.5);two=native.capture(rect,.5)
    assert one is two and calls==['allocate']
    assert (one[:2]==80).all() and not one[2:].any()
    full=native.capture(rect);assert (full==80).all() and len(native._capture_slots)==2
    native.close_capture();assert not native._capture_slots and calls.count('free')==2


def test_small_automark_capture_uses_client_coordinates_and_exact_buffer_shape():
    from src.overlay.window_tracker import GameWindowRect
    native=Windows.__new__(Windows);native.foreground=lambda rect:True;calls=[]
    native.u=SimpleNamespace(GetDC=lambda hwnd:calls.append(('dc',hwnd)) or 1,ReleaseDC=lambda *a:None)
    def bits(dc,bmp,start,height,buffer,info,usage):ct.memset(buffer,42,4*3*height);return height
    native.g=SimpleNamespace(CreateCompatibleDC=lambda dc:2,CreateCompatibleBitmap=lambda *a:3,
        SelectObject=lambda *a:4,BitBlt=lambda *args:calls.append(('blit',args[6:8])) or True,GetDIBits=bits,
        DeleteObject=lambda *a:None,DeleteDC=lambda *a:None)
    rect=GameWindowRect(100,200,10,10,hwnd=99)
    result=native.capture(rect,region=(2,3,3,2))
    assert result.shape==(2,3,3) and (result==42).all()
    assert ('dc',99) in calls and ('blit',(2,3)) in calls
    assert native.capture(rect,region=(9,9,3,3)) is None
    native.close_capture()


def test_pil_cache_is_bounded_by_bytes_and_hits_keep_recent_images():
    @image_lru(128,10)
    def picture(color):return Image.new('RGBA',(4,4),color)
    first=picture('red');picture('green')
    assert picture('red') is first
    picture('blue');info=picture.cache_info()
    assert info.currsize==2 and info.bytes==128 and info.hits==1


def test_tk_cache_preserves_images_still_used_by_canvas():
    canvas=SimpleNamespace(winfo_class=lambda:'Canvas',find_all=lambda:[1],type=lambda item:'image',
        itemcget=lambda *a:'visible',winfo_children=lambda:[])
    root=SimpleNamespace(winfo_class=lambda:'Tk',winfo_children=lambda:[canvas])
    cache=PhotoCache(root,budget=64)
    cache.values['used']=('visible',64);cache.values['unused']=('old',64);cache.bytes=128
    cache.prune(force=True)
    assert list(cache.values)==['used'] and cache.bytes==64



def test_rapid_selection_cannot_acknowledge_release_of_a_still_active_recognizer():
    import threading
    from src.live.desktop import DesktopApp
    app=DesktopApp.__new__(DesktopApp)
    app.reference_lock=threading.Lock();app.reference_released=threading.Event()
    old=object();app.recognizer=None
    app.acknowledge_reference_release(old)
    assert not app.reference_released.is_set()
    app.recognizer=object();app.acknowledge_reference_release(None)
    assert not app.reference_released.is_set()
    app.recognizer=None;app.acknowledge_reference_release(None)
    assert app.reference_released.is_set()


def test_selector_draws_use_the_returned_cached_photo_without_private_root_dicts(monkeypatch):
    import src.live.oculus_art as oculi
    import src.live.marker_art as markers
    image=Image.new('RGBA',(22,22),'white');photo=object();calls=[]
    canvas=SimpleNamespace(create_image=lambda *a,**kw:calls.append(kw['image']))
    monkeypatch.setattr(oculi,'selector_image',lambda category,size=30:image)
    monkeypatch.setattr(oculi,'tk_image',lambda *a:photo)
    oculi.draw_oculus(canvas,SimpleNamespace(members={'cryoculus'},label='Cryoculi',icon='cryoculus'),10,10)
    monkeypatch.setattr(markers,'legend_image',lambda *a:image)
    monkeypatch.setattr(markers,'tk_image',lambda *a:photo)
    assert markers.draw_chest_legend(canvas,'common-chest',10,10)
    assert calls==[photo,photo]


def test_frozen_telemetry_counts_bootstrap_parent_as_part_of_app(tmp_path,monkeypatch):
    import sys,json
    import src.live.performance as module
    memory=SimpleNamespace(rss=1024,peak_wset=2048)
    def process(pid):return SimpleNamespace(pid=pid,exe=lambda:'D:/HexenMap.exe',memory_info=lambda:memory,
        memory_full_info=lambda:SimpleNamespace(uss=512),cpu_times=lambda:SimpleNamespace(user=0.,system=0.))
    main=process(2);parent=process(1);main.parent=lambda:parent;parent.children=lambda recursive:[main]
    monkeypatch.setattr(module.psutil,'Process',lambda:main)
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    path=tmp_path/'performance.jsonl';telemetry=module.PerformanceTelemetry(path)
    telemetry.record(None,'light','hidden');telemetry.close()
    row=json.loads(path.read_text())
    assert row['processes']==2 and row['rss_MiB']==round(2048/1024**2,2)
