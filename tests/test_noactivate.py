import ctypes as ct
from ctypes import wintypes as wt
from types import SimpleNamespace
import sys
import pytest

from src.live.noactivate import NoActivate


def test_noactivate_delivers_mouse_message_and_forwards_other_messages():
    guard=NoActivate.__new__(NoActivate);calls=[];guard.callback=object();guard.handles={1}
    guard.api=SimpleNamespace(RemoveWindowSubclass=lambda *a:calls.append('removed'),
                             DefSubclassProc=lambda *a:42)
    assert guard.dispatch(1,0x21,0,0,1,0)==3
    assert guard.dispatch(1,0x20,0,0,1,0)==42
    assert guard.dispatch(1,0x82,0,0,1,0)==42
    assert not guard.handles and calls==['removed']


@pytest.mark.skipif(sys.platform!='win32',reason='Windows/Tk native controls')
def test_real_tk_parent_and_children_reject_mouse_activation_and_release_hooks():
    import tkinter as tk
    root=tk.Tk();root.withdraw()
    button=tk.Button(root,text='Coletar');button.pack();root.update_idletasks()
    button.winfo_id()
    user=ct.WinDLL('user32')
    user.GetAncestor.argtypes=[wt.HWND,wt.UINT];user.GetAncestor.restype=wt.HWND
    user.SendMessageW.argtypes=[wt.HWND,wt.UINT,wt.WPARAM,wt.LPARAM];user.SendMessageW.restype=ct.c_ssize_t
    guard=NoActivate();top=user.GetAncestor(root.winfo_id(),2)
    try:
        guard.install(top)
        assert user.SendMessageW(top,0x21,0,0)==3
        assert user.SendMessageW(button.winfo_id(),0x21,0,0)==3
        count=len(guard.handles);guard.install(top)
        assert len(guard.handles)==count and count>=2
    finally:
        root.destroy();guard.close()
    assert not guard.handles
