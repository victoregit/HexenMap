"""Unit and integration tests for Marco D: Continuous Tracking & Real Datasets."""

import json
import math
import pytest
from typing import Dict, List

from src.markers.importers import (
    BaseMarkerImporter,
    CommunityJSONMarkerImporter,
    DatasetProvenance,
    GeoJSONMarkerImporter,
)
from src.markers.models import Marker, MarkerCoordinate
from src.tracking.base import PositionEstimate
from src.tracking.reference_tile_manager import ReferenceTile, ReferenceTileManager
from src.tracking.smooth_tracker import ConfidenceGatedTracker, SmoothedPositionTracker
from src.legacy_app import GenshinOverlayApp


class TestDatasetImporters:
    """Tests for dataset provenance and format importers."""

    def test_dataset_provenance_license_compatibility(self):
        """Verify license compatibility validation for open and permissive licenses."""
        prov_mit = DatasetProvenance(name="Open Map", license_type="MIT")
        assert prov_mit.is_license_compatible is True

        prov_ccby = DatasetProvenance(name="CC Map", license_type="CC-BY-4.0")
        assert prov_ccby.is_license_compatible is True

        prov_cc0 = DatasetProvenance(name="Public Domain", license_type="CC0-1.0")
        assert prov_cc0.is_license_compatible is True

        prov_odbl = DatasetProvenance(name="ODbL Data", license_type="ODbL-1.0")
        assert prov_odbl.is_license_compatible is True

        prov_prop = DatasetProvenance(name="Closed Data", license_type="Proprietary-All-Rights-Reserved")
        assert prov_prop.is_license_compatible is False

        # Serialization roundtrip
        d = prov_ccby.to_dict()
        restored = DatasetProvenance.from_dict(d)
        assert restored.name == prov_ccby.name
        assert restored.license_type == prov_ccby.license_type
        assert restored.is_license_compatible is True

    def test_geojson_importer_valid_collection(self):
        """Verify RFC 7946 GeoJSON FeatureCollection parsing."""
        raw_geojson = {
            "type": "FeatureCollection",
            "provenance": {
                "name": "Dragonspine Georeferenced Chests",
                "license": "CC-BY-4.0",
                "attribution": "Genshin Gem Wish Community",
                "version": "2.1.0",
            },
            "features": [
                {
                    "type": "Feature",
                    "id": "ds_chest_001",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [820.5, 1240.2, 150.0],
                    },
                    "properties": {
                        "name": "Frostbearing Precious Chest",
                        "category_id": "precious_chest",
                        "region_id": "dragonspine",
                        "layer": "surface",
                        "description": "Buried in snow near waypoint",
                        "tags": ["snow", "dragonspine"],
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [750.0, 1120.0],
                    },
                    "properties": {
                        "id": "ds_chest_002",
                        "name": "Subterranean Cavern Chest",
                        "category_id": "luxurious_chest",
                        "region_id": "dragonspine",
                        "layer": "underground",
                    },
                },
            ],
        }

        importer = GeoJSONMarkerImporter()
        markers, provenance = importer.import_markers(raw_geojson)

        assert len(markers) == 2
        assert provenance.name == "Dragonspine Georeferenced Chests"
        assert provenance.is_license_compatible is True

        m1 = markers[0]
        assert m1.id == "ds_chest_001"
        assert m1.coordinates.x == 820.5
        assert m1.coordinates.y == 1240.2
        assert m1.coordinates.z == 150.0
        assert m1.category_id == "precious_chest"
        assert m1.region_id == "dragonspine"
        assert m1.layer == "surface"

        m2 = markers[1]
        assert m2.id == "ds_chest_002"
        assert m2.layer == "underground"
        assert m2.coordinates.z == 0.0

    def test_geojson_importer_rejects_invalid_geometries(self):
        """Verify that non-Point features or out-of-bound coords are discarded."""
        invalid_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 0], [10, 10]],
                    },
                    "properties": {"name": "Invalid Geometry"},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [9999999.0, 0.0],  # Out of Teyvat bounds
                    },
                    "properties": {"name": "Out of Bounds"},
                },
            ],
        }

        importer = GeoJSONMarkerImporter()
        markers, _ = importer.import_markers(invalid_geojson)
        assert len(markers) == 0

    def test_community_json_importer(self):
        """Verify Community JSON format parsing with coordinate dictionaries."""
        comm_data = {
            "metadata": {
                "name": "Mondstadt Anemoculi",
                "license": "MIT",
                "attribution": "Community Project",
            },
            "markers": [
                {
                    "id": "ane_01",
                    "name": "Starfell Lake Anemoculus",
                    "category": "anemoculus",
                    "region": "mondstadt",
                    "position": {"x": 250.0, "y": -400.0, "z": 20.0},
                    "tags": ["oculus", "anemo"],
                },
                {
                    "id": "ane_02",
                    "name": "Windrise Tree Anemoculus",
                    "category": "anemoculus",
                    "region": "mondstadt",
                    "position": [180.0, -120.0],
                },
            ],
        }

        importer = CommunityJSONMarkerImporter()
        markers, provenance = importer.import_markers(comm_data)

        assert len(markers) == 2
        assert provenance.name == "Mondstadt Anemoculi"
        assert provenance.is_license_compatible is True

        assert markers[0].id == "ane_01"
        assert markers[0].coordinates.x == 250.0
        assert markers[0].category_id == "anemoculus"

        assert markers[1].id == "ane_02"
        assert markers[1].coordinates.x == 180.0
        assert markers[1].coordinates.y == -120.0


class TestContinuousTracking:
    """Tests for continuous position smoothing, circular statistics, and confidence gating."""

    def test_coordinate_exponential_moving_average(self):
        """Verify coordinate EMA convergence towards a step function input."""
        smoother = SmoothedPositionTracker(alpha=0.5, angle_alpha=0.5)

        # Initial estimate at (0, 0)
        e0 = smoother.update(PositionEstimate(x=0.0, y=0.0, confidence=1.0, is_valid=True))
        assert e0.x == 0.0
        assert e0.y == 0.0

        # Step input to (100, 100)
        # t=1: 0.5 * 100 + 0.5 * 0 = 50.0
        e1 = smoother.update(PositionEstimate(x=100.0, y=100.0, confidence=1.0, is_valid=True))
        assert pytest.approx(e1.x, abs=0.01) == 50.0
        assert pytest.approx(e1.y, abs=0.01) == 50.0

        # t=2: 0.5 * 100 + 0.5 * 50 = 75.0
        e2 = smoother.update(PositionEstimate(x=100.0, y=100.0, confidence=1.0, is_valid=True))
        assert pytest.approx(e2.x, abs=0.01) == 75.0
        assert pytest.approx(e2.y, abs=0.01) == 75.0

    def test_circular_statistics_heading_smoothing(self):
        """Verify circular heading smoothing across the 359° <-> 1° angular discontinuity.

        Crucial Requirement: When heading alternates around North (e.g., 358° and 2°),
        the smoothed angle must remain within [350°, 360°) or [0°, 10°],
        and MUST NOT swing through South (180°)!
        """
        smoother = SmoothedPositionTracker(alpha=0.5, angle_alpha=0.5)

        # First reading: 358° (2° West of North)
        e0 = smoother.update(PositionEstimate(x=0.0, y=0.0, heading_degrees=358.0, is_valid=True))
        assert pytest.approx(e0.heading_degrees, abs=0.1) == 358.0

        # Second reading: 2° (2° East of North)
        # Average of 358° and 2° in circular statistics is 0° (North), NOT 180°!
        e1 = smoother.update(PositionEstimate(x=0.0, y=0.0, heading_degrees=2.0, is_valid=True))
        # Distance from 0° (or 360°) should be within 1.0 degree
        diff_from_north = min(e1.heading_degrees, 360.0 - e1.heading_degrees)
        assert diff_from_north <= 1.0, f"Circular heading failed! Got {e1.heading_degrees}°"

    def test_confidence_gated_tracker_rejection(self):
        """Verify strict confidence gate: rejects < 60% confidence to eliminate point jitter."""
        gate = ConfidenceGatedTracker(min_confidence=0.60)

        # Reading with 85% confidence -> Accepted
        good_est = PositionEstimate(x=50.0, y=50.0, confidence=0.85, is_valid=True)
        res_good = gate.process(good_est)
        assert res_good.is_valid is True
        assert res_good.x == 50.0
        assert gate.accepted_count == 1
        assert gate.rejected_count == 0

        # Reading with 45% confidence -> Rejected (< 0.60)
        noisy_est = PositionEstimate(x=999.0, y=999.0, confidence=0.45, is_valid=True)
        res_noisy = gate.process(noisy_est)
        assert res_noisy.is_valid is False
        assert gate.accepted_count == 1
        assert gate.rejected_count == 1

        # Reading with 59.9% confidence -> Rejected
        borderline_low = PositionEstimate(x=100.0, y=100.0, confidence=0.599, is_valid=True)
        assert gate.process(borderline_low).is_valid is False
        assert gate.rejected_count == 2

        # Reading with 60.0% confidence -> Accepted
        borderline_accept = PositionEstimate(x=60.0, y=60.0, confidence=0.60, is_valid=True)
        assert gate.process(borderline_accept).is_valid is True
        assert gate.accepted_count == 2


class TestReferenceTileManager:
    """Tests for multi-scale regional reference tile indexing and retrieval."""

    def test_tile_indexing_and_bounds_query(self):
        """Verify spatial queries for reference tiles."""
        mgr = ReferenceTileManager()

        # Query region
        ds_tiles = mgr.get_tiles_for_region("dragonspine")
        assert len(ds_tiles) >= 1
        assert ds_tiles[0].region_id == "dragonspine"

        # Query bounds: area overlapping Dragonspine bounds (400, 1000, 1200, 1800)
        query_overlap = (600.0, 1100.0, 700.0, 1200.0)
        matched_tiles = mgr.get_tiles_for_bounds(query_overlap)
        assert any(t.region_id == "dragonspine" for t in matched_tiles)

        # Query bounds completely outside known regions
        query_far = (50000.0, 50000.0, 60000.0, 60000.0)
        matched_far = mgr.get_tiles_for_bounds(query_far)
        assert len(matched_far) == 0

    def test_procedural_fallback_tile_generation(self):
        """Verify that requesting tile images generates procedural textures without crash."""
        mgr = ReferenceTileManager()
        tile = mgr.get_tile("dragonspine_center_s1")
        assert tile is not None

        img = mgr.get_tile_image(tile)
        assert img is not None
        assert img.shape == (256, 256, 3)

        # Verify caching returns same matrix
        img_cached = mgr.get_tile_image(tile)
        assert img_cached is img


class TestAppDatasetIntegration:
    """Integration test for App dataset loading with provenance."""

    def test_load_dataset_with_provenance(self, tmp_path):
        """Verify app loading verified GeoJSON with provenance tracking."""
        geojson_file = tmp_path / "dragonspine_chests.geojson"
        data = {
            "type": "FeatureCollection",
            "provenance": {
                "name": "Verified Dragonspine Chests",
                "license": "CC-BY-4.0",
                "attribution": "Community Cartographers",
                "version": "1.2.0",
            },
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [850.0, 1300.0, 20.0]},
                    "properties": {
                        "id": "ds_prov_01",
                        "name": "Summit Chest",
                        "category_id": "luxurious_chest",
                        "region_id": "dragonspine",
                    },
                }
            ],
        }
        geojson_file.write_text(json.dumps(data))

        app = GenshinOverlayApp(
            progress_path=str(tmp_path / "progress.json"),
            headless=True,
        )

        count, provenance = app.load_dataset_with_provenance(str(geojson_file))
        assert count == 1
        assert provenance.name == "Verified Dragonspine Chests"
        assert provenance.license_type == "CC-BY-4.0"
        assert provenance.is_license_compatible is True

        # Verify marker added to repository
        marker = app.repository.get_marker("ds_prov_01")
        assert marker is not None
        assert marker.name == "Summit Chest"
