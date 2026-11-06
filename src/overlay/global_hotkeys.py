"""Global Windows hotkey listener using RegisterHotKey and dedicated daemon message loop.

Captures system-wide hotkeys (e.g., F11, F12) even when Genshin Impact has exclusive OS input focus,
without injecting any input or modifying game memory.
"""

from __future__ import annotations
import ctypes
import logging
import platform
import threading
import time
from typing import Callable, Dict, NamedTuple, Optional

logger = logging.getLogger(__name__)

# Virtual Key Codes
VK_ESCAPE = 0x1B
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

# Modifier Flags
MOD_NONE = 0x0000
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Windows Messages
WM_QUIT = 0x0012
WM_HOTKEY = 0x0312


class HotkeyBinding(NamedTuple):
    hotkey_id: int
    vk_code: int
    modifiers: int
    callback: Callable[[], None]


def is_windows() -> bool:
    """Return True if executing on a genuine Windows OS."""
    return platform.system() == "Windows"


class GlobalHotkeyListener:
    """Listens for global keyboard shortcuts across Windows without game interference."""

    def __init__(self) -> None:
        self._bindings: Dict[int, HotkeyBinding] = {}
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._lock = threading.Lock()
        self.registration_errors: list[int] = []

    @property
    def is_running(self) -> bool:
        return self._is_running

    def register_hotkey(
        self,
        hotkey_id: int,
        vk_code: int,
        modifiers: int = MOD_NOREPEAT,
        callback: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Register a hotkey binding.

        Args:
            hotkey_id: Unique integer identifier for this hotkey.
            vk_code: Virtual-key code (e.g., VK_F11).
            modifiers: Combination of MOD_* flags (MOD_NOREPEAT recommended).
            callback: Function to invoke when hotkey is triggered.
        """
        with self._lock:
            binding = HotkeyBinding(
                hotkey_id=hotkey_id,
                vk_code=vk_code,
                modifiers=modifiers,
                callback=callback or (lambda: None),
            )
            self._bindings[hotkey_id] = binding

            # If listener thread is already active on Windows, register dynamically
            if self._is_running and is_windows() and self._thread_id:
                try:
                    user32 = ctypes.windll.user32
                    user32.RegisterHotKey(None, hotkey_id, modifiers, vk_code)
                except Exception as e:
                    logger.debug("Dynamic hotkey registration error: %s", e)

            return True

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        """Unregister a previously registered hotkey."""
        with self._lock:
            if hotkey_id in self._bindings:
                if self._is_running and is_windows():
                    try:
                        ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
                    except Exception as e:
                        logger.debug("Dynamic hotkey unregistration error: %s", e)
                del self._bindings[hotkey_id]
                return True
            return False

    def is_registered(self, hotkey_id: int) -> bool:
        """Return True if hotkey_id is currently registered."""
        with self._lock:
            return hotkey_id in self._bindings

    def trigger_hotkey(self, hotkey_id: int) -> bool:
        """Manually trigger hotkey callback (useful for testing or programmatic simulation)."""
        binding = None
        with self._lock:
            binding = self._bindings.get(hotkey_id)
        if binding and binding.callback:
            try:
                binding.callback()
                return True
            except Exception as e:
                logger.error("Error executing callback for hotkey %d: %s", hotkey_id, e)
        return False

    def start(self) -> None:
        """Start the global hotkey listener background thread."""
        with self._lock:
            if self._is_running:
                return
            self._stop_event.clear()
            self._is_running = True

            self._thread = threading.Thread(target=self._run_loop, name="GlobalHotkeyThread", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop listener thread and clean up registered hotkeys."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_event.set()

            if is_windows() and self._thread_id:
                try:
                    ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
                except Exception as e:
                    logger.debug("PostThreadMessageW error: %s", e)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_loop(self) -> None:
        """Background message pump loop."""
        if not is_windows():
            # In Linux/CI mock environment, sleep until stopped
            while not self._stop_event.is_set():
                time.sleep(0.05)
            return

        try:
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            self._thread_id = kernel32.GetCurrentThreadId()

            # Set argtypes/restypes
            user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
            user32.RegisterHotKey.restype = ctypes.c_int
            user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.UnregisterHotKey.restype = ctypes.c_int

            # Register all current bindings on this thread
            with self._lock:
                for b in self._bindings.values():
                    res = user32.RegisterHotKey(None, b.hotkey_id, b.modifiers, b.vk_code)
                    if not res:
                        self.registration_errors.append(b.hotkey_id)
                        logger.warning("Failed to register hotkey id %d (VK 0x%02X)", b.hotkey_id, b.vk_code)
                    else:
                        logger.debug("Registered global hotkey id %d (VK 0x%02X)", b.hotkey_id, b.vk_code)

            # Native MSG struct
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.c_void_p),
                    ("message", ctypes.c_uint),
                    ("wParam", ctypes.c_size_t),
                    ("lParam", ctypes.c_size_t),
                    ("time", ctypes.c_uint32),
                    ("pt", POINT),
                ]

            msg = MSG()
            # Message loop: PeekMessage with 10ms wait or GetMessage
            while not self._stop_event.is_set():
                # PeekMessage allows checking _stop_event periodically
                has_msg = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)  # PM_REMOVE = 1
                if has_msg:
                    if msg.message == WM_QUIT:
                        break
                    elif msg.message == WM_HOTKEY:
                        hotkey_id = int(msg.wParam)
                        self._dispatch_async(hotkey_id)
                    else:
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.01)

            # Clean up hotkeys on thread exit
            with self._lock:
                for b in self._bindings.values():
                    user32.UnregisterHotKey(None, b.hotkey_id)
        except Exception as e:
            logger.error("Exception in GlobalHotkeyListener loop: %s", e)
        finally:
            self._thread_id = None
            self._is_running = False

    def _dispatch_async(self, hotkey_id: int) -> None:
        """Dispatch callback in a dedicated thread to never block the OS message pump."""
        binding = None
        with self._lock:
            binding = self._bindings.get(hotkey_id)
        if binding and binding.callback:
            t = threading.Thread(
                target=self._safe_invoke,
                args=(binding.callback, hotkey_id),
                name=f"HotkeyDispatch-{hotkey_id}",
                daemon=True,
            )
            t.start()

    def _safe_invoke(self, callback: Callable[[], None], hotkey_id: int) -> None:
        try:
            callback()
        except Exception as e:
            logger.error("Error executing callback for global hotkey %d: %s", hotkey_id, e)
