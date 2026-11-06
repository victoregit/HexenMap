"""Unit tests for AutoTrackerService background worker lifecycle and event propagation."""

import time
import numpy as np
import pytest
import cv2

from src.capture.win32_capture import MockScreenCapture
from src.performance.performance_monitor import PerformanceMonitor
from src.tracking.autotracker_service import AutoTrackerService
from src.tracking.base import PositionEstimate
from src.tracking.position_tracker import SimulatedPositionTracker
from src.tracking.state_detector import GameState


class TestAutoTrackerService:
    @pytest.fixture
    def mock_capture(self):
        # Create a mock screen capture producing an active minimap with a 90° East arrow
        mock = MockScreenCapture()
        active_minimap = np.full((220, 220, 3), (70, 130, 90), dtype=np.uint8)
        cv2.circle(active_minimap, (110, 110), 90, (200, 200, 200), 2)
        # Draw East-pointing arrow (tip at 130, 110)
        triangle = np.array([[130, 110], [98, 102], [110, 110], [98, 118]], dtype=np.int32)
        cv2.fillPoly(active_minimap, [triangle], (255, 230, 0))
        mock.set_custom_minimap(active_minimap)
        return mock

    @pytest.fixture
    def service(self, mock_capture):
        perf = PerformanceMonitor()
        sim_tracker = SimulatedPositionTracker()
        srv = AutoTrackerService(
            capture_backend=mock_capture,
            position_tracker=sim_tracker,
            perf_monitor=perf,
            sample_interval_sec=0.04,  # Fast 25 Hz for testing
        )
        yield srv
        srv.stop()

    def test_service_lifecycle_start_pause_stop(self, service):
        assert service.is_running is False
        assert service.is_paused is False

        service.start()
        assert service.is_running is True

        service.pause()
        assert service.is_paused is True

        service.resume()
        assert service.is_paused is False

        service.stop()
        assert service.is_running is False

    def test_position_listener_invoked(self, service):
        received_estimates = []

        def on_pos(est: PositionEstimate):
            received_estimates.append(est)

        service.add_position_listener(on_pos)
        service.start()

        # Wait for worker ticks
        time.sleep(0.12)
        service.stop()

        assert len(received_estimates) >= 1
        latest = received_estimates[-1]
        assert latest.is_valid is True
        # Check that heading was detected around 90 degrees (East)
        diff = abs(latest.heading_degrees - 90.0)
        assert min(diff, 360.0 - diff) <= 5.0
        assert latest.layer == "surface"

    def test_state_listener_and_cv_suspension(self, service, mock_capture):
        state_changes = []

        def on_state(st: GameState):
            state_changes.append(st)

        service.add_state_listener(on_state)

        # Inject a solid black loading screen into capture
        black_loading = np.full((220, 220, 3), 5, dtype=np.uint8)
        mock_capture.set_custom_minimap(black_loading)

        service.start()
        time.sleep(0.10)
        service.stop()

        assert GameState.LOADING_SCREEN in state_changes

    def test_remove_listener(self, service):
        received = []
        listener = lambda est: received.append(est)

        service.add_position_listener(listener)
        service.remove_position_listener(listener)

        service.start()
        time.sleep(0.08)
        service.stop()

        assert len(received) == 0
