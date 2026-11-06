"""Abstract interfaces and data models for player position tracking."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
from typing import Any, Dict, Optional


@dataclass
class PositionEstimate:
    """Estimated player position and orientation."""
    x: float
    y: float
    confidence: float = 0.0          # Range 0.0 (unreliable) to 1.0 (perfect)
    layer: str = "surface"           # 'surface' or 'underground'
    heading_degrees: float = 0.0     # 0 = North, 90 = East, 180 = South, 270 = West
    is_valid: bool = False
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "layer": self.layer,
            "heading_degrees": self.heading_degrees,
            "is_valid": self.is_valid,
            "timestamp": self.timestamp,
        }

    @classmethod
    def invalid(cls) -> PositionEstimate:
        return cls(x=0.0, y=0.0, confidence=0.0, is_valid=False)


class PositionTrackerInterface(ABC):
    """Abstract interface for CV and simulated position tracking engines."""

    @abstractmethod
    def estimate_position(self, frame: Optional[Any] = None) -> PositionEstimate:
        """Estimate the current world position from an image frame or sensor feed."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracking state or cached templates."""
        pass
