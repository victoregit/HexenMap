"""Unit tests for UndergroundCaveDetector surface vs subterranean classification."""

import numpy as np
import pytest
import cv2

from src.tracking.underground_detector import UndergroundCaveDetector


class TestUndergroundCaveDetector:
    @pytest.fixture
    def detector(self):
        return UndergroundCaveDetector()

    def test_surface_terrain_classification(self, detector):
        # Vibrant overworld grass and water minimap (BGR: green 130, blue 70, red 40)
        surface_crop = np.full((220, 220, 3), (70, 140, 60), dtype=np.uint8)
        # Add blue river
        surface_crop[80:120, :] = (200, 110, 40)

        layer, conf = detector.detect_layer(surface_crop)
        assert layer == "surface"
        assert conf >= 0.70

    def test_underground_cavern_classification(self, detector):
        # The Chasm underground dark slate cavern palette (BGR: ~45, 45, 50)
        underground_crop = np.full((220, 220, 3), (45, 48, 52), dtype=np.uint8)

        layer, conf = detector.detect_layer(underground_crop)
        assert layer == "underground"
        assert conf >= 0.70

    def test_none_and_empty_inputs(self, detector):
        layer, conf = detector.detect_layer(None)
        assert conf == 0.0
        layer_empty, conf_empty = detector.detect_layer(np.array([]))
        assert conf_empty == 0.0
