"""Overlay window management module."""

from src.overlay.capture_exclusion import is_capture_excluded, set_capture_exclusion
from src.overlay.global_hotkeys import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NONE,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    VK_ESCAPE,
    VK_F11,
    VK_F12,
    GlobalHotkeyListener,
)
from src.overlay.multi_surface_manager import ActiveSurfaceState, MultiSurfaceOverlayManager
from src.overlay.overlay_manager import OverlayManager, OverlayMode
from src.overlay.win32_overlay import (
    get_toplevel_hwnd,
    is_windows,
    set_always_on_top,
    set_click_through,
    set_window_transparency,
)
from src.overlay.window_tracker import GameWindowRect, GameWindowTracker

__all__ = [
    "ActiveSurfaceState",
    "GameWindowRect",
    "GameWindowTracker",
    "GlobalHotkeyListener",
    "MOD_ALT",
    "MOD_CONTROL",
    "MOD_NONE",
    "MOD_NOREPEAT",
    "MOD_SHIFT",
    "MOD_WIN",
    "MultiSurfaceOverlayManager",
    "OverlayManager",
    "OverlayMode",
    "VK_ESCAPE",
    "VK_F11",
    "VK_F12",
    "get_toplevel_hwnd",
    "is_capture_excluded",
    "is_windows",
    "set_always_on_top",
    "set_capture_exclusion",
    "set_click_through",
    "set_window_transparency",
]
