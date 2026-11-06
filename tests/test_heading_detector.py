"""Unit tests for PlayerHeadingDetector angle accuracy and robustness."""

import math
import numpy as np
import pytest
import cv2

from src.tracking.heading_detector import PlayerHeadingDetector


def create_synthetic_minimap_with_arrow(
    size: int = 220,
    heading_deg: float = 0.0,
    color_bgr: tuple = (255, 230, 0),  # Cyan pointer
) -> np.ndarray:
    """Helper to draw a directional arrow at center of a simulated minimap."""
    img = np.full((size, size, 3), (70, 110, 80), dtype=np.uint8)
    cx, cy = size // 2, size // 2

    rad = math.radians(heading_deg)
    arrow_len = 22.0
    tip_x = int(round(cx + arrow_len * math.sin(rad)))
    tip_y = int(round(cy - arrow_len * math.cos(rad)))

    base_rad_left = rad + math.radians(140)
    base_rad_right = rad - math.radians(140)
    base_len = 12.0
    b1_x = int(round(cx + base_len * math.sin(base_rad_left)))
    b1_y = int(round(cy - base_len * math.cos(base_rad_left)))
    b2_x = int(round(cx + base_len * math.sin(base_rad_right)))
    b2_y = int(round(cy - base_len * math.cos(base_rad_right)))

    triangle = np.array([[tip_x, tip_y], [b1_x, b1_y], [cx, cy], [b2_x, b2_y]], dtype=np.int32)
    cv2.fillPoly(img, [triangle], color_bgr)
    return img


class TestPlayerHeadingDetector:
    @pytest.fixture
    def detector(self):
        return PlayerHeadingDetector()

    @pytest.mark.parametrize("target_angle", [0.0, 45.0, 90.0, 180.0, 270.0, 315.0])
    def test_heading_accuracy_at_known_angles(self, detector, target_angle):
        minimap = create_synthetic_minimap_with_arrow(size=220, heading_deg=target_angle)
        detected_angle, confidence = detector.detect_heading(minimap)

        assert confidence >= 0.5
        # Angular difference taking 360 wrap-around into account
        diff = abs(detected_angle - target_angle)
        diff = min(diff, 360.0 - diff)
        assert diff <= 3.5, f"Target {target_angle}°, detected {detected_angle}° (diff {diff}°)"

    def test_yellow_coop_pointer(self, detector):
        # Yellow arrow pointer (BGR: 40, 210, 255)
        minimap = create_synthetic_minimap_with_arrow(size=220, heading_deg=90.0, color_bgr=(40, 210, 255))
        detected_angle, confidence = detector.detect_heading(minimap)
        assert confidence >= 0.4
        diff = abs(detected_angle - 90.0)
        assert min(diff, 360.0 - diff) <= 3.5

    def test_none_and_empty_inputs(self, detector):
        angle, conf = detector.detect_heading(None)
        assert conf == 0.0
        angle2, conf2 = detector.detect_heading(np.array([]))
        assert conf2 == 0.0

    def test_blank_and_noise_minimap(self, detector):
        # Blank green field without arrow
        blank = np.full((220, 220, 3), (70, 110, 80), dtype=np.uint8)
        _, conf = detector.detect_heading(blank)
        assert conf == 0.0

        # Uniform noise
        noise = np.random.randint(0, 100, (220, 220, 3), dtype=np.uint8)
        _, conf_noise = detector.detect_heading(noise)
        assert conf_noise <= 0.2
