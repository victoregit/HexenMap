"""Abstract base classes and contracts for screen capture."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class ScreenCaptureInterface(ABC):
    """Abstract interface for game window detection and frame capture."""

    @abstractmethod
    def is_game_running(self) -> bool:
        """Check if the game window or process is currently active."""
        pass

    @abstractmethod
    def find_game_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Locate game window rect. Returns (x, y, width, height) or None."""
        pass

    @abstractmethod
    def capture_frame(self, rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Capture screen frame in BGR format for specified rect (or full window if None)."""
        pass

    @abstractmethod
    def capture_minimap(self, client_rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Capture and return the top-left minimap crop in BGR format."""
        pass

    @staticmethod
    def calculate_minimap_crop_rect(
        window_width: int,
        window_height: int,
        base_resolution: Tuple[int, int] = (1920, 1080),
        base_crop: Tuple[int, int, int, int] = (30, 20, 220, 220),
    ) -> Tuple[int, int, int, int]:
        """Calculate resolution-aware minimap crop rect (x, y, width, height).

        For 1080p (1920x1080), default crop is (30, 20, 220, 220).
        For other resolutions (e.g. 1440p, 4K, 720p), scales proportionally.
        """
        base_w, base_h = base_resolution
        base_x, base_y, base_cw, base_ch = base_crop

        scale_x = window_width / float(base_w)
        scale_y = window_height / float(base_h)
        # Minimap maintains 1:1 aspect ratio, so scale size by minimum dimension scale
        scale_size = min(scale_x, scale_y)

        crop_x = int(round(base_x * scale_x))
        crop_y = int(round(base_y * scale_y))
        crop_w = max(32, int(round(base_cw * scale_size)))
        crop_h = max(32, int(round(base_ch * scale_size)))

        # Bounds check against window dimensions
        if crop_x + crop_w > window_width:
            crop_w = max(10, window_width - crop_x)
        if crop_y + crop_h > window_height:
            crop_h = max(10, window_height - crop_y)

        return crop_x, crop_y, crop_w, crop_h
