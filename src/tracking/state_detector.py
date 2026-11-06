"""Game state detection engine to suspend CV execution during loading screens and cutscenes."""

from __future__ import annotations
from enum import Enum
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class GameState(str, Enum):
    """Current state of the game client."""
    ACTIVE_GAMEPLAY = "active_gameplay"
    LOADING_SCREEN = "loading_screen"
    CUTSCENE_OR_DIALOGUE = "cutscene_dialogue"
    MENU_OPEN = "menu_open"
    UNKNOWN = "unknown"


class GameStateDetector:
    """Heuristic classifier detecting loading screens, cutscenes, and active gameplay."""

    def __init__(
        self,
        loading_std_threshold: float = 14.0,
        letterbox_brightness_threshold: float = 16.0,
        active_edge_threshold: float = 12.0,
    ) -> None:
        self.loading_std_threshold = loading_std_threshold
        self.letterbox_brightness_threshold = letterbox_brightness_threshold
        self.active_edge_threshold = active_edge_threshold

    def detect_state(
        self,
        full_frame: Optional[np.ndarray] = None,
        minimap_crop: Optional[np.ndarray] = None,
    ) -> Tuple[GameState, float]:
        """Classify current game screen state.

        Returns:
            Tuple of (GameState, confidence [0.0, 1.0]).
        """
        if full_frame is None and minimap_crop is None:
            return GameState.UNKNOWN, 0.0

        # 1. Analyze minimap crop if available (fastest check)
        if minimap_crop is not None and isinstance(minimap_crop, np.ndarray) and minimap_crop.size > 0:
            std = float(np.std(minimap_crop))
            mean_val = float(np.mean(minimap_crop))

            # Loading screen heuristic (solid white or black screen)
            if std < self.loading_std_threshold and (mean_val > 220.0 or mean_val < 30.0):
                return GameState.LOADING_SCREEN, 0.95

            # Edge density test
            if cv2 is not None:
                gray = minimap_crop if len(minimap_crop.shape) == 2 else cv2.cvtColor(minimap_crop, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                edge_pct = (np.count_nonzero(edges) / float(edges.size)) * 100.0

                # In cutscenes/dialogues, the minimap UI is hidden
                if edge_pct < 0.5 and std < 20.0:
                    return GameState.CUTSCENE_OR_DIALOGUE, 0.85

                if edge_pct >= 2.0 and std >= self.loading_std_threshold:
                    return GameState.ACTIVE_GAMEPLAY, 0.92

        # 2. Analyze full frame if available
        if full_frame is not None and isinstance(full_frame, np.ndarray) and full_frame.size > 0:
            fh, fw = full_frame.shape[:2]
            if fh >= 100 and fw >= 100:
                # Subsample top, center, and bottom slices for sub-millisecond letterbox check
                top_slice = full_frame[: int(fh * 0.06), :]
                bot_slice = full_frame[-int(fh * 0.06) :, :]
                mid_slice = full_frame[int(fh * 0.3) : int(fh * 0.7), :]

                top_mean = float(np.mean(top_slice))
                bot_mean = float(np.mean(bot_slice))
                mid_mean = float(np.mean(mid_slice))

                # Pure black top/bottom letterbox bars during story cutscenes
                if top_mean < self.letterbox_brightness_threshold and bot_mean < self.letterbox_brightness_threshold and mid_mean > 35.0:
                    return GameState.CUTSCENE_OR_DIALOGUE, 0.90

                frame_std = float(np.std(mid_slice))
                if frame_std < self.loading_std_threshold and (mid_mean > 225.0 or mid_mean < 25.0):
                    return GameState.LOADING_SCREEN, 0.95

                return GameState.ACTIVE_GAMEPLAY, 0.85

        return GameState.ACTIVE_GAMEPLAY, 0.60
