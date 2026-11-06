"""Integration tests for GenshinOverlayApp end-to-end execution."""

import os
import pytest
from src.legacy_app import GenshinOverlayApp
from src.overlay.overlay_manager import OverlayMode


class TestAppIntegration:
    @pytest.fixture
    def app_instance(self, tmp_path):
        progress_file = str(tmp_path / "app_progress.json")
        app = GenshinOverlayApp(
            data_path=None,  # Defaults to data/demo_markers.json
            progress_path=progress_file,
            initial_mode=OverlayMode.EXPANDED,
            headless=True,
            demo_mode=True,
        )
        return app

    def test_app_initialization(self, app_instance):
        assert app_instance.repository.total_count == 50
        assert app_instance.progress.collected_count == 0
        assert app_instance.overlay_mgr.mode == OverlayMode.EXPANDED

    def test_app_headless_run_cycle(self, app_instance):
        # Run 5 simulated cycles
        app_instance.run_headless(iterations=5)

        # Performance monitor should have recorded cv, render, query timings
        all_stats = app_instance.perf_monitor.get_all_stats()
        assert all_stats["cv_ms"]["count"] >= 5
        assert all_stats["render_ms"]["count"] >= 5
        assert all_stats["query_ms"]["count"] >= 5

        # Some markers should have been marked collected in the headless loop
        assert app_instance.progress.collected_count > 0

    def test_app_filtering_workflow(self, app_instance):
        # 1. Total unfiltered markers
        all_markers = app_instance.get_filtered_markers()
        # In demo dataset, surface markers on default layer 'surface'
        assert len(all_markers) > 0

        # 2. Filter by search query "Windrise"
        app_instance.search_query = "Windrise"
        filtered = app_instance.get_filtered_markers()
        assert len(filtered) >= 2
        for m in filtered:
            assert "windrise" in m.name.lower() or "windrise" in m.description.lower() or any("windrise" in t.lower() for t in m.tags)

        # 3. Filter by underground layer
        app_instance.search_query = ""
        app_instance.selected_layer = "underground"
        underground_markers = app_instance.get_filtered_markers()
        assert len(underground_markers) > 0
        for m in underground_markers:
            assert m.layer == "underground"

    def test_nearest_marker_and_collection_toggle(self, app_instance):
        # Player at Windrise coordinates (-820, -2210)
        nearest_info = app_instance.find_nearest_marker(-820.0, -2210.0)
        assert nearest_info is not None
        nearest_marker, dist = nearest_info
        assert dist < 10.0  # Windrise statue/oculus is within a few meters

        # Toggle marker as collected
        app_instance.toggle_marker_collected(nearest_marker.id)
        assert app_instance.progress.is_collected(nearest_marker.id) is True

        # Now finding nearest should find a DIFFERENT marker or at greater distance
        next_nearest_info = app_instance.find_nearest_marker(-820.0, -2210.0)
        assert next_nearest_info is not None
        next_marker, _ = next_nearest_info
        assert next_marker.id != nearest_marker.id

    def test_export_and_reimport_workflow(self, app_instance, tmp_path):
        app_instance.progress.mark_collected("mond_statue_windrise")
        app_instance.progress.mark_collected("liyue_statue_dihua")

        export_file = str(tmp_path / "exported_progress.json")
        app_instance.progress.export_to_json(export_file)

        # Fresh app
        new_progress = str(tmp_path / "fresh_app_progress.json")
        fresh_app = GenshinOverlayApp(
            progress_path=new_progress,
            headless=True,
        )
        assert fresh_app.progress.collected_count == 0

        imported = fresh_app.progress.import_from_json(export_file)
        assert imported == 2
        assert fresh_app.progress.is_collected("mond_statue_windrise") is True
        assert fresh_app.progress.is_collected("liyue_statue_dihua") is True

    def test_update_gui_layout_for_mode_no_name_error(self, app_instance):
        """Regression test ensuring _update_gui_layout_for_mode does not raise NameError for tk."""
        from unittest.mock import MagicMock
        from src.overlay.overlay_manager import OverlayMode

        # Set up mock GUI widgets on app_instance
        app_instance.root = MagicMock()
        app_instance.top_bar = MagicMock()
        app_instance.workspace = MagicMock()
        app_instance.compact_hud = MagicMock()
        app_instance.redraw_map = MagicMock()

        # Test switching across all modes: COMPACT, EXPANDED, HIDDEN
        # None of these should raise NameError (e.g. name 'tk' is not defined)
        app_instance._update_gui_layout_for_mode(OverlayMode.COMPACT)
        app_instance.compact_hud.pack.assert_called_once()
        app_instance.root.geometry.assert_called_with("420x48+20+20")

        app_instance._update_gui_layout_for_mode(OverlayMode.EXPANDED)
        app_instance.top_bar.pack.assert_called()
        app_instance.workspace.pack.assert_called()
        app_instance.redraw_map.assert_called_once()

        app_instance._update_gui_layout_for_mode(OverlayMode.HIDDEN)
        app_instance.root.withdraw.assert_called_once()

        # Also verify no-op if root is None
        app_instance.root = None
        app_instance._update_gui_layout_for_mode(OverlayMode.COMPACT)

    def test_schedule_gui_tick(self, app_instance):
        """Verify that _schedule_gui_tick triggers map redrawing in simulated mode and reschedules."""
        from unittest.mock import MagicMock
        app_instance.root = MagicMock()
        app_instance.redraw_map = MagicMock()
        app_instance.is_running = True
        app_instance.tracking_mode = "simulated"

        app_instance._schedule_gui_tick()
        app_instance.redraw_map.assert_called_once()
        app_instance.root.after.assert_called_once_with(100, app_instance._schedule_gui_tick)

    def test_tracking_mode_switch_and_center(self, app_instance):
        """Verify tracking mode switching, auto-center toggle, and center on player."""
        from unittest.mock import MagicMock
        app_instance.root = MagicMock()
        app_instance.redraw_map = MagicMock()

        # Switch to live_cv
        app_instance.set_tracking_mode("live_cv")
        assert app_instance.tracking_mode == "live_cv"

        # Switch back to simulated
        app_instance.set_tracking_mode("simulated")
        assert app_instance.tracking_mode == "simulated"

        # Center on player
        old_cx = app_instance.renderer.state.center_x
        app_instance.center_on_player()
        assert app_instance.renderer.state.center_x is not None

        # Toggle auto-center
        prev_auto = app_instance.auto_center
        app_instance.toggle_auto_center()
        assert app_instance.auto_center == (not prev_auto)
        app_instance.toggle_auto_center()
        assert app_instance.auto_center == prev_auto


