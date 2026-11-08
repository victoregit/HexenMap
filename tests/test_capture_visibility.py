import ctypes as ct
import os
from types import SimpleNamespace
import pytest
from src.live.native import Windows
from src.live.storage import read_settings,write_json,DEFAULT_KEYS


def native(fail=None):
    n=Windows.__new__(Windows);calls=[]
    def pid(hwnd,pointer):ct.cast(pointer,ct.POINTER(ct.c_ulong)).contents.value=os.getpid() if hwnd!=3 else 999999
    def affinity(hwnd,mode):calls.append((hwnd,mode));return not (hwnd==fail and mode==0)
    n.u=SimpleNamespace(SetWindowDisplayAffinity=affinity,IsWindow=lambda h:h!=4,GetWindowThreadProcessId=pid)
    return n,calls


def test_capture_toggle_applies_to_owned_windows_and_new_surfaces():
    n,calls=native();n.capture_windows={1,2,3,4};n.set_capture_visible(True)
    assert set(calls)=={(1,0),(2,0)} and n.capture_windows=={1,2}
    n.capture_policy(5);assert calls[-1]==(5,0)
    n.set_capture_visible(False);assert set(calls[-3:])=={(1,0x11),(2,0x11),(5,0x11)}


def test_capture_failure_does_not_change_the_preference_and_rolls_back():
    n,calls=native(fail=2);n.capture_windows={1,2};n.capture_visible=False
    with pytest.raises(OSError):n.set_capture_visible(True)
    assert not n.capture_visible
    if (1,0) in calls:assert (1,0x11) in calls


def test_capture_preference_round_trips_without_changing_other_settings(tmp_path):
    path=tmp_path/'settings.json'
    data={'categories':['common-chest'],'hotkeys':dict(DEFAULT_KEYS),'capture_visible':True}
    write_json(path,data);result=read_settings(path)
    assert result['capture_visible'] and result['categories']==data['categories'] and result['hotkeys']==data['hotkeys']
    data['capture_visible']='true';write_json(path,data);assert not read_settings(path)['capture_visible']


def test_sharing_mode_captures_the_game_client_not_the_desktop():
    from src.overlay.window_tracker import GameWindowRect
    for visible in (False,True):
        n=Windows.__new__(Windows);n.capture_visible=visible;calls=[]
        n.foreground=lambda rect:True
        n.u=SimpleNamespace(GetDC=lambda source:(calls.append(('get',source)) or 1),ReleaseDC=lambda source,dc:calls.append(('release',source)))
        def copy(*args):calls.append(('copy',args[6:8]));return True
        def bits(dc,bmp,start,height,buffer,info,usage):ct.memset(buffer,80,2*2*4);return height
        n.g=SimpleNamespace(CreateCompatibleDC=lambda dc:2,CreateCompatibleBitmap=lambda *a:3,
            SelectObject=lambda *a:4,BitBlt=copy,GetDIBits=bits,DeleteObject=lambda *a:None,DeleteDC=lambda *a:None)
        rect=GameWindowRect(10,20,2,2,hwnd=99)
        result=n.capture(rect)
        assert result.shape==(2,2,3) and (result==80).all()
        assert ('get',99 if visible else None) in calls
        assert ('copy',(0,0) if visible else (10,20)) in calls
        assert ('release',99 if visible else None) in calls
