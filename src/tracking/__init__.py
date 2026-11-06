"""Player position tracking module."""

from src.tracking.base import PositionEstimate, PositionTrackerInterface
from src.tracking.position_tracker import MinimapTemplateTracker, SimulatedPositionTracker
from src.tracking.heading_detector import PlayerHeadingDetector
from src.tracking.state_detector import GameState, GameStateDetector
from src.tracking.underground_detector import UndergroundCaveDetector
from src.tracking.autotracker_service import AutoTrackerService
from src.tracking.smooth_tracker import ConfidenceGatedTracker, SmoothedPositionTracker
from src.tracking.reference_tile_manager import ReferenceTile, ReferenceTileManager

__all__ = [
    "AutoTrackerService",
    "ConfidenceGatedTracker",
    "GameState",
    "GameStateDetector",
    "MinimapTemplateTracker",
    "PlayerHeadingDetector",
    "PositionEstimate",
    "PositionTrackerInterface",
    "ReferenceTile",
    "ReferenceTileManager",
    "SimulatedPositionTracker",
    "SmoothedPositionTracker",
    "UndergroundCaveDetector",
]
