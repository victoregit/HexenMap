"""Continuous smoothed position tracker and confidence gating.

Implements Exponential Moving Average (EMA) filtering on world coordinates (x, y)
and circular statistics smoothing on compass heading angle (handling the 359° <-> 0° boundary),
plus strict confidence gating (< 60% rejection) to eliminate marker jitter and hallucination.
"""

from __future__ import annotations
import math
import time
from typing import Optional

from src.tracking.base import PositionEstimate


class SmoothedPositionTracker:
    """Filters noisy position estimates using Exponential Moving Average and circular angular statistics."""

    def __init__(self, alpha: float = 0.35, angle_alpha: float = 0.30) -> None:
        """Initialize tracker with smoothing coefficients.

        Args:
            alpha: Coordinate smoothing factor in range (0.0, 1.0].
                   Higher = more responsive, lower = smoother.
            angle_alpha: Heading angle smoothing factor in range (0.0, 1.0].
        """
        self.alpha = max(0.01, min(1.0, float(alpha)))
        self.angle_alpha = max(0.01, min(1.0, float(angle_alpha)))

        self._current_x: Optional[float] = None
        self._current_y: Optional[float] = None
        self._sin_heading: Optional[float] = None
        self._cos_heading: Optional[float] = None
        self._last_estimate: Optional[PositionEstimate] = None

    @property
    def has_state(self) -> bool:
        return self._current_x is not None and self._current_y is not None

    def reset(self) -> None:
        """Clear smoothed state."""
        self._current_x = None
        self._current_y = None
        self._sin_heading = None
        self._cos_heading = None
        self._last_estimate = None

    def update(self, estimate: PositionEstimate) -> PositionEstimate:
        """Update tracker with a new position estimate and return smoothed estimate.

        If the incoming estimate is invalid, returns the invalid estimate.
        """
        if not estimate.is_valid:
            return estimate

        # 1. Coordinate smoothing
        if self._current_x is None or self._current_y is None:
            self._current_x = float(estimate.x)
            self._current_y = float(estimate.y)
        else:
            self._current_x = self.alpha * float(estimate.x) + (1.0 - self.alpha) * self._current_x
            self._current_y = self.alpha * float(estimate.y) + (1.0 - self.alpha) * self._current_y

        # 2. Heading angle circular statistics smoothing (handling 359° <-> 0° jump)
        rad = math.radians(estimate.heading_degrees % 360.0)
        s_raw = math.sin(rad)
        c_raw = math.cos(rad)

        if self._sin_heading is None or self._cos_heading is None:
            self._sin_heading = s_raw
            self._cos_heading = c_raw
        else:
            self._sin_heading = self.angle_alpha * s_raw + (1.0 - self.angle_alpha) * self._sin_heading
            self._cos_heading = self.angle_alpha * c_raw + (1.0 - self.angle_alpha) * self._cos_heading

        smoothed_rad = math.atan2(self._sin_heading, self._cos_heading)
        smoothed_deg = (math.degrees(smoothed_rad) + 360.0) % 360.0

        smoothed_est = PositionEstimate(
            x=self._current_x,
            y=self._current_y,
            confidence=estimate.confidence,
            layer=estimate.layer,
            heading_degrees=smoothed_deg,
            is_valid=True,
            timestamp=estimate.timestamp or time.time(),
        )
        self._last_estimate = smoothed_est
        return smoothed_est


class ConfidenceGatedTracker:
    """Rejects noisy, unconfident position estimates below an acceptance threshold."""

    def __init__(
        self,
        min_confidence: float = 0.60,
        downstream_smoother: Optional[SmoothedPositionTracker] = None,
    ) -> None:
        """Initialize confidence gate.

        Args:
            min_confidence: Minimum required confidence [0.0, 1.0] to accept an estimate.
            downstream_smoother: Optional SmoothedPositionTracker to smooth accepted estimates.
        """
        self.min_confidence = float(min_confidence)
        self.smoother = downstream_smoother or SmoothedPositionTracker()
        self._rejected_count = 0
        self._accepted_count = 0

    @property
    def rejected_count(self) -> int:
        return self._rejected_count

    @property
    def accepted_count(self) -> int:
        return self._accepted_count

    def reset(self) -> None:
        self.smoother.reset()
        self._rejected_count = 0
        self._accepted_count = 0

    def process(self, raw_estimate: PositionEstimate) -> PositionEstimate:
        """Filter raw estimate through the confidence gate and optional smoother.

        Returns PositionEstimate.invalid() if confidence is below threshold.
        """
        if not raw_estimate.is_valid or raw_estimate.confidence < self.min_confidence:
            self._rejected_count += 1
            return PositionEstimate.invalid()

        self._accepted_count += 1
        return self.smoother.update(raw_estimate)
