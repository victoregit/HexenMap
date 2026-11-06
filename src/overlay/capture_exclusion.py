"""Capture exclusion management using Windows DWM SetWindowDisplayAffinity.

Prevents the overlay window and markers from appearing in desktop screenshots,
DirectX frame captures, Discord/OBS streams, or OpenCV capture loops
(WDA_EXCLUDEFROMCAPTURE = 0x00000011).
"""

from __future__ import annotations
import ctypes
import logging
import platform
import sys
from typing import Dict

logger = logging.getLogger(__name__)

# Windows Display Affinity Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 2004 (Build 19041) and newer

# State tracking for mock and runtime inspection
_exclusion_state: Dict[int, bool] = {}


def is_windows() -> bool:
    """Return True if executing on a genuine Windows OS."""
    return platform.system() == "Windows"


def get_windows_build() -> int:
    """Return Windows build number or 0 if not on Windows."""
    if not is_windows():
        return 0
    try:
        ver_str = platform.version()
        # Format usually '10.0.19045' or similar
        parts = ver_str.split(".")
        if len(parts) >= 3:
            return int(parts[2])
        return int(parts[-1])
    except Exception:
        return 0


def set_capture_exclusion(hwnd: int, exclude: bool = True) -> bool:
    """Set or remove window capture exclusion from screen recorders / BitBlt capture.

    When excluded (WDA_EXCLUDEFROMCAPTURE), the window remains visible to the player
    on the physical display via DWM, but is completely invisible to screen capture
    APIs (including BitBlt, Windows Graphics Capture, and OBS).

    Args:
        hwnd: Integer window handle (HWND).
        exclude: True to exclude from capture, False to restore normal capture.

    Returns:
        bool: True if setting was applied successfully (or mocked in CI), False otherwise.
    """
    if not hwnd or hwnd <= 0:
        logger.debug("set_capture_exclusion called with invalid HWND: %s", hwnd)
        return False

    if not is_windows():
        _exclusion_state[hwnd] = exclude
        logger.debug("Mock capture exclusion for HWND %s set to %s", hwnd, exclude)
        return True

    try:
        user32 = ctypes.windll.user32
        # Set function signatures
        user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        user32.SetWindowDisplayAffinity.restype = ctypes.c_int

        affinity = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
        build = get_windows_build()

        # If on older Windows 10 (< build 19041), WDA_EXCLUDEFROMCAPTURE is not supported;
        # fallback to WDA_MONITOR which blanks window in capture.
        if exclude and 0 < build < 19041:
            logger.info("Windows build %d < 19041; falling back to WDA_MONITOR", build)
            affinity = WDA_MONITOR

        result = user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), ctypes.c_uint32(affinity))
        if result != 0:
            _exclusion_state[hwnd] = exclude
            logger.info("Successfully set capture affinity 0x%08X on HWND %s", affinity, hwnd)
            return True

        err = ctypes.GetLastError()
        logger.warning("SetWindowDisplayAffinity failed on HWND %s (error code: %d)", hwnd, err)
        return False
    except Exception as e:
        logger.error("Exception in SetWindowDisplayAffinity on HWND %s: %s", hwnd, e)
        return False


def is_capture_excluded(hwnd: int) -> bool:
    """Check if the given window handle is currently recorded as excluded."""
    return _exclusion_state.get(hwnd, False)
