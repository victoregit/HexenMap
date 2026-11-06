"""Unit tests for screen capture subsystem and resolution scaling."""

import pytest
import numpy as np

from src.capture.base import ScreenCaptureInterface
from src.capture.win32_capture import MockScreenCapture, Win32ScreenCapture, get_screen_capture


class TestScreenCaptureScaling:
    def test_calculate_minimap_crop_1080p(self):
        # Base 1080p (1920x1080)
        x, y, w, h = ScreenCaptureInterface.calculate_minimap_crop_rect(1920, 1080)
        assert x == 30
        assert y == 20
        assert w == 220
        assert h == 220

    def test_calculate_minimap_crop_1440p(self):
        # 1440p (2560x1440) -> 1.333x scale
        x, y, w, h = ScreenCaptureInterface.calculate_minimap_crop_rect(2560, 1440)
        assert x == int(round(30 * (2560 / 1920)))
        assert y == int(round(20 * (1440 / 1080)))
        assert w == int(round(220 * (1440 / 1080)))
        assert h == int(round(220 * (1440 / 1080)))

    def test_calculate_minimap_crop_4k(self):
        # 4K (3840x2160) -> 2.0x scale
        x, y, w, h = ScreenCaptureInterface.calculate_minimap_crop_rect(3840, 2160)
        assert x == 60
        assert y == 40
        assert w == 440
        assert h == 440

    def test_calculate_minimap_crop_boundary_clamping(self):
        # Small window (100x100)
        x, y, w, h = ScreenCaptureInterface.calculate_minimap_crop_rect(100, 100)
        assert x + w <= 100
        assert y + h <= 100
        assert w >= 10
        assert h >= 10


class TestMockScreenCapture:
    def test_mock_lifecycle_and_game_running(self):
        mock = MockScreenCapture(game_running=True)
        assert mock.is_game_running() is True
        assert mock.find_game_window() == (0, 0, 1920, 1080)

        mock.set_game_running(False)
        assert mock.is_game_running() is False
        assert mock.find_game_window() is None
        assert mock.capture_frame() is None
        assert mock.capture_minimap() is None

    def test_mock_capture_frame_dimensions(self):
        mock = MockScreenCapture(window_rect=(10, 10, 800, 600))
        frame = mock.capture_frame()
        assert frame is not None
        assert frame.shape == (600, 800, 3)

    def test_mock_capture_minimap_dimensions(self):
        mock = MockScreenCapture(window_rect=(0, 0, 1920, 1080))
        minimap = mock.capture_minimap()
        assert minimap is not None
        assert minimap.shape == (220, 220, 3)

    def test_custom_frame_and_minimap_injection(self):
        mock = MockScreenCapture()
        custom = np.full((100, 100, 3), 128, dtype=np.uint8)
        mock.set_custom_minimap(custom)
        captured = mock.capture_minimap()
        assert np.array_equal(captured, custom)

    def test_get_screen_capture_factory(self):
        capture = get_screen_capture(prefer_mock=True)
        assert isinstance(capture, MockScreenCapture)
