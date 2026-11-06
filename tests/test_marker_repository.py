"""Unit tests for Marker models and MarkerRepository."""

import pytest
from src.markers.models import (
    LayerInfo,
    Marker,
    MarkerCategory,
    MarkerCoordinate,
    MarkerFilter,
    RegionBounds,
    RegionInfo,
)
from src.markers.marker_repository import MarkerRepository, MarkerValidationError


class TestMarkerModels:
    def test_marker_coordinate_distance(self):
        c1 = MarkerCoordinate(0, 0, 0)
        c2 = MarkerCoordinate(3, 4, 12)
        assert c1.distance_to(c2) == 5.0
        assert c1.distance_3d_to(c2) == 13.0

    def test_marker_coordinate_dict_roundtrip(self):
        c = MarkerCoordinate(123.5, -456.2, 78.9)
        d = c.to_dict()
        c2 = MarkerCoordinate.from_dict(d)
        assert c2.x == 123.5
        assert c2.y == -456.2
        assert c2.z == 78.9

    def test_region_bounds_contains(self):
        bounds = RegionBounds(min_x=-100, min_y=-100, max_x=100, max_y=100)
        assert bounds.contains(0, 0) is True
        assert bounds.contains(-100, 100) is True
        assert bounds.contains(101, 0) is False
        assert bounds.contains(0, -101) is False

    def test_marker_filter_matches(self):
        marker = Marker(
            id="m1",
            name="Windrise Anemoculus",
            category_id="anemoculus",
            region_id="mondstadt",
            layer="surface",
            coordinates=MarkerCoordinate(-800, -2200, 10),
            description="High in the tree",
            tags=["tree", "oculi"],
        )

        # Match category
        f_cat_ok = MarkerFilter(categories={"anemoculus"})
        f_cat_bad = MarkerFilter(categories={"geoculus"})
        assert f_cat_ok.matches(marker, False) is True
        assert f_cat_bad.matches(marker, False) is False

        # Match collection status
        f_uncoll = MarkerFilter(collected=False)
        f_coll = MarkerFilter(collected=True)
        assert f_uncoll.matches(marker, False) is True
        assert f_coll.matches(marker, False) is False

        # Match search term (name, description, id, or tag)
        assert MarkerFilter(search="windrise").matches(marker, False) is True
        assert MarkerFilter(search="tree").matches(marker, False) is True
        assert MarkerFilter(search="m1").matches(marker, False) is True
        assert MarkerFilter(search="nonexistent").matches(marker, False) is False

        # Match bounding box
        f_bbox_in = MarkerFilter(bounding_box=(-1000, -2500, -500, -2000))
        f_bbox_out = MarkerFilter(bounding_box=(0, 0, 1000, 1000))
        assert f_bbox_in.matches(marker, False) is True
        assert f_bbox_out.matches(marker, False) is False


class TestMarkerRepository:
    def test_load_from_dict_and_counts(self, sample_markers_dict):
        repo = MarkerRepository()
        count = repo.load_from_json(sample_markers_dict)
        assert count == 4
        assert repo.total_count == 4
        assert len(repo.get_categories()) == 3
        assert len(repo.get_regions()) == 2
        assert len(repo.get_layers()) == 2

    def test_validate_marker_errors(self):
        repo = MarkerRepository()
        # Missing id
        with pytest.raises(MarkerValidationError):
            repo.validate_marker({"name": "Test", "category_id": "anemo", "coordinates": {"x": 0, "y": 0}})

        # Missing name
        with pytest.raises(MarkerValidationError):
            repo.validate_marker({"id": "t1", "category_id": "anemo", "coordinates": {"x": 0, "y": 0}})

        # Missing coordinates
        with pytest.raises(MarkerValidationError):
            repo.validate_marker({"id": "t1", "name": "Test", "category_id": "anemo"})

        # Invalid non-numeric coordinates
        with pytest.raises(MarkerValidationError):
            repo.validate_marker({"id": "t1", "name": "Test", "category_id": "anemo", "coordinates": {"x": "bad", "y": 0}})

    def test_filter_by_region_and_layer(self, sample_repository):
        # Surface markers in Mondstadt
        f = MarkerFilter(regions={"mondstadt"}, layers={"surface"})
        res = sample_repository.filter_markers(f)
        assert len(res) == 2
        assert {m.id for m in res} == {"m1", "m2"}

        # Underground markers
        f_under = MarkerFilter(layers={"underground"})
        res_under = sample_repository.filter_markers(f_under)
        assert len(res_under) == 1
        assert res_under[0].id == "m4"

    def test_count_by_category(self, sample_repository):
        collected = {"m1", "m4"}
        counts = sample_repository.count_by_category(collected)

        assert counts["anemoculus"]["total"] == 1
        assert counts["anemoculus"]["collected"] == 1
        assert counts["anemoculus"]["remaining"] == 0

        assert counts["luxurious_chest"]["total"] == 2
        assert counts["luxurious_chest"]["collected"] == 1
        assert counts["luxurious_chest"]["remaining"] == 1

        assert counts["geoculus"]["total"] == 1
        assert counts["geoculus"]["collected"] == 0
        assert counts["geoculus"]["remaining"] == 1

    def test_get_bounds(self, sample_repository):
        # Specific region bounds from definition
        mond_bounds = sample_repository.get_bounds("mondstadt")
        assert mond_bounds.min_x == -3000
        assert mond_bounds.max_x == 1000

        # Global calculated bounds with padding
        global_bounds = sample_repository.get_bounds()
        assert global_bounds.min_x < -3460
        assert global_bounds.max_x > 182
