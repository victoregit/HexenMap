"""Unit and integration tests for Marco A: Georeferenced Expanded Map Projection."""

import numpy as np
import pytest

from src.legacy_app import GenshinOverlayApp
from src.map.expanded_projector import ExpandedMapProjector
from src.map.registration import MapRegistration
from src.markers.models import Marker, MarkerCoordinate


class TestExpandedMapProjection:
    """Test suite verifying MapRegistration, ExpandedMapProjector, and filter contracts."""

    def test_zero_selected_categories_returns_zero_markers(self, tmp_path):
        """Regression test: verify that zero selected categories returns 0 markers, NEVER all."""
        app = GenshinOverlayApp(
            progress_path=str(tmp_path / "progress.json"),
            headless=True,
        )
        assert len(app.repository.get_all_markers()) > 0

        # Normal selection: all categories active
        initial_count = len(app.get_filtered_markers())
        assert initial_count > 0

        # User unchecks all categories (empty set)
        app.selected_categories = set()
        filtered = app.get_filtered_markers()
        assert len(filtered) == 0, "Zero selected categories must strictly return 0 markers!"
        assert len(app.active_marker_ids) == 0

    def test_registration_control_points(self):
        """Verify MapRegistration calibration accuracy with known control points."""
        registration = MapRegistration(max_allowed_error=3.0, min_confidence_threshold=0.80)

        # Ground truth transformation: s = 1.10, theta = 0, tx = 84.0, ty = 81.0
        src_pts = np.array([
            [100.0, 100.0],
            [300.0, 100.0],
            [300.0, 400.0],
            [100.0, 400.0],
            [200.0, 250.0],
        ], dtype=np.float32)

        # Add slight sub-pixel noise (< 0.2 px)
        s_true = 1.10
        tx_true = 84.0
        ty_true = 81.0
        dst_pts = src_pts * s_true + np.array([tx_true, ty_true], dtype=np.float32)
        dst_pts[0] += [0.1, -0.1]
        dst_pts[2] += [-0.1, 0.1]

        result = registration.register_from_control_points(src_pts, dst_pts)
        assert result.is_valid is True
        assert registration.is_calibrated is True
        assert result.mean_reprojection_error < 0.5  # Sub-pixel accuracy
        assert result.confidence >= 0.85
        assert pytest.approx(result.scale, rel=0.01) == s_true
        assert pytest.approx(result.translation[0], abs=1.0) == tx_true
        assert pytest.approx(result.translation[1], abs=1.0) == ty_true

        # Verify forward project and unproject roundtrip
        px, py = registration.project(200.0, 250.0)
        wx, wy = registration.unproject(px, py)
        assert pytest.approx(wx, abs=0.01) == 200.0
        assert pytest.approx(wy, abs=0.01) == 250.0

    def test_projection_pan_and_zoom(self):
        """Verify ExpandedMapProjector applies screen pan and zoom scale accurately."""
        registration = MapRegistration()
        # Identity matrix: 1:1 mapping
        registration.set_transformation_matrix(
            np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ]),
            confidence=1.0,
            mean_error=0.0,
        )

        projector = ExpandedMapProjector(
            registration=registration,
            viewport_width=1000,
            viewport_height=800,
            initial_pan=(0.0, 0.0),
            initial_zoom=1.0,
        )

        marker = Marker(
            id="test_chest_01",
            name="Test Chest",
            category_id="luxurious_chest",
            region_id="dragonspine",
            coordinates=MarkerCoordinate(x=500.0, y=400.0),  # Viewport center
        )

        # 1. At center with zoom=1.0, pan=(0, 0): screen pos should be (500, 400)
        items = projector.project_markers([marker])
        assert len(items) == 1
        assert items[0].screen_x == 500.0
        assert items[0].screen_y == 400.0

        # 2. Pan right by +50 px, down by -30 px
        projector.set_pan(50.0, -30.0)
        items_panned = projector.project_markers([marker])
        assert items_panned[0].screen_x == 550.0
        assert items_panned[0].screen_y == 370.0

        # 3. Zoom 2.0x on a marker away from center: (600, 400) -> dx=+100 -> new x = 500 + 100*2 = 700
        marker_offset = Marker(
            id="test_chest_02",
            name="Offset Chest",
            category_id="common_chest",
            region_id="dragonspine",
            coordinates=MarkerCoordinate(x=600.0, y=400.0),
        )
        projector.set_pan(0.0, 0.0)
        projector.set_zoom(2.0)
        items_zoomed = projector.project_markers([marker_offset])
        assert pytest.approx(items_zoomed[0].screen_x, 0.01) == 700.0
        assert pytest.approx(items_zoomed[0].screen_y, 0.01) == 400.0

    def test_rejection_on_invalid_registration(self):
        """Verify strict safety constraint: uncalibrated registration rejects projection."""
        registration = MapRegistration(max_allowed_error=1.0, min_confidence_threshold=0.70)
        # 4 points with heavy distortion such that inlier ratio < 70%
        src_bad = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]], dtype=np.float32)
        dst_bad = np.array([[0.0, 0.0], [100.0, 50.0], [-50.0, 200.0], [300.0, -100.0]], dtype=np.float32)

        res = registration.register_from_control_points(src_bad, dst_bad, max_error_thresh=1.0)
        assert res.is_valid is False
        assert registration.is_calibrated is False

        # Attempt to project via projector
        projector = ExpandedMapProjector(registration=registration)
        marker = Marker(
            id="test_chest",
            name="Test",
            category_id="chest",
            region_id="dragonspine",
            coordinates=MarkerCoordinate(x=10.0, y=10.0),
        )
        projected = projector.project_markers([marker])
        assert len(projected) == 0, "Uncalibrated registration must return 0 markers to avoid hallucinations!"

    def test_frustum_culling(self):
        """Verify markers outside viewport bounds are flagged as not visible."""
        registration = MapRegistration()
        registration.set_transformation_matrix(
            np.eye(3)[:2],
            confidence=1.0,
            mean_error=0.0,
        )
        projector = ExpandedMapProjector(
            registration=registration,
            viewport_width=800,
            viewport_height=600,
        )

        in_marker = Marker(
            id="in", name="In", category_id="c", region_id="r",
            coordinates=MarkerCoordinate(x=400, y=300),
        )
        out_marker = Marker(
            id="out", name="Out", category_id="c", region_id="r",
            coordinates=MarkerCoordinate(x=5000, y=5000),
        )

        items = projector.project_markers([in_marker, out_marker])
        item_in = next(i for i in items if i.marker_id == "in")
        item_out = next(i for i in items if i.marker_id == "out")

        assert item_in.is_visible is True
        assert item_out.is_visible is False
