"""Unit and integration tests for Marco B: Circular Gameplay Minimap Overlay."""

import math
import os
import cv2
import numpy as np
import pytest

from src.map.minimap_projector import MinimapCircle, MinimapProjector, ProjectedMinimapMarker
from src.markers.models import Marker, MarkerCoordinate


class TestMinimapProjection:
    """Test suite verifying MinimapProjector, circular masking, and relative player projection."""

    @pytest.fixture
    def sample_circle(self) -> MinimapCircle:
        return MinimapCircle(center_x=140.0, center_y=95.0, radius=80.0)

    @pytest.fixture
    def sample_markers(self) -> list[Marker]:
        return [
            Marker(
                id="m_center",
                name="Center Chest",
                category_id="luxurious_chest",
                region_id="dragonspine",
                coordinates=MarkerCoordinate(x=100.0, y=100.0),
            ),
            Marker(
                id="m_east",
                name="East Chest",
                category_id="precious_chest",
                region_id="dragonspine",
                coordinates=MarkerCoordinate(x=150.0, y=100.0),  # +50 world units East
            ),
            Marker(
                id="m_far_north",
                name="Far North Chest",
                category_id="common_chest",
                region_id="dragonspine",
                coordinates=MarkerCoordinate(x=100.0, y=-500.0),  # -600 world units North (far)
            ),
        ]

    def test_circular_masking_strictly_bounds_markers(self, sample_circle, sample_markers):
        """Verify that markers outside circle radius are marked is_inside_circle=False and 0 pixels leak."""
        projector = MinimapProjector(circle=sample_circle)
        # Player at (100, 100)
        projected = projector.project_markers(
            markers=sample_markers,
            player_pos=(100.0, 100.0),
            scale=0.5,
        )

        p_center = next(p for p in projected if p.marker_id == "m_center")
        p_east = next(p for p in projected if p.marker_id == "m_east")
        p_far = next(p for p in projected if p.marker_id == "m_far_north")

        # Center marker: distance 0 px -> inside
        assert p_center.distance_from_center == 0.0
        assert p_center.is_inside_circle is True

        # East marker: +50 * 0.5 = 25 px from center -> inside (25 < 80)
        assert p_east.distance_from_center == 25.0
        assert p_east.is_inside_circle is True

        # Far North marker: -600 * 0.5 = 300 px from center -> outside (300 > 80)
        assert p_far.distance_from_center == 300.0
        assert p_far.is_inside_circle is False

        # Test render_minimap_overlay with zero leakage
        base_img = np.full((200, 280, 3), 40, dtype=np.uint8)
        rendered = projector.render_minimap_overlay(base_img, projected, sample_circle)

        # Calculate difference outside circle
        h, w = base_img.shape[:2]
        y_coords, x_coords = np.ogrid[:h, :w]
        dist_from_c = np.sqrt((x_coords - sample_circle.center_x) ** 2 + (y_coords - sample_circle.center_y) ** 2)
        outside_mask = dist_from_c > sample_circle.radius

        diff = np.abs(rendered.astype(int) - base_img.astype(int))
        outside_diff = diff[outside_mask]
        leaked_pixels = np.count_nonzero(outside_diff.sum(axis=1))

        assert leaked_pixels == 0, f"Expected strictly 0 leaked pixels, got {leaked_pixels}!"

    def test_relative_projection_translates_with_player(self, sample_circle, sample_markers):
        """Verify that moving the player translates relative marker coordinates oppositely."""
        projector = MinimapProjector(circle=sample_circle)
        scale = 1.0

        # Player at (100, 100): marker 'm_center' at (100, 100) is at minimap center (140, 95)
        proj_1 = projector.project_markers(sample_markers, player_pos=(100.0, 100.0), scale=scale)
        m_c1 = next(p for p in proj_1 if p.marker_id == "m_center")
        assert m_c1.screen_x == 140.0
        assert m_c1.screen_y == 95.0

        # Player moves East by +20 units to (120, 100): marker moves West on screen to (120, 95)
        proj_2 = projector.project_markers(sample_markers, player_pos=(120.0, 100.0), scale=scale)
        m_c2 = next(p for p in proj_2 if p.marker_id == "m_center")
        assert m_c2.screen_x == 120.0
        assert m_c2.screen_y == 95.0

        # Player moves North by -15 units to (100, 85): marker moves South on screen to (140, 110)
        proj_3 = projector.project_markers(sample_markers, player_pos=(100.0, 85.0), scale=scale)
        m_c3 = next(p for p in proj_3 if p.marker_id == "m_center")
        assert m_c3.screen_x == 140.0
        assert m_c3.screen_y == 110.0

    def test_rotation_invariance_and_angles(self, sample_circle):
        """Verify rotating minimap by 0°, 90°, 180°, and 270° rotates relative vectors accurately."""
        projector = MinimapProjector(circle=sample_circle)
        # Marker placed directly East of player at (100, 0)
        marker = Marker(
            id="m_east",
            name="East",
            category_id="chest",
            region_id="dragonspine",
            coordinates=MarkerCoordinate(x=100.0, y=0.0),
        )
        player_pos = (0.0, 0.0)
        scale = 0.5  # dx = +100 -> screen delta = +50 px
        cx, cy = sample_circle.center_x, sample_circle.center_y

        # Heading 0° (North-up / facing North): Marker East is at screen +X
        p0 = projector.project_markers([marker], player_pos, player_heading=0.0, minimap_rotation=True, scale=scale)[0]
        assert pytest.approx(p0.screen_x, abs=0.01) == cx + 50.0
        assert pytest.approx(p0.screen_y, abs=0.01) == cy

        # Heading 90° (Facing East): Player looks East, so East marker is directly Ahead (screen -Y)
        p90 = projector.project_markers([marker], player_pos, player_heading=90.0, minimap_rotation=True, scale=scale)[0]
        assert pytest.approx(p90.screen_x, abs=0.01) == cx
        assert pytest.approx(p90.screen_y, abs=0.01) == cy - 50.0

        # Heading 180° (Facing South): East marker is to player's Left (screen -X)
        p180 = projector.project_markers([marker], player_pos, player_heading=180.0, minimap_rotation=True, scale=scale)[0]
        assert pytest.approx(p180.screen_x, abs=0.01) == cx - 50.0
        assert pytest.approx(p180.screen_y, abs=0.01) == cy

        # Heading 270° (Facing West): East marker is directly Behind player (screen +Y)
        p270 = projector.project_markers([marker], player_pos, player_heading=270.0, minimap_rotation=True, scale=scale)[0]
        assert pytest.approx(p270.screen_x, abs=0.01) == cx
        assert pytest.approx(p270.screen_y, abs=0.01) == cy + 50.0

    def test_zero_selected_returns_zero_rendered(self, sample_circle, sample_markers):
        """Verify strict rule: empty list or active_ids=set() returns strictly 0 items."""
        projector = MinimapProjector(circle=sample_circle)

        # Empty marker list
        res_empty = projector.project_markers([], player_pos=(0, 0))
        assert len(res_empty) == 0

        # Non-empty marker list with active_ids set to empty set
        res_zero_filter = projector.project_markers(sample_markers, player_pos=(0, 0), active_ids=set())
        assert len(res_zero_filter) == 0

    def test_circle_detection_on_reference_image(self):
        """Verify automated Hough circle detection on real reference minimap image."""
        ref_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "reference", "02_circular_minimap.png"
        )
        if not os.path.exists(ref_path):
            pytest.skip("Reference image 02_circular_minimap.png not found")

        img = cv2.imread(ref_path)
        assert img is not None

        projector = MinimapProjector()
        detected_circle = projector.detect_minimap_circle(img)

        assert detected_circle is not None
        # Verify detected circle is within reasonable bounds of the image
        assert 80.0 <= detected_circle.center_x <= 160.0
        assert 60.0 <= detected_circle.center_y <= 120.0
        assert 65.0 <= detected_circle.radius <= 90.0
