"""Position tracking implementations: CV Minimap Template Matcher & Simulation Tracker."""

from __future__ import annotations
import logging
import math
import time
from typing import Any, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # Graceful fallback if cv2 not installed

from src.tracking.base import PositionEstimate, PositionTrackerInterface

logger = logging.getLogger(__name__)


class MinimapTemplateTracker(PositionTrackerInterface):
    """Visual tracking engine using OpenCV template matching on minimap crops."""

    def __init__(
        self,
        reference_map: Optional[np.ndarray] = None,
        world_bounds: Tuple[float, float, float, float] = (-3000.0, -4000.0, 2000.0, 4500.0),
        min_confidence: float = 0.60,
        sample_interval_sec: float = 0.20,  # 5 Hz sampling to conserve CPU
    ) -> None:
        self._reference_map = reference_map
        self._world_bounds = world_bounds  # (min_x, min_y, max_x, max_y)
        self._min_confidence = min_confidence
        self._sample_interval = sample_interval_sec
        self._last_sample_time: float = 0.0
        self._last_estimate: PositionEstimate = PositionEstimate.invalid()

    @property
    def sample_interval(self) -> float:
        return self._sample_interval

    @sample_interval.setter
    def sample_interval(self, value: float) -> None:
        self._sample_interval = max(0.01, float(value))

    def set_reference_map(self, map_image: np.ndarray) -> None:
        """Assign reference terrain map array for matching."""
        self._reference_map = map_image

    def estimate_position(self, frame: Optional[Any] = None) -> PositionEstimate:
        """Estimate position from minimap frame crop.

        Args:
            frame: Minimap crop as BGR or Grayscale numpy array.

        Returns:
            PositionEstimate instance.
        """
        now = time.time()
        # Rate limit to target sampling rate unless frame is explicitly new test run
        if self._last_estimate.is_valid and (now - self._last_sample_time) < self._sample_interval:
            return self._last_estimate

        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return PositionEstimate.invalid()

        if self._reference_map is None or not isinstance(self._reference_map, np.ndarray):
            return PositionEstimate.invalid()

        if cv2 is None:
            logger.warning("cv2 is not installed. MinimapTemplateTracker cannot perform template matching.")
            return PositionEstimate.invalid()

        try:
            # Convert images to grayscale if 3 channels
            ref_gray = self._reference_map
            if len(ref_gray.shape) == 3:
                ref_gray = cv2.cvtColor(ref_gray, cv2.COLOR_BGR2GRAY)

            templ_gray = frame
            if len(templ_gray.shape) == 3:
                templ_gray = cv2.cvtColor(templ_gray, cv2.COLOR_BGR2GRAY)

            # Ensure template is smaller than reference
            th, tw = templ_gray.shape[:2]
            rh, rw = ref_gray.shape[:2]

            if th > rh or tw > rw:
                logger.warning("Template frame (%dx%d) larger than reference (%dx%d)", tw, th, rw, rh)
                return PositionEstimate.invalid()

            # Execute normalized cross-correlation
            res = cv2.matchTemplate(ref_gray, templ_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            confidence = float(max_val)
            if confidence < self._min_confidence:
                self._last_estimate = PositionEstimate(
                    x=0.0,
                    y=0.0,
                    confidence=confidence,
                    is_valid=False,
                    timestamp=now,
                )
                self._last_sample_time = now
                return self._last_estimate

            # Matched center in reference image coordinates
            match_x = max_loc[0] + tw / 2.0
            match_y = max_loc[1] + th / 2.0

            # Project pixel coordinate into world coordinate space
            min_wx, min_wy, max_wx, max_wy = self._world_bounds
            world_x = min_wx + (match_x / rw) * (max_wx - min_wx)
            world_y = min_wy + (match_y / rh) * (max_wy - min_wy)

            self._last_estimate = PositionEstimate(
                x=float(world_x),
                y=float(world_y),
                confidence=confidence,
                layer="surface",
                heading_degrees=0.0,
                is_valid=True,
                timestamp=now,
            )
            self._last_sample_time = now
            return self._last_estimate

        except Exception as e:
            logger.error("Template matching error: %s", e)
            return PositionEstimate.invalid()

    def reset(self) -> None:
        self._last_sample_time = 0.0
        self._last_estimate = PositionEstimate.invalid()


class SimulatedPositionTracker(PositionTrackerInterface):
    """Mock/Simulated position tracker for unit testing, benchmarks, and demo mode."""

    def __init__(
        self,
        waypoints: Optional[List[Tuple[float, float]]] = None,
        speed_units_per_sec: float = 50.0,
        initial_layer: str = "surface",
    ) -> None:
        self._waypoints = waypoints or [
            (-820.0, -2210.0),  # Windrise
            (-1150.0, -2920.0), # Starfell Lake
            (-1560.0, -2510.0), # Mondstadt City
            (-1200.0, -1850.0), # Dawn Winery
        ]
        self._current_index = 0
        self._current_x = self._waypoints[0][0]
        self._current_y = self._waypoints[0][1]
        self._speed = speed_units_per_sec
        self._layer = initial_layer
        self._heading = 0.0
        self._last_update_time = time.time()
        self._confidence = 0.98

    def estimate_position(self, frame: Optional[Any] = None) -> PositionEstimate:
        """Step position simulation forward along waypoints."""
        now = time.time()
        elapsed = now - self._last_update_time
        if elapsed >= 0.01:
            dt = min(1.0, elapsed)
            self._last_update_time = now

            target_x, target_y = self._waypoints[self._current_index]
            dx = target_x - self._current_x
            dy = target_y - self._current_y
            dist = math.hypot(dx, dy)

            step = self._speed * dt
            if dist <= step or dist < 1.0:
                self._current_x = target_x
                self._current_y = target_y
                self._current_index = (self._current_index + 1) % len(self._waypoints)
            else:
                self._current_x += (dx / dist) * step
                self._current_y += (dy / dist) * step
                # Calculate heading in degrees (0 = North, 90 = East)
                heading_rad = math.atan2(dx, -dy)
                self._heading = (math.degrees(heading_rad) + 360.0) % 360.0

        return PositionEstimate(
            x=self._current_x,
            y=self._current_y,
            confidence=self._confidence,
            layer=self._layer,
            heading_degrees=self._heading,
            is_valid=True,
            timestamp=now,
        )

    def set_position(self, x: float, y: float, heading: float = 0.0) -> None:
        """Directly place simulated player at coordinate."""
        self._current_x = x
        self._current_y = y
        self._heading = heading
        self._last_update_time = time.time()

    def reset(self) -> None:
        self._current_index = 0
        if self._waypoints:
            self._current_x = self._waypoints[0][0]
            self._current_y = self._waypoints[0][1]
        self._heading = 0.0
        self._last_update_time = time.time()
