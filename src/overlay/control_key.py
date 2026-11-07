"""Observe only Ctrl transitions via a Windows low-level keyboard message loop.

    Never suppresses keys, records typed text, or sends input to another process.
"""
from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import logging
import sys
import threading

logger=logging.getLogger(__name__)
CONTROL_KEYS={0x11,0xa2,0xa3}


class ControlKeyListener:
    def __init__(self):
        self._pressed=set()
        self._lock=threading.Lock()
        self._stop=threading.Event()
        self._thread=None
        self.error=""

    @property
    def is_down(self):
        with self._lock:
            return bool(self._pressed)

    def transition(self,key: int,down: bool):
        if key not in CONTROL_KEYS:
            return
        with self._lock:
            before=bool(self._pressed)
            if down: self._pressed.add(key)
            else: self._pressed.discard(key)
            after=bool(self._pressed)
        if before!=after:
            logger.info("Ctrl transition: %s", "down" if after else "up")

    def reset(self):
        with self._lock:
            self._pressed.clear()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread=threading.Thread(target=self._run_safe,name="ControlKeyListener",daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=1)
        self.reset()

    def _run_safe(self):
        try:
            self._run()
        except Exception as exc:
            self.error=f"Falha ao observar Ctrl: {exc}"
            logger.exception(self.error)

    def _run(self):
        if sys.platform!="win32":
            return
        u=ct.WinDLL("user32",use_last_error=True)
        kernel=ct.WinDLL("kernel32",use_last_error=True)
        class Keyboard(ct.Structure):
            _fields_=[("vkCode",wt.DWORD),("scanCode",wt.DWORD),("flags",wt.DWORD),
                      ("time",wt.DWORD),("dwExtraInfo",ct.c_size_t)]
        callback_type=ct.WINFUNCTYPE(ct.c_ssize_t,ct.c_int,wt.WPARAM,wt.LPARAM)
        u.SetWindowsHookExW.argtypes=[ct.c_int,callback_type,wt.HINSTANCE,wt.DWORD]
        u.SetWindowsHookExW.restype=wt.HANDLE
        u.CallNextHookEx.argtypes=[wt.HANDLE,ct.c_int,wt.WPARAM,wt.LPARAM]
        u.CallNextHookEx.restype=ct.c_ssize_t
        u.UnhookWindowsHookEx.argtypes=[wt.HANDLE]
        u.UnhookWindowsHookEx.restype=wt.BOOL
        u.PeekMessageW.argtypes=[ct.POINTER(wt.MSG),wt.HWND,wt.UINT,wt.UINT,wt.UINT]
        u.PeekMessageW.restype=wt.BOOL
        u.TranslateMessage.argtypes=[ct.POINTER(wt.MSG)]
        u.DispatchMessageW.argtypes=[ct.POINTER(wt.MSG)]
        u.DispatchMessageW.restype=ct.c_ssize_t
        kernel.GetModuleHandleW.argtypes=[wt.LPCWSTR]
        kernel.GetModuleHandleW.restype=wt.HMODULE
        def callback(code,message,data):
            try:
                if code>=0:
                    key=ct.cast(data,ct.POINTER(Keyboard)).contents.vkCode
                    if key in CONTROL_KEYS:
                        if message in (0x100,0x104): self.transition(key,True)
                        elif message in (0x101,0x105): self.transition(key,False)
            except Exception:
                logger.exception("Ctrl event failed")
            return u.CallNextHookEx(None,code,message,data)
        proc=callback_type(callback)
        handle=u.SetWindowsHookExW(13,proc,kernel.GetModuleHandleW(None),0)
        if not handle:
            self.error=f"Não foi possível observar Ctrl: {ct.get_last_error()}"
            logger.error(self.error)
            return
        logger.info("Ctrl observer installed")
        try:
            message=wt.MSG()
            while not self._stop.is_set():
                while u.PeekMessageW(ct.byref(message),None,0,0,1):
                    u.TranslateMessage(ct.byref(message))
                    u.DispatchMessageW(ct.byref(message))
                self._stop.wait(.005)
        finally:
            u.UnhookWindowsHookEx(handle)
            self.reset()
