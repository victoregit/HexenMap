"""Game window tracking module for Genshin Impact.

Monitors game window presence, position, resolution changes, and minimization state
via Win32 FindWindowW, GetClientRect, and ClientToScreen, keeping the overlay aligned.
"""

from __future__ import annotations
import ctypes
from dataclasses import dataclass
import logging
import platform
import threading
import time
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Known Genshin Impact window titles
DEFAULT_WINDOW_TITLES = [
    "Genshin Impact",
    "原神",
    "YuanShen",
]


@dataclass
class GameWindowRect:
    """Bounding client rectangle and status of the game window."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_minimized: bool = False
    is_found: bool = False
    hwnd: Optional[int] = None

    @property
    def aspect_ratio(self) -> float:
        return (self.width / self.height) if self.height > 0 else 0.0

    def has_moved_or_resized(self, other: GameWindowRect) -> bool:
        """Check if coordinates or dimensions changed meaningfully."""
        return (
            self.x != other.x
            or self.y != other.y
            or self.width != other.width
            or self.height != other.height
            or self.is_minimized != other.is_minimized
            or self.is_found != other.is_found
        )


def is_windows() -> bool:
    """Return True if executing on a genuine Windows OS."""
    return platform.system() == "Windows"


class GameWindowTracker:
    """Tracks position, dimension, and state of the Genshin Impact game window."""

    def __init__(
        self,
        window_titles: Optional[List[str]] = None,
        poll_interval_s: float = 0.5,
    ) -> None:
        self.window_titles = window_titles or list(DEFAULT_WINDOW_TITLES)
        self.poll_interval_s = poll_interval_s

        self._last_rect = GameWindowRect()
        self._mock_rect: Optional[GameWindowRect] = None

        self._on_moved_callbacks: List[Callable[[GameWindowRect], None]] = []
        self._on_found_callbacks: List[Callable[[int], None]] = []
        self._on_lost_callbacks: List[Callable[[], None]] = []

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def latest_rect(self) -> GameWindowRect:
        with self._lock:
            return self._last_rect

    def add_on_moved_callback(self, cb: Callable[[GameWindowRect], None]) -> None:
        self._on_moved_callbacks.append(cb)

    def add_on_found_callback(self, cb: Callable[[int], None]) -> None:
        self._on_found_callbacks.append(cb)

    def add_on_lost_callback(self, cb: Callable[[], None]) -> None:
        self._on_lost_callbacks.append(cb)

    def set_mock_rect(self, rect: Optional[GameWindowRect]) -> None:
        """Set mock window rect for tests and simulated environments."""
        with self._lock:
            self._mock_rect = rect

    def find_game_hwnd(self) -> Optional[int]:
        """Locate the native HWND for Genshin Impact by known titles."""
        if self._mock_rect is not None:
            return self._mock_rect.hwnd if self._mock_rect.is_found else None

        if not is_windows():
            return None

        try:
            user32 = ctypes.windll.user32
            for title in self.window_titles:
                hwnd = user32.FindWindowW(None, title)
                if hwnd and user32.IsWindow(hwnd):
                    return int(hwnd)
        except Exception as e:
            logger.debug("Error in find_game_hwnd: %s", e)
        return None

    def poll_once(self) -> GameWindowRect:
        """Poll current window status and dispatch callbacks if changes are detected."""
        current = self._query_window_rect()

        with self._lock:
            previous = self._last_rect
            self._last_rect = current

        # State transition: Found
        if not previous.is_found and current.is_found and current.hwnd:
            for cb in self._on_found_callbacks:
                try:
                    cb(current.hwnd)
                except Exception as e:
                    logger.error("Error in on_found callback: %s", e)

        # State transition: Lost
        elif previous.is_found and not current.is_found:
            for cb in self._on_lost_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.error("Error in on_lost callback: %s", e)

        # Dimension or position change
        if current.has_moved_or_resized(previous):
            for cb in self._on_moved_callbacks:
                try:
                    cb(current)
                except Exception as e:
                    logger.error("Error in on_moved callback: %s", e)

        return current

    def _query_window_rect(self) -> GameWindowRect:
        """Query real Win32 client coordinates or mock rect."""
        if self._mock_rect is not None:
            return self._mock_rect

        if not is_windows():
            return GameWindowRect()

        hwnd = self.find_game_hwnd()
        if not hwnd:
            return GameWindowRect()

        try:
            user32 = ctypes.windll.user32

            # Check if minimized
            is_minimized = bool(user32.IsIconic(ctypes.c_void_p(hwnd)))

            # Get client rect (w, h)
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            client_rect = RECT()
            if not user32.GetClientRect(ctypes.c_void_p(hwnd), ctypes.byref(client_rect)):
                return GameWindowRect(hwnd=hwnd, is_found=True, is_minimized=is_minimized)

            w = client_rect.right - client_rect.left
            h = client_rect.bottom - client_rect.top

            # Map client top-left (0, 0) to screen coordinates
            pt = POINT(0, 0)
            user32.ClientToScreen(ctypes.c_void_p(hwnd), ctypes.byref(pt))

            return GameWindowRect(
                x=int(pt.x),
                y=int(pt.y),
                width=int(w),
                height=int(h),
                is_minimized=is_minimized,
                is_found=True,
                hwnd=hwnd,
            )
        except Exception as e:
            logger.debug("Error querying game window rect: %s", e)
            return GameWindowRect(hwnd=hwnd, is_found=True)

    def start(self) -> None:
        """Start background polling thread."""
        with self._lock:
            if self._is_running:
                return
            self._stop_event.clear()
            self._is_running = True
            self._thread = threading.Thread(target=self._run_poll_loop, name="GameWindowTrackerThread", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop background polling thread."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as e:
                logger.error("Exception in window tracker loop: %s", e)
            self._stop_event.wait(self.poll_interval_s)
