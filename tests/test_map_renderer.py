"""Unit tests for MapRenderer coordinate transformations, viewport panning, and rendering."""

import pytest
from src.map.map_renderer import MapRenderer, MarkerRenderItem, PlayerRenderItem
from src.markers.models import Marker, MarkerCoordinate, RegionBounds


class TestMapRenderer:
    def test_world_to_viewport_and_back(self, map_renderer):
        # Viewport width=800, height=600, center=(0, 0), zoom=1.0
        # World (0, 0) should be at screen (400, 300)
        vx, vy = map_renderer.world_to_viewport(0, 0)
        assert vx == 400.0
        assert vy == 300.0

        # Screen (400, 300) should project back to (0, 0)
        wx, wy = map_renderer.viewport_to_world(400, 300)
        assert wx == 0.0
        assert wy == 0.0

        # Arbitrary coordinate
        wx_test, wy_test = 150.0, -220.0
        vx, vy = map_renderer.world_to_viewport(wx_test, wy_test)
        wx_back, wy_back = map_renderer.viewport_to_world(vx, vy)
        assert pytest.approx(wx_back, 0.001) == wx_test
        assert pytest.approx(wy_back, 0.001) == wy_test

    def test_pan_by(self, map_renderer):
        # Pan by 100 pixels in X and 50 in Y
        # Panning right moves the camera right, so world center increases or decreases appropriately
        old_cx = map_renderer.state.center_x
        map_renderer.pan_by(100, 0)
        # Pan by +100 screen px moves viewport left relative to world
        assert map_renderer.state.center_x < old_cx

    def test_zoom_clamping_and_zoom_at(self, map_renderer):
        # Test minimum and maximum zoom clamps
        map_renderer.set_zoom(0.001)
        assert map_renderer.state.zoom == map_renderer.state.min_zoom

        map_renderer.set_zoom(100.0)
        assert map_renderer.state.zoom == map_renderer.state.max_zoom

        # Zoom at specific screen point keeps that point stationary
        map_renderer.set_zoom(1.0)
        map_renderer.center_on(0, 0)

        screen_x, screen_y = 500.0, 350.0
        wx_before, wy_before = map_renderer.viewport_to_world(screen_x, screen_y)

        map_renderer.zoom_at(2.0, screen_x, screen_y)
        wx_after, wy_after = map_renderer.viewport_to_world(screen_x, screen_y)

        assert pytest.approx(wx_before, 0.001) == wx_after
        assert pytest.approx(wy_before, 0.001) == wy_after

    def test_fit_bounds(self, map_renderer):
        bounds = RegionBounds(min_x=-1000, min_y=-1000, max_x=1000, max_y=1000)
        map_renderer.fit_bounds(bounds, padding=0.0)

        # Center should be midway (0, 0)
        assert map_renderer.state.center_x == 0.0
        assert map_renderer.state.center_y == 0.0

        # Viewport is 800x600, bound is 2000x2000
        # Zoom should be min(800/2000, 600/2000) = 0.3
        assert pytest.approx(map_renderer.state.zoom, 0.01) == 0.3

    def test_prepare_render_list(self, map_renderer, sample_repository):
        markers = sample_repository.get_all_markers()
        collected = {"m1"}
        cats_map = sample_repository.get_categories()

        # Render for surface layer
        map_renderer.set_layer("surface")
        result = map_renderer.prepare_render_list(
            markers=markers,
            collected_ids=collected,
            categories_map=cats_map,
            player_coords=(0.0, 0.0, 90.0),
        )

        assert "markers" in result
        assert "player" in result
        # Should include surface markers m1, m2, m3, but exclude m4 (underground)
        rendered_marker_ids = {item.marker.id for item in result["markers"]}
        assert "m1" in rendered_marker_ids
        assert "m2" in rendered_marker_ids
        assert "m3" in rendered_marker_ids
        assert "m4" not in rendered_marker_ids

        # Check collected status reflection
        m1_item = next(item for item in result["markers"] if item.marker.id == "m1")
        assert m1_item.is_collected is True

        # Player item
        p_item = result["player"]
        assert p_item is not None
        assert p_item.heading == 90.0

    def test_find_marker_at_screen_pos(self, map_renderer, sample_repository):
        markers = sample_repository.get_all_markers()
        # Move viewport center onto m1 (-820, -2210)
        map_renderer.center_on(-820.0, -2210.0)
        # World (-820, -2210) should now be at center (400, 300)
        found = map_renderer.find_marker_at_screen_pos(400.0, 300.0, markers, set(), tolerance_px=10.0)
        assert found is not None
        assert found.id == "m1"

        # Far away position returns None
        not_found = map_renderer.find_marker_at_screen_pos(50.0, 50.0, markers, set(), tolerance_px=5.0)
        assert not_found is None

    def test_regional_landmasses(self, map_renderer):
        landmasses = map_renderer.get_regional_landmasses()
        assert len(landmasses) >= 4
        region_ids = [lm["id"] for lm in landmasses]
        assert "mondstadt" in region_ids
        assert "dragonspine" in region_ids
        assert "liyue" in region_ids
        assert "chasm" in region_ids
        for lm in landmasses:
            assert len(lm["polygon"]) >= 3
            assert "fill" in lm
            assert "outline" in lm

