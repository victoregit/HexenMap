"""Player heading and orientation detector analyzing the minimap player pointer."""

from __future__ import annotations
import math
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class PlayerHeadingDetector:
    """Detects player orientation in degrees [0, 360) from minimap center crop."""

    _CYAN_LOWER = np.array([75, 80, 140], dtype=np.uint8)
    _CYAN_UPPER = np.array([115, 255, 255], dtype=np.uint8)
    _YELLOW_LOWER = np.array([18, 90, 150], dtype=np.uint8)
    _YELLOW_UPPER = np.array([42, 255, 255], dtype=np.uint8)
    _WHITE_LOWER = np.array([0, 0, 215], dtype=np.uint8)
    _WHITE_UPPER = np.array([180, 60, 255], dtype=np.uint8)
    _MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)) if cv2 is not None else None

    def __init__(
        self,
        center_roi_fraction: float = 0.35,
        min_contour_area: float = 12.0,
    ) -> None:
        self.center_roi_fraction = center_roi_fraction
        self.min_contour_area = min_contour_area
        self._last_heading: float = 0.0

    def detect_heading(self, minimap_crop: Optional[np.ndarray]) -> Tuple[float, float]:
        """Detect player heading angle in degrees (0=N, 90=E, 180=S, 270=W) and confidence [0, 1].

        Args:
            minimap_crop: BGR or grayscale numpy array of the minimap.

        Returns:
            Tuple of (heading_degrees, confidence).
        """
        if minimap_crop is None or not isinstance(minimap_crop, np.ndarray) or minimap_crop.size == 0:
            return self._last_heading, 0.0

        if cv2 is None:
            return self._last_heading, 0.0

        h, w = minimap_crop.shape[:2]
        if h < 20 or w < 20:
            return self._last_heading, 0.0

        # Extract Center Region of Interest (ROI) where the player arrow is located
        roi_w = int(w * self.center_roi_fraction)
        roi_h = int(h * self.center_roi_fraction)
        cx, cy = w // 2, h // 2
        x1 = max(0, cx - roi_w // 2)
        y1 = max(0, cy - roi_h // 2)
        x2 = min(w, x1 + roi_w)
        y2 = min(h, y1 + roi_h)

        roi = minimap_crop[y1:y2, x1:x2]
        roi_center_x = (x2 - x1) / 2.0
        roi_center_y = (y2 - y1) / 2.0

        # Convert to HSV if 3 channels
        if len(roi.shape) == 3 and roi.shape[2] == 3:
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # Mask 1: Cyan / Light Blue pointer (Genshin player indicator)
            mask_cyan = cv2.inRange(hsv, self._CYAN_LOWER, self._CYAN_UPPER)
            # Mask 2: Yellow / Gold pointer (Genshin co-op / alternate indicator)
            mask_yellow = cv2.inRange(hsv, self._YELLOW_LOWER, self._YELLOW_UPPER)
            # Mask 3: High-brightness highlight mask
            mask_white = cv2.inRange(hsv, self._WHITE_LOWER, self._WHITE_UPPER)

            mask = cv2.bitwise_or(mask_cyan, mask_yellow)
            mask = cv2.bitwise_or(mask, mask_white)
        else:
            # Grayscale fallback
            gray = roi if len(roi.shape) == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Morphological clean up
        kernel = self._MORPH_KERNEL if self._MORPH_KERNEL is not None else cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._last_heading, 0.0

        # Choose the contour closest to the ROI center with sufficient area
        best_contour = None
        best_dist = float("inf")

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_contour_area:
                continue

            m = cv2.moments(cnt)
            if m["m00"] == 0:
                continue
            cnt_cx = m["m10"] / m["m00"]
            cnt_cy = m["m01"] / m["m00"]
            dist_to_center = math.hypot(cnt_cx - roi_center_x, cnt_cy - roi_center_y)

            if dist_to_center < best_dist:
                best_dist = dist_to_center
                best_contour = cnt

        if best_contour is None:
            return self._last_heading, 0.0

        # Compute contour centroid
        m = cv2.moments(best_contour)
        if m["m00"] == 0:
            return self._last_heading, 0.0
        centroid_x = m["m10"] / m["m00"]
        centroid_y = m["m01"] / m["m00"]

        # Find the acute tip of the arrow (point furthest from centroid along primary axis)
        pts = best_contour.reshape(-1, 2)
        dists = np.hypot(pts[:, 0] - centroid_x, pts[:, 1] - centroid_y)
        tip_idx = int(np.argmax(dists))
        tip_x, tip_y = pts[tip_idx]

        dx = float(tip_x - centroid_x)
        dy = float(tip_y - centroid_y)
        dist = math.hypot(dx, dy)

        if dist < 2.0:
            # Arrow is circular or stationary
            return self._last_heading, 0.2

        # Convert to clockwise compass heading:
        # dx positive right, dy positive down. 0 deg = North (up, dy < 0)
        heading_rad = math.atan2(dx, -dy)
        heading_deg = (math.degrees(heading_rad) + 360.0) % 360.0

        # Confidence metric based on contour area and sharpness
        area = cv2.contourArea(best_contour)
        confidence = min(1.0, max(0.4, (area / 100.0) * 0.8 + 0.2))

        self._last_heading = round(heading_deg, 1)
        return self._last_heading, round(confidence, 2)
