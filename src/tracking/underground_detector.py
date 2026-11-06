"""Underground cavern vs overworld surface terrain classifier."""

from __future__ import annotations
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class UndergroundCaveDetector:
    """Classifies whether the minimap view corresponds to surface terrain or underground caverns."""

    def __init__(
        self,
        saturation_threshold: float = 35.0,
        darkness_threshold: float = 75.0,
    ) -> None:
        self.saturation_threshold = saturation_threshold
        self.darkness_threshold = darkness_threshold
        self._last_detected_layer: str = "surface"

    def detect_layer(self, minimap_crop: Optional[np.ndarray]) -> Tuple[str, float]:
        """Classify active minimap layer as 'surface' or 'underground'.

        Returns:
            Tuple of (layer_id: str, confidence: float [0.0, 1.0]).
        """
        if minimap_crop is None or not isinstance(minimap_crop, np.ndarray) or minimap_crop.size == 0:
            return self._last_detected_layer, 0.0

        if cv2 is None or len(minimap_crop.shape) != 3 or minimap_crop.shape[2] != 3:
            return self._last_detected_layer, 0.5

        # Sample circular central region of minimap to avoid UI border elements
        h, w = minimap_crop.shape[:2]
        r = min(h, w) // 3
        cx, cy = w // 2, h // 2
        inner_roi = minimap_crop[cy - r : cy + r, cx - r : cx + r]

        if inner_roi.size == 0:
            return self._last_detected_layer, 0.0

        hsv = cv2.cvtColor(inner_roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        val_mean = float(np.mean(hsv[:, :, 2]))

        # Calculate blue/green channel vibrancy vs red
        b_mean = float(np.mean(inner_roi[:, :, 0]))
        g_mean = float(np.mean(inner_roi[:, :, 1]))
        r_mean = float(np.mean(inner_roi[:, :, 2]))

        # Underground caverns (e.g. The Chasm underground) feature low saturation and dark slate palette
        is_subterranean = (sat_mean < self.saturation_threshold) and (val_mean < self.darkness_threshold)

        # If nearly monochromatic gray/slate:
        color_variance = max(abs(b_mean - g_mean), abs(g_mean - r_mean), abs(b_mean - r_mean))
        if color_variance < 10.0 and val_mean < 80.0:
            is_subterranean = True

        if is_subterranean:
            self._last_detected_layer = "underground"
            # Confidence grows as saturation and brightness drop further below threshold
            conf = min(0.95, 0.65 + (self.darkness_threshold - val_mean) / 100.0)
            return "underground", round(conf, 2)
        else:
            self._last_detected_layer = "surface"
            conf = min(0.95, 0.65 + sat_mean / 100.0)
            return "surface", round(conf, 2)
