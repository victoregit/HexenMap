"""Overlay manager coordinating window modes, transparency, and click-through."""

from __future__ import annotations
from enum import Enum
import logging
from typing import Callable, List, Optional

from src.overlay import win32_overlay

logger = logging.getLogger(__name__)


class OverlayMode(str, Enum):
    """Overlay display mode."""
    COMPACT = "compact"      # Small non-intrusive HUD in corner, click-through active
    EXPANDED = "expanded"    # Full-screen or large window for interactive map navigation
    HIDDEN = "hidden"        # Window minimized or hidden


class OverlayManager:
    """Manages overlay display mode, click-through toggles, and hotkey actions."""

    def __init__(
        self,
        hwnd: Optional[int] = None,
        initial_mode: OverlayMode = OverlayMode.EXPANDED,
        compact_alpha: float = 0.85,
        expanded_alpha: float = 0.95,
    ) -> None:
        self._hwnd = hwnd
        self._mode = initial_mode
        self._is_visible = initial_mode != OverlayMode.HIDDEN
        self._compact_alpha = compact_alpha
        self._expanded_alpha = expanded_alpha
        self._click_through_enabled = False

        self._mode_callbacks: List[Callable[[OverlayMode], None]] = []
        self._visibility_callbacks: List[Callable[[bool], None]] = []

        if hwnd is not None:
            self._apply_state()

    @property
    def hwnd(self) -> Optional[int]:
        return self._hwnd

    @property
    def mode(self) -> OverlayMode:
        return self._mode

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @property
    def is_click_through(self) -> bool:
        return self._click_through_enabled

    @property
    def current_alpha(self) -> float:
        if self._mode == OverlayMode.COMPACT:
            return self._compact_alpha
        return self._expanded_alpha

    def attach_window(self, hwnd: int) -> None:
        """Attach native window handle to overlay manager."""
        self._hwnd = hwnd
        self._apply_state()

    def set_mode(self, mode: OverlayMode) -> None:
        """Switch overlay mode and apply corresponding window styles."""
        if mode == OverlayMode.HIDDEN:
            self._mode = OverlayMode.HIDDEN
            self._is_visible = False
            self._notify_visibility(False)
            self._notify_mode(OverlayMode.HIDDEN)
            return

        self._mode = mode
        self._is_visible = True
        self._apply_state()
        self._notify_visibility(True)
        self._notify_mode(mode)

    def toggle_mode(self) -> OverlayMode:
        """Toggle between COMPACT and EXPANDED mode."""
        if self._mode == OverlayMode.COMPACT:
            new_mode = OverlayMode.EXPANDED
        else:
            new_mode = OverlayMode.COMPACT
        self.set_mode(new_mode)
        return new_mode

    def toggle_visibility(self) -> bool:
        """Toggle overlay between visible and hidden."""
        if self._is_visible:
            self.set_mode(OverlayMode.HIDDEN)
            return False
        else:
            self.set_mode(OverlayMode.EXPANDED)
            return True

    def cycle_mode(self) -> OverlayMode:
        """Cycle through COMPACT -> EXPANDED -> HIDDEN -> COMPACT."""
        if self._mode == OverlayMode.COMPACT:
            self.set_mode(OverlayMode.EXPANDED)
        elif self._mode == OverlayMode.EXPANDED:
            self.set_mode(OverlayMode.HIDDEN)
        else:
            self.set_mode(OverlayMode.COMPACT)
        return self._mode

    def set_transparency(self, alpha: float) -> None:
        """Manually override transparency for current mode."""
        if self._mode == OverlayMode.COMPACT:
            self._compact_alpha = max(0.1, min(1.0, alpha))
        else:
            self._expanded_alpha = max(0.1, min(1.0, alpha))
        if self._hwnd is not None:
            win32_overlay.set_window_transparency(self._hwnd, self.current_alpha)

    def _apply_state(self) -> None:
        """Enforce transparency, always-on-top, and click-through on window handle."""
        if self._hwnd is None:
            return

        # Always on top
        win32_overlay.set_always_on_top(self._hwnd, self._is_visible)

        # Transparency
        win32_overlay.set_window_transparency(self._hwnd, self.current_alpha)

        # In COMPACT mode, clicks pass through to game; in EXPANDED mode, clicks are captured by overlay
        want_click_through = (self._mode == OverlayMode.COMPACT)
        win32_overlay.set_click_through(self._hwnd, want_click_through)
        self._click_through_enabled = want_click_through

    def register_mode_callback(self, callback: Callable[[OverlayMode], None]) -> None:
        """Register callback invoked whenever mode transitions."""
        self._mode_callbacks.append(callback)

    def register_visibility_callback(self, callback: Callable[[bool], None]) -> None:
        """Register callback invoked whenever visibility changes."""
        self._visibility_callbacks.append(callback)

    def _notify_mode(self, mode: OverlayMode) -> None:
        for cb in self._mode_callbacks:
            try:
                cb(mode)
            except Exception as e:
                logger.error("Error in mode callback: %s", e)

    def _notify_visibility(self, visible: bool) -> None:
        for cb in self._visibility_callbacks:
            try:
                cb(visible)
            except Exception as e:
                logger.error("Error in visibility callback: %s", e)
