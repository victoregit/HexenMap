"""Unit tests for position trackers (Simulated and OpenCV Minimap Template Tracker)."""

import time
import numpy as np
import pytest
from src.tracking.base import PositionEstimate
from src.tracking.position_tracker import MinimapTemplateTracker, SimulatedPositionTracker


class TestPositionEstimate:
    def test_default_and_invalid(self):
        est = PositionEstimate.invalid()
        assert est.is_valid is False
        assert est.confidence == 0.0
        assert est.to_dict()["is_valid"] is False

    def test_valid_estimate(self):
        est = PositionEstimate(x=100.0, y=200.0, confidence=0.88, layer="surface", heading_degrees=45.0, is_valid=True)
        assert est.x == 100.0
        assert est.confidence == 0.88
        assert est.is_valid is True


class TestSimulatedPositionTracker:
    def test_navigation_along_waypoints(self):
        tracker = SimulatedPositionTracker(
            waypoints=[(0.0, 0.0), (100.0, 0.0)],
            speed_units_per_sec=1000.0,  # Fast to trigger waypoint transition
        )
        pos0 = tracker.estimate_position()
        assert pos0.is_valid is True
        assert pos0.confidence > 0.9

        # Sleep slightly and estimate again
        time.sleep(0.02)
        pos1 = tracker.estimate_position()
        assert pos1.is_valid is True
        assert pos1.x >= 0.0

    def test_set_position_and_reset(self):
        tracker = SimulatedPositionTracker()
        tracker.set_position(555.0, -888.0, heading=180.0)
        pos = tracker.estimate_position()
        assert pos.heading_degrees == 180.0

        tracker.reset()
        pos_reset = tracker.estimate_position()
        assert pos_reset.x != 555.0


class TestMinimapTemplateTracker:
    def test_graceful_handling_on_none_and_empty(self):
        tracker = MinimapTemplateTracker(sample_interval_sec=0.0)
        # None frame
        assert tracker.estimate_position(None).is_valid is False
        # Empty array
        assert tracker.estimate_position(np.array([])).is_valid is False

    def test_template_match_synthetic_success(self, synthetic_minimap_pair):
        ref_map, crop = synthetic_minimap_pair
        # World bounds from 0 to 2000
        bounds = (0.0, 0.0, 2000.0, 2000.0)
        tracker = MinimapTemplateTracker(
            reference_map=ref_map,
            world_bounds=bounds,
            min_confidence=0.70,
            sample_interval_sec=0.0,  # No rate limit for unit test
        )

        estimate = tracker.estimate_position(crop)
        assert estimate.is_valid is True
        assert estimate.confidence >= 0.90
        # Expected position corresponds to center of the crop in world coords
        # Crop is [45:75, 55:85], center is (70, 60) in (x, y) coordinates of the 200x200 image
        # x: 70/200 * 2000 = 700; y: 60/200 * 2000 = 600
        assert pytest.approx(estimate.x, abs=10.0) == 700.0
        assert pytest.approx(estimate.y, abs=10.0) == 600.0

    def test_template_match_low_confidence_fallback(self, synthetic_minimap_pair):
        ref_map, _ = synthetic_minimap_pair
        # Completely random noise as crop
        noise_crop = np.random.randint(0, 255, (30, 30, 3), dtype=np.uint8)

        tracker = MinimapTemplateTracker(
            reference_map=ref_map,
            min_confidence=0.85,
            sample_interval_sec=0.0,
        )
        estimate = tracker.estimate_position(noise_crop)
        # Should report invalid due to low correlation
        assert estimate.is_valid is False

    def test_rate_limiting(self, synthetic_minimap_pair):
        ref_map, crop = synthetic_minimap_pair
        tracker = MinimapTemplateTracker(
            reference_map=ref_map,
            sample_interval_sec=1.0,  # 1 second rate limit
        )
        est1 = tracker.estimate_position(crop)
        assert est1.is_valid is True

        # Call immediately again with invalid frame; should return cached est1 because < 1 sec
        est2 = tracker.estimate_position(None)
        assert est2.is_valid is True
        assert est2.x == est1.x
