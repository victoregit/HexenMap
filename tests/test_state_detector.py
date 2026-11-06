"""Unit tests for GameStateDetector loading screen, cutscene, and gameplay classification."""

import numpy as np
import pytest
import cv2

from src.tracking.state_detector import GameState, GameStateDetector


class TestGameStateDetector:
    @pytest.fixture
    def detector(self):
        return GameStateDetector()

    def test_loading_screen_solid_black(self, detector):
        # 1080p black loading screen
        black_screen = np.full((1080, 1920, 3), 5, dtype=np.uint8)
        state, conf = detector.detect_state(full_frame=black_screen)
        assert state == GameState.LOADING_SCREEN
        assert conf >= 0.90

    def test_loading_screen_solid_white(self, detector):
        # White teleport transition screen
        white_screen = np.full((1080, 1920, 3), 245, dtype=np.uint8)
        state, conf = detector.detect_state(full_frame=white_screen)
        assert state == GameState.LOADING_SCREEN
        assert conf >= 0.90

    def test_loading_screen_on_minimap_crop(self, detector):
        # Black or white minimap crop during loading
        black_crop = np.full((220, 220, 3), 2, dtype=np.uint8)
        state, conf = detector.detect_state(minimap_crop=black_crop)
        assert state == GameState.LOADING_SCREEN
        assert conf >= 0.90

    def test_cutscene_dialogue_letterbox(self, detector):
        # 1080p frame with black bars on top and bottom 6%
        frame = np.full((1080, 1920, 3), 100, dtype=np.uint8)
        frame[:80, :] = 0   # top black bar
        frame[-80:, :] = 0  # bottom black bar
        state, conf = detector.detect_state(full_frame=frame)
        assert state == GameState.CUTSCENE_OR_DIALOGUE
        assert conf >= 0.80

    def test_active_gameplay_minimap(self, detector):
        # Active minimap with circular border and terrain features
        minimap = np.full((220, 220, 3), (70, 130, 90), dtype=np.uint8)
        cv2.circle(minimap, (110, 110), 90, (200, 200, 200), 2)
        cv2.line(minimap, (40, 40), (180, 180), (180, 120, 40), 5)

        state, conf = detector.detect_state(minimap_crop=minimap)
        assert state == GameState.ACTIVE_GAMEPLAY
        assert conf >= 0.85

    def test_unknown_when_none(self, detector):
        state, conf = detector.detect_state(None, None)
        assert state == GameState.UNKNOWN
        assert conf == 0.0
