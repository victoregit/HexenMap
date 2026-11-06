"""Repository for loading, indexing, validating, and querying markers."""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.markers.models import (
    LayerInfo,
    Marker,
    MarkerCategory,
    MarkerFilter,
    RegionBounds,
    RegionInfo,
)


class MarkerValidationError(ValueError):
    """Raised when marker data fails validation."""
    pass


class MarkerRepository:
    """In-memory repository for fast spatial and categorical marker lookups."""

    def __init__(self) -> None:
        self._markers: Dict[str, Marker] = {}
        self._categories: Dict[str, MarkerCategory] = {}
        self._regions: Dict[str, RegionInfo] = {}
        self._layers: Dict[str, LayerInfo] = {}
        self._source_version: str = "1.0.0"
        self._metadata: Dict[str, Any] = {}

    @property
    def total_count(self) -> int:
        return len(self._markers)

    @property
    def version(self) -> str:
        return self._source_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def validate_marker(self, data: Dict[str, Any]) -> None:
        """Validate marker dictionary against schema requirements.

        Raises:
            MarkerValidationError: If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            raise MarkerValidationError("Marker data must be a dictionary")

        if "id" not in data or not str(data["id"]).strip():
            raise MarkerValidationError("Marker missing required non-empty 'id'")

        if "name" not in data or not str(data["name"]).strip():
            raise MarkerValidationError(f"Marker '{data.get('id')}' missing required 'name'")

        if "category_id" not in data or not str(data["category_id"]).strip():
            raise MarkerValidationError(f"Marker '{data.get('id')}' missing required 'category_id'")

        if "coordinates" not in data:
            raise MarkerValidationError(f"Marker '{data.get('id')}' missing required 'coordinates'")

        coords = data["coordinates"]
        if isinstance(coords, dict):
            if "x" not in coords or "y" not in coords:
                raise MarkerValidationError(f"Coordinates for '{data.get('id')}' must contain 'x' and 'y'")
            try:
                float(coords["x"])
                float(coords["y"])
                if "z" in coords:
                    float(coords["z"])
            except (ValueError, TypeError) as exc:
                raise MarkerValidationError(f"Coordinates for '{data.get('id')}' must be numeric") from exc
        elif isinstance(coords, (list, tuple)):
            if len(coords) < 2:
                raise MarkerValidationError(f"Coordinates list for '{data.get('id')}' must have at least 2 items")
            try:
                float(coords[0])
                float(coords[1])
            except (ValueError, TypeError) as exc:
                raise MarkerValidationError(f"Coordinates for '{data.get('id')}' must be numeric") from exc
        else:
            raise MarkerValidationError(f"Invalid coordinates format for marker '{data.get('id')}'")

    def load_from_json(self, source: Union[str, os.PathLike, Dict[str, Any]]) -> int:
        """Load and index markers from a JSON file path or a dictionary.

        Returns:
            Number of successfully loaded markers.
        """
        if isinstance(source, (str, os.PathLike)):
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError("Source must be a file path or dictionary")

        self._source_version = data.get("version", "1.0.0")
        self._metadata = data.get("metadata", {})

        # Load layers
        for layer_data in data.get("layers", []):
            layer = LayerInfo.from_dict(layer_data)
            self._layers[layer.id] = layer

        # Load categories
        for cat_data in data.get("categories", []):
            cat = MarkerCategory.from_dict(cat_data)
            self._categories[cat.id] = cat

        # Load regions
        for reg_data in data.get("regions", []):
            reg = RegionInfo.from_dict(reg_data)
            self._regions[reg.id] = reg

        # Load markers
        loaded_count = 0
        for marker_data in data.get("markers", []):
            self.validate_marker(marker_data)
            marker = Marker.from_dict(marker_data)
            self._markers[marker.id] = marker
            loaded_count += 1

        return loaded_count

    def add_marker(self, marker: Marker) -> None:
        """Add or update a single marker."""
        self._markers[marker.id] = marker

    def get_marker(self, marker_id: str) -> Optional[Marker]:
        """Retrieve marker by ID."""
        return self._markers.get(marker_id)

    def get_all_markers(self) -> List[Marker]:
        """Return all indexed markers."""
        return list(self._markers.values())

    def get_categories(self) -> Dict[str, MarkerCategory]:
        """Return registered categories mapping."""
        return dict(self._categories)

    def get_regions(self) -> Dict[str, RegionInfo]:
        """Return registered regions mapping."""
        return dict(self._regions)

    def get_layers(self) -> Dict[str, LayerInfo]:
        """Return registered layers mapping."""
        return dict(self._layers)

    def filter_markers(
        self,
        marker_filter: Optional[MarkerFilter] = None,
        collected_ids: Optional[Set[str]] = None,
    ) -> List[Marker]:
        """Query markers matching filter criteria and collection status.

        Args:
            marker_filter: MarkerFilter specification or None to return all.
            collected_ids: Set of marker IDs already marked as collected.

        Returns:
            List of matching Marker instances.
        """
        if collected_ids is None:
            collected_ids = set()

        if marker_filter is None:
            return list(self._markers.values())

        results: List[Marker] = []
        for marker in self._markers.values():
            is_collected = marker.id in collected_ids
            if marker_filter.matches(marker, is_collected):
                results.append(marker)
        return results

    def count_by_category(self, collected_ids: Optional[Set[str]] = None) -> Dict[str, Dict[str, int]]:
        """Count total and collected markers per category.

        Returns:
            Dict mapping category_id to {"total": int, "collected": int, "remaining": int}
        """
        if collected_ids is None:
            collected_ids = set()

        counts: Dict[str, Dict[str, int]] = {}
        # Pre-populate all known categories
        for cat_id in self._categories:
            counts[cat_id] = {"total": 0, "collected": 0, "remaining": 0}

        for marker in self._markers.values():
            cat = marker.category_id
            if cat not in counts:
                counts[cat] = {"total": 0, "collected": 0, "remaining": 0}
            counts[cat]["total"] += 1
            if marker.id in collected_ids:
                counts[cat]["collected"] += 1

        for data in counts.values():
            data["remaining"] = data["total"] - data["collected"]

        return counts

    def get_bounds(self, region_id: Optional[str] = None) -> RegionBounds:
        """Calculate bounding box for all markers or within a specific region."""
        if region_id and region_id in self._regions and self._regions[region_id].bounds:
            return self._regions[region_id].bounds

        markers = [m for m in self._markers.values() if not region_id or m.region_id == region_id]
        if not markers:
            return RegionBounds(min_x=-1000.0, min_y=-1000.0, max_x=1000.0, max_y=1000.0)

        min_x = min(m.coordinates.x for m in markers)
        min_y = min(m.coordinates.y for m in markers)
        max_x = max(m.coordinates.x for m in markers)
        max_y = max(m.coordinates.y for m in markers)

        # Add slight padding
        padding_x = max(50.0, (max_x - min_x) * 0.05)
        padding_y = max(50.0, (max_y - min_y) * 0.05)

        return RegionBounds(
            min_x=min_x - padding_x,
            min_y=min_y - padding_y,
            max_x=max_x + padding_x,
            max_y=max_y + padding_y,
        )

    def clear(self) -> None:
        """Clear all stored data."""
        self._markers.clear()
        self._categories.clear()
        self._regions.clear()
        self._layers.clear()
        self._metadata.clear()
