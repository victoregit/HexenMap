"""Typed, pointer-safe Win32 calls for the new runtime only."""
from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import sys
import os
import struct

import numpy as np

from src.overlay.window_tracker import GameWindowRect
from src.live.identity import WINDOW_TITLE,INSTANCE_MUTEX,LEGACY_INSTANCE_MUTEX,LEGACY_WINDOW_TITLES


class OverlayAlreadyRunning(RuntimeError):
    pass


class Windows:
    def __init__(self):
        if sys.platform != "win32":
            raise OSError("O overlay ao vivo requer Windows 10/11")
        self.u = ct.WinDLL("user32", use_last_error=True)
        self.g = ct.WinDLL("gdi32", use_last_error=True)
        self.k=ct.WinDLL('kernel32',use_last_error=True)
        self.k.CreateMutexW.argtypes=[ct.c_void_p,wt.BOOL,wt.LPCWSTR]
        self.k.CreateMutexW.restype=wt.HANDLE
        self.k.CloseHandle.argtypes=[wt.HANDLE];self.k.CloseHandle.restype=wt.BOOL
        self.instance_handle=None
        signatures = {
            "FindWindowW": ([wt.LPCWSTR,wt.LPCWSTR],wt.HWND),
            "IsWindow": ([wt.HWND],wt.BOOL), "IsIconic": ([wt.HWND],wt.BOOL),
            "GetForegroundWindow": ([],wt.HWND),
            "SetForegroundWindow": ([wt.HWND],wt.BOOL),
            "GetWindowThreadProcessId": ([wt.HWND,ct.POINTER(wt.DWORD)],wt.DWORD),
            "GetAsyncKeyState": ([ct.c_int],ct.c_short),
            "GetCursorPos": ([ct.POINTER(wt.POINT)],wt.BOOL),
            "GetClientRect": ([wt.HWND,ct.POINTER(wt.RECT)],wt.BOOL),
            "GetWindowRect": ([wt.HWND,ct.POINTER(wt.RECT)],wt.BOOL),
            "IsWindowVisible": ([wt.HWND],wt.BOOL),
            "GetWindow": ([wt.HWND,wt.UINT],wt.HWND),
            "GetWindowTextW": ([wt.HWND,wt.LPWSTR,ct.c_int],ct.c_int),
            "GetSystemMetrics": ([ct.c_int],ct.c_int),
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

    def existing_panel(self):
        found=[]
        callback_type=ct.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
        def visit(hwnd,param):
            text=ct.create_unicode_buffer(256);self.u.GetWindowTextW(hwnd,text,256)
            if text.value not in (WINDOW_TITLE,*LEGACY_WINDOW_TITLES):return True
            pid=wt.DWORD();self.u.GetWindowThreadProcessId(hwnd,ct.byref(pid))
            if pid.value==os.getpid():return True
            if self.get_style(hwnd,-20)&(0x80000|0x8000000):return True
            if self.u.GetWindow(hwnd,4):return True
            found.append(hwnd);return False
        enum=self.u.EnumWindows;enum.argtypes=[callback_type,wt.LPARAM];enum.restype=wt.BOOL
        enum(callback_type(visit),0)
        return found[0] if found else None

    def acquire_instance(self):
        handles=[];already=False
        for name in (INSTANCE_MUTEX,LEGACY_INSTANCE_MUTEX):
            handle=self.k.CreateMutexW(None,False,name)
            if not handle:
                error=ct.get_last_error()
                for owned in handles:self.k.CloseHandle(owned)
                raise ct.WinError(error)
            already=already or ct.get_last_error()==183
            handles.append(handle)
        panel=self.existing_panel()
        if already or panel:
            for handle in handles:self.k.CloseHandle(handle)
            if panel:
                self.u.ShowWindow(panel,9);self.u.SetForegroundWindow(panel)
            return False
        self.instance_handles=handles;self.instance_handle=handles[0]
        return True

    def release_instance(self):
        if self.instance_handle:
            for handle in getattr(self,'instance_handles',[self.instance_handle]):self.k.CloseHandle(handle)
            self.instance_handles=[];self.instance_handle=None

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

    def panel(self, child_hwnd: int) -> None:
        """Apply the user's capture preference to interactive controls too."""
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        self.capture_policy(hwnd)
        self._caption_theme(hwnd)

    def _caption_theme(self,hwnd):
        """App-window colors only; older Windows keeps its native frame."""
        try:
            from src.live.theme import BG,TEXT
            if not hasattr(self,'_dwm'):
                self._dwm=ct.WinDLL('dwmapi')
                self._dwm.DwmSetWindowAttribute.argtypes=[wt.HWND,wt.DWORD,ct.c_void_p,wt.DWORD]
                self._dwm.DwmSetWindowAttribute.restype=ct.c_long
            dark=wt.BOOL(True)
            self._dwm.DwmSetWindowAttribute(hwnd,20,ct.byref(dark),ct.sizeof(dark))
            for attribute,color in ((35,BG),(36,TEXT)):
                value=wt.DWORD(int(color[1:3],16)|(int(color[3:5],16)<<8)|(int(color[5:7],16)<<16))
                self._dwm.DwmSetWindowAttribute(hwnd,attribute,ct.byref(value),ct.sizeof(value))
        except (OSError,AttributeError):pass

    def capture_policy(self,hwnd):
        if not self.u.SetWindowDisplayAffinity(hwnd,0 if getattr(self,'capture_visible',False) else 0x11):
            raise OSError('Não foi possível configurar a visibilidade na captura')
        if not hasattr(self,'capture_windows'):self.capture_windows=set()
        self.capture_windows.add(hwnd)

    def set_capture_visible(self,visible):
        previous=getattr(self,'capture_visible',False);applied=[];valid=set()
        try:
            for hwnd in getattr(self,'capture_windows',set()):
                pid=wt.DWORD()
                if not self.u.IsWindow(hwnd):continue
                self.u.GetWindowThreadProcessId(hwnd,ct.byref(pid))
                if pid.value!=os.getpid():continue
                valid.add(hwnd)
                if not self.u.SetWindowDisplayAffinity(hwnd,0 if visible else 0x11):
                    raise OSError('O Windows não permitiu alterar a visibilidade na captura')
                applied.append(hwnd)
        except OSError:
            for hwnd in applied:self.u.SetWindowDisplayAffinity(hwnd,0 if previous else 0x11)
            raise
        self.capture_windows=valid;self.capture_visible=bool(visible)

    def desktop_bounds(self):
        x,y=self.u.GetSystemMetrics(76),self.u.GetSystemMetrics(77)
        return x,y,x+self.u.GetSystemMetrics(78),y+self.u.GetSystemMetrics(79)

    def work_area(self,x,y):
        """Usable monitor rectangle for panel placement, excluding the taskbar."""
        class MonitorInfo(ct.Structure):
            _fields_=[('size',wt.DWORD),('monitor',wt.RECT),('work',wt.RECT),('flags',wt.DWORD)]
        self.u.MonitorFromPoint.argtypes=[wt.POINT,wt.DWORD]
        self.u.MonitorFromPoint.restype=wt.HANDLE
        self.u.GetMonitorInfoW.argtypes=[wt.HANDLE,ct.POINTER(MonitorInfo)]
        self.u.GetMonitorInfoW.restype=wt.BOOL
        monitor=self.u.MonitorFromPoint(wt.POINT(round(x),round(y)),2)
        info=MonitorInfo();info.size=ct.sizeof(info)
        if monitor and self.u.GetMonitorInfoW(monitor,ct.byref(info)):
            r=info.work;return r.left,r.top,r.right,r.bottom
        return self.desktop_bounds()

    def move_panel(self, child_hwnd, x, y):
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        self.u.SetWindowPos(hwnd,None,x,y,0,0,0x01|0x04|0x10)

    def panel_mask(self,child_hwnd,bounds=None):
        """Clip our own live panel during collapse; None restores its full shape."""
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        if bounds is None:
            if not self.u.SetWindowRgn(hwnd,None,True):raise ct.WinError(ct.get_last_error())
            return
        region=self.g.CreateRectRgn(*map(round,bounds))
        if not region:raise ct.WinError(ct.get_last_error())
        try:
            if not self.u.SetWindowRgn(hwnd,region,True):raise ct.WinError(ct.get_last_error())
            region=None  # Ownership transfers to Windows after a successful call.
        finally:
            if region:self.g.DeleteObject(region)

    def transition_panel(self,child_hwnd):
        """The temporary visual never activates or adds a taskbar button."""
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        ct.set_last_error(0)
        self.set_style(hwnd,-20,self.get_style(hwnd,-20)|0x80|0x8000000)
        if ct.get_last_error():raise ct.WinError(ct.get_last_error())

    def control_bounds(self, child_hwnd, occluder=None):
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        if not self.u.IsWindowVisible(hwnd) or self.u.IsIconic(hwnd):return None
        # A normal detached window behind the game must not cut a hole in its map.
        if occluder:
            previous=self.u.GetWindow(hwnd,3)
            seen=set()
            while previous and previous not in seen:
                if previous==occluder:return None
                seen.add(previous);previous=self.u.GetWindow(previous,3)
        rect=wt.RECT()
        if not self.u.GetWindowRect(hwnd,ct.byref(rect)):return None
        return rect.left,rect.top,rect.right,rect.bottom

    def above_icons(self, child_hwnd):
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        if self.u.IsWindowVisible(hwnd) and not self.u.IsIconic(hwnd):
            # Reorder only. Never activate, move, resize or unminimize the panel.
            self.u.SetWindowPos(hwnd,ct.c_void_p(-1),0,0,0,0,0x01|0x02|0x10)

    def exclude_controls(self, hwnd, width, height, rectangles):
        """OS-level clipping supplements symbol filtering; coordinates are physical pixels."""
        region=self.g.CreateRectRgn(0,0,width,height)
        if not region:raise ct.WinError(ct.get_last_error())
        try:
            for left,top,right,bottom in rectangles:
                cut=self.g.CreateRectRgn(round(left),round(top),round(right),round(bottom))
                if not cut:raise ct.WinError(ct.get_last_error())
                try:
                    if not self.g.CombineRgn(region,region,cut,4):raise ct.WinError(ct.get_last_error())
                finally:self.g.DeleteObject(cut)
            if not self.u.SetWindowRgn(hwnd,region,True):raise ct.WinError(ct.get_last_error())
            region=None
        finally:
            if region:self.g.DeleteObject(region)

    def show_panel(self, child_hwnd: int) -> None:
        hwnd=self.u.GetAncestor(child_hwnd,2) or child_hwnd
        self.u.ShowWindow(hwnd,4)  # SW_SHOWNOACTIVATE: returning to the game must not focus us.

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
        # Minimize the independent panel without minimizing its marker surfaces.
        self.set_style(hwnd,-8,0)
        style=self.get_style(hwnd,-20)
        # Layered, transparent to input, tool window, never activates.
        ct.set_last_error(0)
        self.set_style(hwnd,-20,style | 0x80000 | 0x20 | 0x80 | 0x8000000)
        if ct.get_last_error():
            raise ct.WinError(ct.get_last_error())
        # Magenta color key; icons remain fully opaque, background fully clear.
        if not self.u.SetLayeredWindowAttributes(hwnd,0x00ff00ff,255,1):
            raise ct.WinError(ct.get_last_error())
        self.capture_policy(hwnd)
        return hwnd

    def place(self, hwnd: int, rect: GameWindowRect) -> None:
        key=(hwnd,rect.x,rect.y,rect.width,rect.height)
        if getattr(self,'_placed',None)==key and self.u.IsWindowVisible(hwnd):return
        self._placed=key
        # SWP_NOACTIVATE | SWP_SHOWWINDOW. This never brings the game to foreground.
        if not self.u.SetWindowPos(hwnd,ct.c_void_p(-1),rect.x,rect.y,rect.width,rect.height,0x10|0x40):
            raise ct.WinError(ct.get_last_error())

    def input_overlay(self, child_hwnd: int) -> int:
        """Separate alpha surface: no color-key holes through clickable icons."""
        hwnd=self.overlay(child_hwnd)
        if not self.u.SetLayeredWindowAttributes(hwnd,0,2,2):
            raise ct.WinError(ct.get_last_error())
        return hwnd

    def dpi_scale(self, hwnd: int) -> float:
        try:
            get=self.u.GetDpiForWindow
            get.argtypes=[wt.HWND];get.restype=wt.UINT
            return (get(hwnd) or 96)/96
        except AttributeError:return 1.

    def input_region(self, hwnd: int, boxes: list[tuple[int,int,int,int]]) -> None:
        from src.live.input_regions import region_data
        self.input_region_data(hwnd,region_data(boxes))

    def input_region_data(self,hwnd,raw):
        if raw:
            buffer=ct.create_string_buffer(raw)
            create=self.g.ExtCreateRegion
            create.argtypes=[ct.c_void_p,wt.DWORD,ct.c_void_p];create.restype=wt.HANDLE
            region=create(None,len(raw),buffer)
        else:region=self.g.CreateRectRgn(0,0,0,0)
        if not region:
            raise ct.WinError(ct.get_last_error())
        try:
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

    def close_capture(self):
        for slot in getattr(self,'_capture_slots',{}).values():
            self.g.SelectObject(slot['mem'],slot['old'])
            self.g.DeleteObject(slot['bitmap']);self.g.DeleteDC(slot['mem'])
        self._capture_slots={}

    def capture(self, rect: GameWindowRect, fraction=1., region=None) -> np.ndarray | None:
        """Retry a blank desktop capture against the game's client DC."""
        if not self.foreground(rect):return None
        key=(rect.hwnd,rect.width,rect.height,getattr(self,'capture_visible',False))
        if getattr(self,'_capture_backend_key',None)!=key:
            self._capture_backend_key=key;self._capture_client_fallback=False;self._prefer_graphics=False
        height=int(region[3]) if region is not None else max(1,min(rect.height,round(rect.height*fraction)))
        if self._prefer_graphics:
            frame=self._capture_graphics(rect,fraction,region)
            if not self._blank_capture(frame,height):
                self.capture_backend='Windows Graphics Capture';self.capture_error=''
                return frame
        client=region is not None or getattr(self,'capture_visible',False) or self._capture_client_fallback
        source=rect.hwnd if client else None
        frame=self._capture_frame(rect,fraction,region,source)
        if not self._blank_capture(frame,height):
            self.capture_backend='janela' if client else 'tela'
            self.capture_error=''
            return frame
        if source is None:
            frame=self._capture_frame(rect,fraction,region,rect.hwnd)
            if not self._blank_capture(frame,height):
                self._capture_client_fallback=True
                self.capture_backend='janela (recuperação automática)';self.capture_error=''
                return frame
        frame=self._capture_graphics(rect,fraction,region)
        if not self._blank_capture(frame,height):
            self._prefer_graphics=True
            self.capture_backend='Windows Graphics Capture';self.capture_error=''
            return frame
        self.capture_backend='GDI e Windows Graphics Capture'
        self.capture_error='Captura do jogo indisponível ou inteiramente branca/preta. '+getattr(self,'graphics_error','')
        return None

    def _capture_graphics(self,rect,fraction,region):
        key=(rect.hwnd,rect.width,rect.height)
        try:
            if getattr(self,'_graphics_key',None)!=key:
                self.close_graphics_capture();self._graphics_key=key
                from src.live.graphics_capture import WindowGraphicsCapture
                self._graphics=WindowGraphicsCapture(rect.hwnd)
            if getattr(self,'_graphics',None) is None:return None
            bounds=wt.RECT()
            dwm=ct.WinDLL('dwmapi')
            function=dwm.DwmGetWindowAttribute
            function.argtypes=[wt.HWND,wt.DWORD,ct.c_void_p,wt.DWORD];function.restype=ct.c_long
            if function(rect.hwnd,9,ct.byref(bounds),ct.sizeof(bounds))!=0:
                if not self.u.GetWindowRect(rect.hwnd,ct.byref(bounds)):return None
            frame=self._graphics.read(rect,(bounds.left,bounds.top,bounds.right,bounds.bottom),fraction,region)
            self.graphics_error=self._graphics.error or ('Aguardando imagem gráfica recente com dimensões válidas.' if frame is None else '')
            return frame
        except Exception as exc:
            self.graphics_error=f'Captura gráfica: {type(exc).__name__}: {exc}'
            return None

    def close_graphics_capture(self):
        graphics=getattr(self,'_graphics',None);self._graphics=None;self._graphics_key=None
        if graphics is not None:graphics.close()

    @staticmethod
    def _blank_capture(frame,height):
        if frame is None:return True
        sample=frame[:height:8,::8]
        if not sample.size:return True
        return bool(sample.max()<5 or sample.min()>250)

    def _capture_frame(self, rect, fraction, region, source):
        """Reusable output; synchronous consumer must copy before handing it to a future."""
        if not self.foreground(rect):return None
        from src.capture.win32_capture import BITMAPINFO, BITMAPINFOHEADER
        sx,sy=(0,0) if source else (rect.x,rect.y)
        width=rect.width;height=max(1,min(rect.height,round(rect.height*fraction)))
        output_height=rect.height
        if region is not None:
            rx,ry,width,height=map(int,region)
            if min(rx,ry)<0 or min(width,height)<1 or rx+width>rect.width or ry+height>rect.height:return None
            sx,sy=rx,ry;output_height=height
        key=(width,height,rect.height,source,output_height)
        if not hasattr(self,'_capture_slots'):self._capture_slots={}
        dc=self.u.GetDC(source)
        if not dc:return None
        try:
            slot=self._capture_slots.get(key)
            if slot is None:
                if len(self._capture_slots)>=(4 if region is not None else 2):self.close_capture()
                mem=self.g.CreateCompatibleDC(dc)
                if not mem:return None
                bitmap=self.g.CreateCompatibleBitmap(dc,width,height)
                if not bitmap:self.g.DeleteDC(mem);return None
                old=self.g.SelectObject(mem,bitmap)
                if not old:self.g.DeleteObject(bitmap);self.g.DeleteDC(mem);return None
                info=BITMAPINFO();info.bmiHeader.biSize=ct.sizeof(BITMAPINFOHEADER)
                info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=-height
                info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32
                slot=dict(mem=mem,bitmap=bitmap,old=old,info=info,buffer=(ct.c_ubyte*(width*height*4))(),
                            output=np.zeros((output_height,width,3),np.uint8))
                self._capture_slots[key]=slot
            if not self.g.BitBlt(slot['mem'],0,0,width,height,dc,sx,sy,0x00cc0020):return None
            self.g.SelectObject(slot['mem'],slot['old'])
            try:
                if self.g.GetDIBits(dc,slot['bitmap'],0,height,slot['buffer'],ct.byref(slot['info']),0)!=height:return None
            finally:self.g.SelectObject(slot['mem'],slot['bitmap'])
            slot['output'][:height]=np.frombuffer(slot['buffer'],np.uint8).reshape(height,width,4)[:,:,:3]
            return slot['output']
        finally:self.u.ReleaseDC(source,dc)
