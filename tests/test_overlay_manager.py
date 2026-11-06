"""Unit tests for OverlayManager and win32_overlay cross-platform abstraction."""

import pytest
from src.overlay.overlay_manager import OverlayManager, OverlayMode
from src.overlay import win32_overlay


class TestOverlayManager:
    def test_initial_state_expanded(self, overlay_mgr):
        assert overlay_mgr.mode == OverlayMode.EXPANDED
        assert overlay_mgr.is_visible is True
        assert overlay_mgr.is_click_through is False
        assert overlay_mgr.current_alpha == 0.95

        # Check simulated win32 state
        state = win32_overlay.get_mock_state().get_or_create(overlay_mgr.hwnd)
        assert state["click_through"] is False
        assert state["always_on_top"] is True
        assert state["alpha"] == 0.95

    def test_switch_to_compact_enables_click_through(self, overlay_mgr):
        overlay_mgr.set_mode(OverlayMode.COMPACT)
        assert overlay_mgr.mode == OverlayMode.COMPACT
        assert overlay_mgr.is_visible is True
        assert overlay_mgr.is_click_through is True
        assert overlay_mgr.current_alpha == 0.85

        state = win32_overlay.get_mock_state().get_or_create(overlay_mgr.hwnd)
        assert state["click_through"] is True
        assert state["alpha"] == 0.85

    def test_toggle_mode(self, overlay_mgr):
        assert overlay_mgr.mode == OverlayMode.EXPANDED
        mode = overlay_mgr.toggle_mode()
        assert mode == OverlayMode.COMPACT
        mode2 = overlay_mgr.toggle_mode()
        assert mode2 == OverlayMode.EXPANDED

    def test_cycle_mode(self, overlay_mgr):
        # EXPANDED -> HIDDEN -> COMPACT -> EXPANDED
        m1 = overlay_mgr.cycle_mode()
        assert m1 == OverlayMode.HIDDEN
        assert overlay_mgr.is_visible is False

        m2 = overlay_mgr.cycle_mode()
        assert m2 == OverlayMode.COMPACT
        assert overlay_mgr.is_visible is True

        m3 = overlay_mgr.cycle_mode()
        assert m3 == OverlayMode.EXPANDED

    def test_toggle_visibility(self, overlay_mgr):
        assert overlay_mgr.is_visible is True
        vis1 = overlay_mgr.toggle_visibility()
        assert vis1 is False
        assert overlay_mgr.mode == OverlayMode.HIDDEN

        vis2 = overlay_mgr.toggle_visibility()
        assert vis2 is True
        assert overlay_mgr.mode == OverlayMode.EXPANDED

    def test_callbacks_fired(self, overlay_mgr):
        mode_history = []
        vis_history = []

        overlay_mgr.register_mode_callback(lambda m: mode_history.append(m))
        overlay_mgr.register_visibility_callback(lambda v: vis_history.append(v))

        overlay_mgr.set_mode(OverlayMode.COMPACT)
        overlay_mgr.set_mode(OverlayMode.HIDDEN)

        assert mode_history == [OverlayMode.COMPACT, OverlayMode.HIDDEN]
        assert vis_history == [True, False]

    def test_transparency_bounds(self, overlay_mgr):
        overlay_mgr.set_transparency(1.5)  # should clamp to 1.0
        assert overlay_mgr.current_alpha == 1.0

        overlay_mgr.set_transparency(-0.2)  # should clamp to 0.1
        assert overlay_mgr.current_alpha == 0.1

    def test_get_toplevel_hwnd(self):
        # On non-Windows mock or generic handle, returns handle safely without errors
        res = win32_overlay.get_toplevel_hwnd(99999)
        assert res == 99999
