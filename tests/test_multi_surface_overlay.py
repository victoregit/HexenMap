"""Unit and integration tests for Marco C: Live Windows Integration & Transparent Overlays."""

import numpy as np
import pytest
import time
from typing import List

from src.map.registration import MapRegistration

from src.overlay.capture_exclusion import (
    is_capture_excluded,
    set_capture_exclusion,
    WDA_EXCLUDEFROMCAPTURE,
    WDA_NONE,
)
from src.overlay.global_hotkeys import (
    GlobalHotkeyListener,
    VK_F11,
    VK_F12,
    MOD_NOREPEAT,
)
from src.overlay.window_tracker import (
    GameWindowRect,
    GameWindowTracker,
)
from src.overlay.multi_surface_manager import (
    ActiveSurfaceState,
    MultiSurfaceOverlayManager,
)
from src.markers.models import Marker, MarkerCoordinate
from src.map.minimap_projector import MinimapCircle
from src.tracking.state_detector import GameState


class TestMultiSurfaceOverlay:
    """Test suite verifying MultiSurfaceOverlayManager, capture exclusion, hotkeys, and window tracking."""

    @pytest.fixture
    def sample_markers(self) -> List[Marker]:
        return [
            Marker(
                id="chest_1",
                name="Chest 1",
                category_id="luxurious_chest",
                region_id="dragonspine",
                coordinates=MarkerCoordinate(x=100.0, y=100.0),
            ),
            Marker(
                id="chest_2",
                name="Chest 2",
                category_id="precious_chest",
                region_id="dragonspine",
                coordinates=MarkerCoordinate(x=120.0, y=100.0),
            ),
        ]

    def test_surface_state_transitions(self, sample_markers):
        """Verify dynamic state transitions between GAMEPLAY_MINIMAP, NATIVE_MAP_OPEN, MENU_OR_LOADING, and NO_GAME."""
        reg = MapRegistration()
        src_pts = np.array([[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0]], dtype=np.float32)
        dst_pts = np.array([[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]], dtype=np.float32)
        reg.register_from_control_points(src_pts, dst_pts)

        mgr = MultiSurfaceOverlayManager(
            hwnd=1234,
            initial_state=ActiveSurfaceState.NO_GAME,
            minimap_circle=MinimapCircle(center_x=100.0, center_y=100.0, radius=50.0),
            registration=reg,
        )

        transitions = []
        mgr.add_state_callback(lambda new_s, old_s: transitions.append((old_s, new_s)))

        # 1. Transition when game starts and is in gameplay
        mgr.update_from_game_state(GameState.ACTIVE_GAMEPLAY, is_game_running=True)
        assert mgr.state == ActiveSurfaceState.GAMEPLAY_MINIMAP
        assert mgr.is_click_through is True
        assert mgr.is_visible is True

        # Marker projection in GAMEPLAY_MINIMAP returns minimap markers
        proj_minimap = mgr.project_markers(sample_markers, player_pos=(100.0, 100.0))
        assert len(proj_minimap) > 0
        assert hasattr(proj_minimap[0], "distance_from_center")

        # 2. Player opens M-key expanded map
        mgr.set_map_open(True)
        assert mgr.state == ActiveSurfaceState.NATIVE_MAP_OPEN
        assert mgr.is_map_open is True
        assert mgr.is_click_through is True

        # Marker projection in NATIVE_MAP_OPEN returns expanded markers
        proj_expanded = mgr.project_markers(sample_markers, player_pos=(100.0, 100.0))
        assert len(proj_expanded) > 0
        assert hasattr(proj_expanded[0], "screen_x")

        # 3. Cutscene or loading screen begins
        mgr.update_from_game_state(GameState.CUTSCENE_OR_DIALOGUE, is_game_running=True)
        assert mgr.state == ActiveSurfaceState.MENU_OR_LOADING
        assert mgr.is_visible is False

        # In MENU_OR_LOADING, projection strictly returns 0 markers
        proj_loading = mgr.project_markers(sample_markers, player_pos=(100.0, 100.0))
        assert len(proj_loading) == 0

        # 4. Game is closed or not running
        mgr.update_from_game_state(GameState.UNKNOWN, is_game_running=False)
        assert mgr.state == ActiveSurfaceState.NO_GAME
        assert mgr.is_click_through is False  # UI becomes interactive for user settings

        # Verify callback history recorded all 4 state transitions
        assert len(transitions) == 4
        assert transitions[0] == (ActiveSurfaceState.NO_GAME, ActiveSurfaceState.GAMEPLAY_MINIMAP)
        assert transitions[1] == (ActiveSurfaceState.GAMEPLAY_MINIMAP, ActiveSurfaceState.NATIVE_MAP_OPEN)
        assert transitions[2] == (ActiveSurfaceState.NATIVE_MAP_OPEN, ActiveSurfaceState.MENU_OR_LOADING)
        assert transitions[3] == (ActiveSurfaceState.MENU_OR_LOADING, ActiveSurfaceState.NO_GAME)

    def test_capture_exclusion_api(self):
        """Verify SetWindowDisplayAffinity capture exclusion call and mock fallback."""
        test_hwnd = 98765

        # Initially not excluded
        assert is_capture_excluded(test_hwnd) is False

        # Enable exclusion
        success = set_capture_exclusion(test_hwnd, exclude=True)
        assert success is True
        assert is_capture_excluded(test_hwnd) is True

        # Disable exclusion
        success_disable = set_capture_exclusion(test_hwnd, exclude=False)
        assert success_disable is True
        assert is_capture_excluded(test_hwnd) is False

        # Invalid HWND fails gracefully
        assert set_capture_exclusion(0, exclude=True) is False
        assert set_capture_exclusion(-1, exclude=True) is False

    def test_global_hotkeys_dispatch(self):
        """Verify registration, dynamic binding, and manual triggering of global hotkeys."""
        listener = GlobalHotkeyListener()

        triggered_keys = []
        listener.register_hotkey(1, VK_F11, MOD_NOREPEAT, callback=lambda: triggered_keys.append("F11"))
        listener.register_hotkey(2, VK_F12, MOD_NOREPEAT, callback=lambda: triggered_keys.append("F12"))

        assert listener.is_registered(1) is True
        assert listener.is_registered(2) is True
        assert listener.is_registered(99) is False

        # Start and stop lifecycle
        listener.start()
        assert listener.is_running is True

        # Trigger hotkey 1 (F11)
        res1 = listener.trigger_hotkey(1)
        assert res1 is True
        assert "F11" in triggered_keys

        # Trigger hotkey 2 (F12)
        res2 = listener.trigger_hotkey(2)
        assert res2 is True
        assert "F12" in triggered_keys

        # Unregister hotkey 1
        unreg_res = listener.unregister_hotkey(1)
        assert unreg_res is True
        assert listener.is_registered(1) is False

        # Triggering unregistered hotkey returns False
        assert listener.trigger_hotkey(1) is False

        listener.stop()
        assert listener.is_running is False

    def test_window_tracker_bounds_detection(self):
        """Verify GameWindowTracker tracking, movement callbacks, and aspect ratio calculation."""
        tracker = GameWindowTracker(poll_interval_s=0.05)

        moved_events = []
        found_events = []
        lost_events = []

        tracker.add_on_moved_callback(lambda rect: moved_events.append(rect))
        tracker.add_on_found_callback(lambda hwnd: found_events.append(hwnd))
        tracker.add_on_lost_callback(lambda: lost_events.append(True))

        # Initial state: Game not found
        rect0 = tracker.poll_once()
        assert rect0.is_found is False

        # Simulate game window opened at 1920x1080
        sim_rect_1 = GameWindowRect(
            x=0,
            y=0,
            width=1920,
            height=1080,
            is_minimized=False,
            is_found=True,
            hwnd=5555,
        )
        tracker.set_mock_rect(sim_rect_1)
        rect1 = tracker.poll_once()

        assert rect1.is_found is True
        assert rect1.hwnd == 5555
        assert pytest.approx(rect1.aspect_ratio, 0.01) == 16.0 / 9.0
        assert len(found_events) == 1
        assert found_events[0] == 5555
        assert len(moved_events) == 1

        # Simulate window moved to secondary monitor at (2560, 100)
        sim_rect_2 = GameWindowRect(
            x=2560,
            y=100,
            width=1920,
            height=1080,
            is_minimized=False,
            is_found=True,
            hwnd=5555,
        )
        tracker.set_mock_rect(sim_rect_2)
        rect2 = tracker.poll_once()
        assert rect2.x == 2560
        assert len(moved_events) == 2

        # Simulate game closed
        sim_rect_closed = GameWindowRect(is_found=False)
        tracker.set_mock_rect(sim_rect_closed)
        rect3 = tracker.poll_once()
        assert rect3.is_found is False
        assert len(lost_events) == 1

    def test_multi_surface_zero_selection_filter(self, sample_markers):
        """Verify strict adherence to zero selection rule across both surfaces."""
        mgr = MultiSurfaceOverlayManager(
            initial_state=ActiveSurfaceState.GAMEPLAY_MINIMAP,
            minimap_circle=MinimapCircle(center_x=100.0, center_y=100.0, radius=50.0),
        )

        # Empty active set returns 0 markers on minimap
        res_minimap = mgr.project_markers(sample_markers, player_pos=(100.0, 100.0), active_ids=set())
        assert len(res_minimap) == 0

        # Switch to expanded map and verify empty set returns 0 markers
        mgr.set_surface_state(ActiveSurfaceState.NATIVE_MAP_OPEN)
        res_expanded = mgr.project_markers(sample_markers, player_pos=(100.0, 100.0), active_ids=set())
        assert len(res_expanded) == 0
