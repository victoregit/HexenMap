"""Background AutoTracker service coordinating screen capture and CV detection engines."""

from __future__ import annotations
import logging
import threading
import time
from typing import Callable, List, Optional

from src.capture.base import ScreenCaptureInterface
from src.capture.win32_capture import get_screen_capture
from src.performance.performance_monitor import PerformanceMonitor
from src.tracking.base import PositionEstimate, PositionTrackerInterface
from src.tracking.heading_detector import PlayerHeadingDetector
from src.tracking.position_tracker import MinimapTemplateTracker
from src.tracking.state_detector import GameState, GameStateDetector
from src.tracking.underground_detector import UndergroundCaveDetector

logger = logging.getLogger(__name__)


class AutoTrackerService:
    """Thread-safe background service executing real-time CV minimap autotracking at 5 Hz."""

    def __init__(
        self,
        capture_backend: Optional[ScreenCaptureInterface] = None,
        position_tracker: Optional[PositionTrackerInterface] = None,
        perf_monitor: Optional[PerformanceMonitor] = None,
        sample_interval_sec: float = 0.20,  # 5 Hz
    ) -> None:
        self.capture = capture_backend or get_screen_capture()
        self.pos_tracker = position_tracker or MinimapTemplateTracker(sample_interval_sec=0.0)
        self.heading_detector = PlayerHeadingDetector()
        self.state_detector = GameStateDetector()
        self.underground_detector = UndergroundCaveDetector()
        self.perf_monitor = perf_monitor

        self.sample_interval = sample_interval_sec
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._latest_estimate = PositionEstimate.invalid()
        self._latest_state = GameState.UNKNOWN
        self._listeners: List[Callable[[PositionEstimate], None]] = []
        self._state_listeners: List[Callable[[GameState], None]] = []

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    @property
    def latest_game_state(self) -> GameState:
        with self._lock:
            return self._latest_state

    def get_latest_estimate(self) -> PositionEstimate:
        """Thread-safe retrieval of latest position estimate."""
        with self._lock:
            return self._latest_estimate

    def add_position_listener(self, callback: Callable[[PositionEstimate], None]) -> None:
        """Register callback invoked whenever a new position estimate is produced."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_position_listener(self, callback: Callable[[PositionEstimate], None]) -> None:
        """Unregister position callback."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def add_state_listener(self, callback: Callable[[GameState], None]) -> None:
        """Register callback invoked when game state (loading/dialogue/gameplay) changes."""
        with self._lock:
            if callback not in self._state_listeners:
                self._state_listeners.append(callback)

    def start(self) -> None:
        """Launch background worker thread."""
        if self.is_running:
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="AutoTrackerService")
        self._thread.start()
        logger.info("AutoTrackerService background thread started at %.1f Hz.", 1.0 / self.sample_interval)

    def stop(self, timeout: float = 2.0) -> None:
        """Signal background thread to terminate and wait for exit."""
        self._stop_event.set()
        self._pause_event.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        logger.info("AutoTrackerService background thread stopped.")

    def pause(self) -> None:
        """Temporarily suspend CV processing."""
        self._pause_event.set()
        logger.debug("AutoTrackerService paused.")

    def resume(self) -> None:
        """Resume CV processing."""
        self._pause_event.clear()
        logger.debug("AutoTrackerService resumed.")

    def _worker_loop(self) -> None:
        """Core sampling loop running at target frequency."""
        while not self._stop_event.is_set():
            t0 = time.perf_counter()

            if not self._pause_event.is_set():
                try:
                    self._process_single_tick()
                except Exception as e:
                    logger.debug("Error in autotracker tick: %s", e)

            elapsed = time.perf_counter() - t0
            sleep_time = max(0.01, self.sample_interval - elapsed)
            self._stop_event.wait(timeout=sleep_time)

    def _process_single_tick(self) -> None:
        """Execute one frame capture and CV analysis cycle."""
        t_start = time.perf_counter()

        # 1. Capture minimap
        minimap = self.capture.capture_minimap()
        if minimap is None or minimap.size == 0:
            return

        # 2. Check Game State (loading screen or dialogue letterbox)
        state, _ = self.state_detector.detect_state(minimap_crop=minimap)
        with self._lock:
            prev_state = self._latest_state
            self._latest_state = state

        if state != prev_state:
            for slistener in list(self._state_listeners):
                try:
                    slistener(state)
                except Exception as e:
                    logger.debug("State listener error: %s", e)

        # Suspend expensive CV matching during cutscenes and loading screens
        if state in (GameState.LOADING_SCREEN, GameState.CUTSCENE_OR_DIALOGUE):
            return

        # 3. Position estimation
        pos_est = self.pos_tracker.estimate_position(minimap)

        # 4. Heading detection
        heading, heading_conf = self.heading_detector.detect_heading(minimap)

        # 5. Underground cavern detection
        detected_layer, _ = self.underground_detector.detect_layer(minimap)

        # 6. Compose enriched estimate
        enriched = PositionEstimate(
            x=pos_est.x if pos_est.is_valid else self._latest_estimate.x,
            y=pos_est.y if pos_est.is_valid else self._latest_estimate.y,
            confidence=pos_est.confidence if pos_est.is_valid else heading_conf,
            layer=detected_layer,
            heading_degrees=heading if heading_conf > 0.3 else self._latest_estimate.heading_degrees,
            is_valid=pos_est.is_valid or (heading_conf > 0.4 and self._latest_estimate.is_valid),
            timestamp=time.time(),
        )

        with self._lock:
            self._latest_estimate = enriched
            callbacks = list(self._listeners)

        # Notify subscribers
        for cb in callbacks:
            try:
                cb(enriched)
            except Exception as e:
                logger.debug("Position listener error: %s", e)

        # Report performance latency
        if self.perf_monitor:
            total_cv_ms = (time.perf_counter() - t_start) * 1000.0
            self.perf_monitor.record_cv_time(total_cv_ms)
