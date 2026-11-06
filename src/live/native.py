"""Typed, pointer-safe Win32 calls for the new runtime only."""
from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import sys
import os

import numpy as np

from src.overlay.window_tracker import GameWindowRect


class Windows:
    def __init__(self):
        if sys.platform != "win32":
            raise OSError("O overlay ao vivo requer Windows 10/11")
        self.u = ct.WinDLL("user32", use_last_error=True)
        self.g = ct.WinDLL("gdi32", use_last_error=True)
        signatures = {
            "FindWindowW": ([wt.LPCWSTR,wt.LPCWSTR],wt.HWND),
            "IsWindow": ([wt.HWND],wt.BOOL), "IsIconic": ([wt.HWND],wt.BOOL),
            "GetForegroundWindow": ([],wt.HWND),
            "SetForegroundWindow": ([wt.HWND],wt.BOOL),
            "GetWindowThreadProcessId": ([wt.HWND,ct.POINTER(wt.DWORD)],wt.DWORD),
            "GetAsyncKeyState": ([ct.c_int],ct.c_short),
            "GetCursorPos": ([ct.POINTER(wt.POINT)],wt.BOOL),
            "GetClientRect": ([wt.HWND,ct.POINTER(wt.RECT)],wt.BOOL),
            "ClientToScreen": ([wt.HWND,ct.POINTER(wt.POINT)],wt.BOOL),
            "GetDC": ([wt.HWND],wt.HDC), "ReleaseDC": ([wt.HWND,wt.HDC],ct.c_int),
            "GetAncestor": ([wt.HWND,wt.UINT],wt.HWND),
            "SetWindowPos": ([wt.HWND,wt.HWND,ct.c_int,ct.c_int,ct.c_int,ct.c_int,wt.UINT],wt.BOOL),
            "ShowWindow": ([wt.HWND,ct.c_int],wt.BOOL),
            "SetLayeredWindowAttributes": ([wt.HWND,wt.DWORD,wt.BYTE,wt.DWORD],wt.BOOL),
            "SetWindowDisplayAffinity": ([wt.HWND,wt.DWORD],wt.BOOL),
        }
        for name,(args,restype) in signatures.items():
            f=getattr(self.u,name); f.argtypes=args; f.restype=restype
        suffix = "PtrW" if ct.sizeof(ct.c_void_p)==8 else "W"
        self.get_style=getattr(self.u,"GetWindowLong"+suffix)
        self.set_style=getattr(self.u,"SetWindowLong"+suffix)
        self.get_style.argtypes=[wt.HWND,ct.c_int]; self.get_style.restype=ct.c_ssize_t
        self.set_style.argtypes=[wt.HWND,ct.c_int,ct.c_ssize_t]; self.set_style.restype=ct.c_ssize_t
        for name,args,result in [
            ("CreateCompatibleDC",[wt.HDC],wt.HDC),
            ("CreateCompatibleBitmap",[wt.HDC,ct.c_int,ct.c_int],wt.HBITMAP),
            ("SelectObject",[wt.HDC,wt.HANDLE],wt.HANDLE),
            ("DeleteObject",[wt.HANDLE],wt.BOOL), ("DeleteDC",[wt.HDC],wt.BOOL),
            ("BitBlt",[wt.HDC,ct.c_int,ct.c_int,ct.c_int,ct.c_int,wt.HDC,ct.c_int,ct.c_int,wt.DWORD],wt.BOOL),
            ("GetDIBits",[wt.HDC,wt.HBITMAP,wt.UINT,wt.UINT,ct.c_void_p,ct.c_void_p,wt.UINT],ct.c_int),
            ("CreateRectRgn",[ct.c_int,ct.c_int,ct.c_int,ct.c_int],wt.HANDLE),
            ("CombineRgn",[wt.HANDLE,wt.HANDLE,wt.HANDLE,ct.c_int],ct.c_int),
        ]:
            f=getattr(self.g,name); f.argtypes=args; f.restype=result
        self.u.SetWindowRgn.argtypes=[wt.HWND,wt.HANDLE,wt.BOOL]
        self.u.SetWindowRgn.restype=ct.c_int

    def enable_dpi(self):
        try:
            f=self.u.SetProcessDpiAwarenessContext
            f.argtypes=[ct.c_void_p]; f.restype=wt.BOOL
            f(ct.c_void_p(-4))
        except AttributeError:
            self.u.SetProcessDPIAware()

    def game(self) -> GameWindowRect:
        for title in ("Genshin Impact", "原神", "YuanShen"):
            hwnd=self.u.FindWindowW(None,title)
            if hwnd and self.u.IsWindow(hwnd):
                rect=wt.RECT(); point=wt.POINT(0,0)
                if not self.u.GetClientRect(hwnd,ct.byref(rect)) or not self.u.ClientToScreen(hwnd,ct.byref(point)):
                    continue
                return GameWindowRect(point.x,point.y,rect.right,rect.bottom,
                                      bool(self.u.IsIconic(hwnd)),True,hwnd)
        return GameWindowRect()

    def foreground(self, rect: GameWindowRect) -> bool:
        return bool(rect.hwnd and not rect.is_minimized and rect.width>0 and rect.height>0
                    and self.u.GetForegroundWindow()==rect.hwnd)

    def menu_foreground(self, rect: GameWindowRect) -> bool:
        hwnd=self.u.GetForegroundWindow()
        if hwnd==rect.hwnd:
            return True
        pid=wt.DWORD()
        self.u.GetWindowThreadProcessId(hwnd,ct.byref(pid))
        return pid.value==os.getpid()

    def restore_game_focus(self, rect: GameWindowRect) -> bool:
        # Only return from our UI; never pull focus back from another application.
        if not rect.hwnd or rect.is_minimized or not self.u.IsWindow(rect.hwnd):
            return False
        if not self.menu_foreground(rect):
            return False
        return bool(self.u.SetForegroundWindow(rect.hwnd))

    def key_down(self, key: int) -> bool:
        return bool(self.u.GetAsyncKeyState(key)&0x8000)

    def popup(self, child_hwnd: int, game: GameWindowRect) -> int:
        hwnd=self.overlay(child_hwnd)
        # The popup belongs to the game window, not the configuration panel.
        ct.set_last_error(0)
        self.set_style(hwnd,-8,game.hwnd)
        if ct.get_last_error():
            raise ct.WinError(ct.get_last_error())
        if not self.u.SetLayeredWindowAttributes(hwnd,0,255,2):
            raise ct.WinError(ct.get_last_error())
        self.interactive(hwnd,True)
        return hwnd

    def overlay(self, child_hwnd: int) -> int:
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        style=self.get_style(hwnd,-20)
        # Layered, transparent to input, tool window, never activates.
        ct.set_last_error(0)
        self.set_style(hwnd,-20,style | 0x80000 | 0x20 | 0x80 | 0x8000000)
        if ct.get_last_error():
            raise ct.WinError(ct.get_last_error())
        # Magenta color key; icons remain fully opaque, background fully clear.
        if not self.u.SetLayeredWindowAttributes(hwnd,0x00ff00ff,255,1):
            raise ct.WinError(ct.get_last_error())
        if not self.u.SetWindowDisplayAffinity(hwnd,0x11):
            raise OSError("Não foi possível excluir o overlay da captura")
        return hwnd

    def place(self, hwnd: int, rect: GameWindowRect) -> None:
        # SWP_NOACTIVATE | SWP_SHOWWINDOW. This never brings the game to foreground.
        if not self.u.SetWindowPos(hwnd,ct.c_void_p(-1),rect.x,rect.y,rect.width,rect.height,0x10|0x40):
            raise ct.WinError(ct.get_last_error())

    def input_overlay(self, child_hwnd: int) -> int:
        """Separate alpha surface: no color-key holes through clickable icons."""
        hwnd=self.overlay(child_hwnd)
        if not self.u.SetLayeredWindowAttributes(hwnd,0,2,2):
            raise ct.WinError(ct.get_last_error())
        return hwnd

    def input_region(self, hwnd: int, boxes: list[tuple[int,int,int,int]]) -> None:
        region=self.g.CreateRectRgn(0,0,0,0)
        if not region:
            raise ct.WinError(ct.get_last_error())
        try:
            for box in boxes:
                part=self.g.CreateRectRgn(*box)
                if not part:
                    raise ct.WinError(ct.get_last_error())
                try:
                    if not self.g.CombineRgn(region,region,part,2):
                        raise ct.WinError(ct.get_last_error())
                finally:
                    self.g.DeleteObject(part)
            if not self.u.SetWindowRgn(hwnd,region,True):
                raise ct.WinError(ct.get_last_error())
            region=None  # Windows owns the region after a successful assignment.
        finally:
            if region:
                self.g.DeleteObject(region)

    def hide(self, hwnd: int) -> None:
        self.u.ShowWindow(hwnd,0)

    def pointer(self) -> tuple[bool,int,int]:
        point=wt.POINT()
        if not self.u.GetCursorPos(ct.byref(point)):
            return False,0,0
        return bool(self.u.GetAsyncKeyState(0x11)&0x8000),point.x,point.y

    def interactive(self, hwnd: int, enabled: bool) -> None:
        style=self.get_style(hwnd,-20)
        updated=(style & ~0x20) if enabled else (style | 0x20)
        if updated!=style:
            ct.set_last_error(0)
            self.set_style(hwnd,-20,updated)
            if ct.get_last_error():
                raise ct.WinError(ct.get_last_error())

    def capture(self, rect: GameWindowRect) -> np.ndarray | None:
        if not self.foreground(rect):
            return None
        # Reuse only the bitmap header definition, never the untyped legacy calls.
        from src.capture.win32_capture import BITMAPINFO, BITMAPINFOHEADER
        dc=mem=bitmap=old=None
        try:
            dc=self.u.GetDC(None)
            if not dc: return None
            mem=self.g.CreateCompatibleDC(dc)
            if not mem: return None
            bitmap=self.g.CreateCompatibleBitmap(dc,rect.width,rect.height)
            if not bitmap: return None
            old=self.g.SelectObject(mem,bitmap)
            if not old: return None
            if not self.g.BitBlt(mem,0,0,rect.width,rect.height,dc,rect.x,rect.y,0x00cc0020):
                return None
            self.g.SelectObject(mem,old); old=None
            info=BITMAPINFO(); info.bmiHeader.biSize=ct.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth=rect.width; info.bmiHeader.biHeight=-rect.height
            info.bmiHeader.biPlanes=1; info.bmiHeader.biBitCount=32
            buffer=(ct.c_ubyte*(rect.width*rect.height*4))()
            if self.g.GetDIBits(dc,bitmap,0,rect.height,buffer,ct.byref(info),0)!=rect.height:
                return None
            return np.frombuffer(buffer,np.uint8).reshape(rect.height,rect.width,4)[:,:,:3].copy()
        finally:
            if old and mem: self.g.SelectObject(mem,old)
            if bitmap: self.g.DeleteObject(bitmap)
            if mem: self.g.DeleteDC(mem)
            if dc: self.u.ReleaseDC(None,dc)
