"""Windows Win32 GDI / BitBlt screen capture and cross-platform mock capture engine."""

from __future__ import annotations
import ctypes
from ctypes import wintypes
import logging
import platform
import sys
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from src.capture.base import ScreenCaptureInterface

logger = logging.getLogger(__name__)


# Win32 GDI Structs and Constants
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class Win32ScreenCapture(ScreenCaptureInterface):
    """High-performance Windows GDI / BitBlt screen capture engine for Genshin Impact."""

    KNOWN_WINDOW_TITLES = ["Genshin Impact", "原神"]

    def __init__(self, target_window_title: Optional[str] = None) -> None:
        self.target_window_title = target_window_title
        self._cached_hwnd: Optional[int] = None

    def is_game_running(self) -> bool:
        """Return True if a game window is detected on the desktop."""
        return self.find_game_window() is not None

    def find_game_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Find the game window and return client rect (x, y, width, height) in screen space."""
        if platform.system() != "Windows":
            return None

        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]

            hwnd = None
            if self.target_window_title:
                hwnd = user32.FindWindowW(None, self.target_window_title)

            if not hwnd:
                for title in self.KNOWN_WINDOW_TITLES:
                    h = user32.FindWindowW(None, title)
                    if h:
                        hwnd = h
                        break

            if not hwnd:
                self._cached_hwnd = None
                return None

            self._cached_hwnd = hwnd

            # Get client area dimensions
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top

            if width <= 0 or height <= 0:
                return None

            # Map client top-left (0, 0) to screen coordinates
            point = wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(point))

            return point.x, point.y, width, height
        except Exception as e:
            logger.debug("Win32 window search error: %s", e)
            return None

    def capture_frame(self, rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Capture screen frame using Win32 BitBlt. Returns BGR numpy array."""
        if platform.system() != "Windows":
            return None

        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            gdi32 = ctypes.windll.gdi32    # type: ignore[attr-defined]

            if rect is None:
                win_rect = self.find_game_window()
                if not win_rect:
                    return None
                x, y, width, height = win_rect
            else:
                x, y, width, height = rect

            if width <= 0 or height <= 0:
                return None

            hdesk_dc = user32.GetDC(0)
            hmem_dc = gdi32.CreateCompatibleDC(hdesk_dc)
            hbmp = gdi32.CreateCompatibleBitmap(hdesk_dc, width, height)
            h_old_bmp = gdi32.SelectObject(hmem_dc, hbmp)

            # Fast hardware blit from desktop DC
            gdi32.BitBlt(hmem_dc, 0, 0, width, height, hdesk_dc, x, y, SRCCOPY)

            # Setup bitmap header
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # Negative for top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32     # BGRA
            bmi.bmiHeader.biCompression = BI_RGB

            buffer_size = width * height * 4
            if not hasattr(self, "_buffer") or getattr(self, "_buffer_size", 0) != buffer_size:
                self._buffer_size = buffer_size
                self._buffer = (ctypes.c_ubyte * buffer_size)()
            buffer = self._buffer

            gdi32.GetDIBits(
                hmem_dc,
                hbmp,
                0,
                height,
                ctypes.byref(buffer),
                ctypes.byref(bmi),
                DIB_RGB_COLORS,
            )

            # Clean up Win32 GDI handles
            gdi32.SelectObject(hmem_dc, h_old_bmp)
            gdi32.DeleteObject(hbmp)
            gdi32.DeleteDC(hmem_dc)
            user32.ReleaseDC(0, hdesk_dc)

            # Convert to numpy array and strip alpha channel (BGRA -> BGR)
            img = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
            return img[:, :, :3].copy()

        except Exception as e:
            logger.debug("Win32 capture error: %s", e)
            return None

    def capture_minimap(self, client_rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Directly capture the minimap sub-region for optimal frame latency."""
        if client_rect is None:
            client_rect = self.find_game_window()

        if not client_rect:
            return None

        win_x, win_y, win_w, win_h = client_rect
        cx, cy, cw, ch = self.calculate_minimap_crop_rect(win_w, win_h)

        # Directly capture the minimap sub-rect rather than full 1080p frame
        return self.capture_frame((win_x + cx, win_y + cy, cw, ch))


class MockScreenCapture(ScreenCaptureInterface):
    """Deterministic synthetic screen capture engine for testing and non-Windows environments."""

    def __init__(
        self,
        window_rect: Tuple[int, int, int, int] = (0, 0, 1920, 1080),
        game_running: bool = True,
    ) -> None:
        self._window_rect = window_rect
        self._is_game_running = game_running
        self._custom_minimap: Optional[np.ndarray] = None
        self._custom_frame: Optional[np.ndarray] = None

    def set_game_running(self, running: bool) -> None:
        self._is_game_running = running

    def set_window_rect(self, rect: Tuple[int, int, int, int]) -> None:
        self._window_rect = rect

    def set_custom_minimap(self, frame: Optional[np.ndarray]) -> None:
        self._custom_minimap = frame

    def set_custom_frame(self, frame: Optional[np.ndarray]) -> None:
        self._custom_frame = frame

    def is_game_running(self) -> bool:
        return self._is_game_running

    def find_game_window(self) -> Optional[Tuple[int, int, int, int]]:
        return self._window_rect if self._is_game_running else None

    def capture_frame(self, rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        if not self._is_game_running:
            return None

        if self._custom_frame is not None:
            return self._custom_frame.copy()

        # Generate a default synthetic full HD frame
        _, _, w, h = rect or self._window_rect
        frame = np.full((h, w, 3), 40, dtype=np.uint8)

        # Draw a synthetic minimap in top-left
        cx, cy, cw, ch = self.calculate_minimap_crop_rect(w, h)
        minimap = self._generate_synthetic_minimap(cw, ch)
        frame[cy : cy + ch, cx : cx + cw] = minimap

        return frame

    def capture_minimap(self, client_rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        if not self._is_game_running:
            return None

        if self._custom_minimap is not None:
            return self._custom_minimap.copy()

        _, _, w, h = client_rect or self._window_rect
        _, _, cw, ch = self.calculate_minimap_crop_rect(w, h)
        return self._generate_synthetic_minimap(cw, ch)

    @staticmethod
    def _generate_synthetic_minimap(
        width: int,
        height: int,
        player_heading_deg: float = 0.0,
        is_underground: bool = False,
    ) -> np.ndarray:
        """Generate a realistic synthetic minimap crop with circular border and player arrow."""
        # Base terrain color
        if is_underground:
            # Dark slate / cavern palette
            minimap = np.full((height, width, 3), (45, 45, 50), dtype=np.uint8)
        else:
            # Overworld grass/water/stone palette
            minimap = np.full((height, width, 3), (70, 130, 90), dtype=np.uint8)
            # Add some simulated water / paths
            minimap[int(height * 0.3) : int(height * 0.6), :] = (180, 120, 40)  # blue/teal stream

        if cv2 is not None:
            # Draw circular minimap border
            center = (width // 2, height // 2)
            radius = min(width, height) // 2 - 4
            cv2.circle(minimap, center, radius, (200, 200, 200), 2)

            # Draw directional player arrow at center
            # In Genshin, the player arrow is a high-contrast cyan/yellow triangle
            rad = np.radians(player_heading_deg)
            arrow_len = radius * 0.35
            tip_x = int(center[0] + arrow_len * np.sin(rad))
            tip_y = int(center[1] - arrow_len * np.cos(rad))

            base_rad_left = rad + np.radians(140)
            base_rad_right = rad - np.radians(140)
            base_len = arrow_len * 0.6
            b1_x = int(center[0] + base_len * np.sin(base_rad_left))
            b1_y = int(center[1] - base_len * np.cos(base_rad_left))
            b2_x = int(center[0] + base_len * np.sin(base_rad_right))
            b2_y = int(center[1] - base_len * np.cos(base_rad_right))

            triangle = np.array([[tip_x, tip_y], [b1_x, b1_y], [center[0], center[1]], [b2_x, b2_y]], dtype=np.int32)
            # Draw high-visibility cyan arrow (BGR: 255, 230, 0)
            cv2.fillPoly(minimap, [triangle], (255, 230, 0))
            cv2.polylines(minimap, [triangle], True, (0, 0, 0), 1)

        return minimap


def get_screen_capture(prefer_mock: bool = False, target_title: Optional[str] = None) -> ScreenCaptureInterface:
    """Factory creating appropriate screen capture backend for the current platform."""
    if not prefer_mock and platform.system() == "Windows":
        return Win32ScreenCapture(target_window_title=target_title)
    return MockScreenCapture()
