"""Win32 API bridge for window transparency, always-on-top, and click-through.

Provides native Windows ctypes implementation and a transparent mock/fallback
for Linux, macOS, and automated CI test environments.
"""

from __future__ import annotations
import ctypes
import logging
import platform
import sys
from typing import Dict

logger = logging.getLogger(__name__)

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class MockWin32State:
    """Tracks simulated window properties when running on non-Windows platforms."""
    def __init__(self) -> None:
        self.windows: Dict[int, Dict[str, bool | float | int]] = {}

    def get_or_create(self, hwnd: int) -> Dict[str, bool | float | int]:
        if hwnd not in self.windows:
            self.windows[hwnd] = {
                "click_through": False,
                "alpha": 1.0,
                "always_on_top": False,
                "ex_style": 0,
            }
        return self.windows[hwnd]


_mock_state = MockWin32State()


def is_windows() -> bool:
    """Return True if executing on a genuine Windows OS."""
    return platform.system() == "Windows"


def get_toplevel_hwnd(hwnd: int) -> int:
    """Resolve the true top-level window handle for a given window or child handle on Windows.

    In Tkinter on Windows, winfo_id() can sometimes yield a child container HWND rather than
    the top-level window frame. This function traverses up the parent hierarchy using GetParent
    to guarantee that extended styles like WS_EX_TRANSPARENT and WS_EX_LAYERED apply to the
    entire window frame.
    """
    if not is_windows():
        return hwnd
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        parent = user32.GetParent(hwnd)
        while parent:
            hwnd = parent
            parent = user32.GetParent(hwnd)
        return hwnd
    except Exception as e:
        logger.debug("Failed traversing window parent hierarchy: %s", e)
        return hwnd


def get_mock_state() -> MockWin32State:
    """Retrieve internal state tracker (used by unit tests to verify behavior)."""
    return _mock_state


def set_click_through(hwnd: int, enabled: bool) -> bool:
    """Enable or disable mouse click-through for the specified window handle.

    When enabled, mouse clicks pass directly through the window to whatever is beneath
    (e.g., the Genshin Impact game client).
    """
    if not is_windows():
        state = _mock_state.get_or_create(hwnd)
        state["click_through"] = enabled
        logger.debug("[MockWin32] set_click_through(hwnd=%s, enabled=%s)", hwnd, enabled)
        return True

    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # Use SetWindowLongPtrW on 64-bit architectures, SetWindowLongW on 32-bit
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            get_window_long = user32.GetWindowLongPtrW
            set_window_long = user32.SetWindowLongPtrW
        else:
            get_window_long = user32.GetWindowLongW
            set_window_long = user32.SetWindowLongW

        current_style = get_window_long(hwnd, GWL_EXSTYLE)
        if enabled:
            new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            new_style = (current_style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT

        set_window_long(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception as e:
        logger.error("Failed to set click-through for hwnd=%s: %s", hwnd, e)
        return False


def set_window_transparency(hwnd: int, alpha: float) -> bool:
    """Set opacity level for window handle (alpha between 0.0 transparent and 1.0 opaque)."""
    alpha = max(0.0, min(1.0, float(alpha)))

    if not is_windows():
        state = _mock_state.get_or_create(hwnd)
        state["alpha"] = alpha
        logger.debug("[MockWin32] set_window_transparency(hwnd=%s, alpha=%.2f)", hwnd, alpha)
        return True

    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            get_window_long = user32.GetWindowLongPtrW
            set_window_long = user32.SetWindowLongPtrW
        else:
            get_window_long = user32.GetWindowLongW
            set_window_long = user32.SetWindowLongW

        current_style = get_window_long(hwnd, GWL_EXSTYLE)
        set_window_long(hwnd, GWL_EXSTYLE, current_style | WS_EX_LAYERED)

        byte_alpha = int(round(alpha * 255))
        success = user32.SetLayeredWindowAttributes(hwnd, 0, byte_alpha, LWA_ALPHA)
        return bool(success)
    except Exception as e:
        logger.error("Failed to set window transparency for hwnd=%s: %s", hwnd, e)
        return False


def set_always_on_top(hwnd: int, enabled: bool) -> bool:
    """Keep window pinned above other windows."""
    if not is_windows():
        state = _mock_state.get_or_create(hwnd)
        state["always_on_top"] = enabled
        logger.debug("[MockWin32] set_always_on_top(hwnd=%s, enabled=%s)", hwnd, enabled)
        return True

    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        insert_after = HWND_TOPMOST if enabled else HWND_NOTOPMOST
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        success = user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
        return bool(success)
    except Exception as e:
        logger.error("Failed to set always-on-top for hwnd=%s: %s", hwnd, e)
        return False
