"""Keep clicks on our own Tk overlay controls from activating their window."""
import ctypes as ct
from ctypes import wintypes as wt
import os


def materialize_controls(widget):
    widget.winfo_id()
    for child in widget.winfo_children():materialize_controls(child)


class NoActivate:
    def __init__(self):
        self.u=ct.WinDLL('user32',use_last_error=True)
        self.api=ct.WinDLL('comctl32',use_last_error=True)
        self.handles=set()
        self.callback_type=ct.WINFUNCTYPE(ct.c_ssize_t,wt.HWND,wt.UINT,wt.WPARAM,wt.LPARAM,ct.c_size_t,ct.c_size_t)
        self.callback=self.callback_type(self.dispatch)
        self.api.SetWindowSubclass.argtypes=[wt.HWND,self.callback_type,ct.c_size_t,ct.c_size_t]
        self.api.SetWindowSubclass.restype=wt.BOOL
        self.api.RemoveWindowSubclass.argtypes=[wt.HWND,self.callback_type,ct.c_size_t]
        self.api.RemoveWindowSubclass.restype=wt.BOOL
        self.api.DefSubclassProc.argtypes=[wt.HWND,wt.UINT,wt.WPARAM,wt.LPARAM]
        self.api.DefSubclassProc.restype=ct.c_ssize_t
        self.u.GetWindowThreadProcessId.argtypes=[wt.HWND,ct.POINTER(wt.DWORD)]
        self.u.GetWindowThreadProcessId.restype=wt.DWORD

    def dispatch(self,hwnd,message,wparam,lparam,identifier,data):
        if message==0x21:return 3  # WM_MOUSEACTIVATE / MA_NOACTIVATE: deliver the click.
        if message==0x82:  # WM_NCDESTROY
            self.api.RemoveWindowSubclass(hwnd,self.callback,1)
            self.handles.discard(hwnd)
        return self.api.DefSubclassProc(hwnd,message,wparam,lparam)

    def install(self,root):
        children=[]
        enumerate_type=ct.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
        def visit(hwnd,data):children.append(hwnd);return True
        self.u.EnumChildWindows.argtypes=[wt.HWND,enumerate_type,wt.LPARAM]
        self.u.EnumChildWindows.restype=wt.BOOL
        self.u.EnumChildWindows(root,enumerate_type(visit),0)
        added=[]
        try:
            for hwnd in (root,*children):
                if hwnd in self.handles:continue
                pid=wt.DWORD();self.u.GetWindowThreadProcessId(hwnd,ct.byref(pid))
                if pid.value!=os.getpid():raise ValueError('Somente janelas do próprio overlay podem ser protegidas')
                if not self.api.SetWindowSubclass(hwnd,self.callback,1,0):
                    raise OSError('Não foi possível impedir a ativação do controle do overlay')
                self.handles.add(hwnd);added.append(hwnd)
        except Exception:
            for hwnd in added:
                self.api.RemoveWindowSubclass(hwnd,self.callback,1);self.handles.discard(hwnd)
            raise

    def close(self):
        for hwnd in tuple(self.handles):
            self.api.RemoveWindowSubclass(hwnd,self.callback,1)
        self.handles.clear()
