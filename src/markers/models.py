"""Data models for markers, categories, regions, layers, and filters."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(slots=True)
class MarkerCoordinate:
    """3D Coordinate in Teyvat world space."""
    x: float
    y: float
    z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarkerCoordinate:
        return cls(
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
        )

    def distance_to(self, other: MarkerCoordinate) -> float:
        """Euclidean distance in 2D (x, y) space."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def distance_3d_to(self, other: MarkerCoordinate) -> float:
        """Euclidean distance in 3D (x, y, z) space."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2) ** 0.5


@dataclass(slots=True)
class MarkerCategory:
    """Category classification for a marker."""
    id: str
    name: str
    group: str = "General"
    color: str = "#3498db"
    icon: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "group": self.group,
            "color": self.color,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarkerCategory:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            group=str(data.get("group", "General")),
            color=str(data.get("color", "#3498db")),
            icon=str(data.get("icon", "default")),
        )


@dataclass(slots=True)
class RegionBounds:
    """Bounding box for a region in world coordinates."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegionBounds:
        return cls(
            min_x=float(data["min_x"]),
            min_y=float(data["min_y"]),
            max_x=float(data["max_x"]),
            max_y=float(data["max_y"]),
        )


@dataclass(slots=True)
class RegionInfo:
    """Region metadata."""
    id: str
    name: str
    bounds: Optional[RegionBounds] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"id": self.id, "name": self.name}
        if self.bounds:
            result["bounds"] = self.bounds.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegionInfo:
        bounds = None
        if "bounds" in data and data["bounds"]:
            bounds = RegionBounds.from_dict(data["bounds"])
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            bounds=bounds,
        )


@dataclass(slots=True)
class LayerInfo:
    """Layer definition (e.g., surface, underground)."""
    id: str
    name: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayerInfo:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            description=str(data.get("description", "")),
        )


@dataclass(slots=True)
class Marker:
    """Exploration item or point of interest in the game world."""
    id: str
    name: str
    category_id: str
    region_id: str
    layer: str = "surface"
    coordinates: MarkerCoordinate = field(default_factory=lambda: MarkerCoordinate(0, 0, 0))
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "region_id": self.region_id,
            "layer": self.layer,
            "coordinates": self.coordinates.to_dict(),
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Marker:
        coords = data.get("coordinates", {})
        if isinstance(coords, dict):
            coordinate = MarkerCoordinate.from_dict(coords)
        elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
            coordinate = MarkerCoordinate(x=float(coords[0]), y=float(coords[1]), z=float(coords[2]) if len(coords) > 2 else 0.0)
        else:
            coordinate = MarkerCoordinate(0, 0, 0)

        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            category_id=str(data.get("category_id", "default")),
            region_id=str(data.get("region_id", "unknown")),
            layer=str(data.get("layer", "surface")),
            coordinates=coordinate,
            description=str(data.get("description", "")),
            tags=[str(t) for t in data.get("tags", [])],
        )


@dataclass(slots=True)
class MarkerFilter:
    """Filter criteria for marker queries."""
    categories: Optional[Set[str]] = None
    regions: Optional[Set[str]] = None
    layers: Optional[Set[str]] = None
    collected: Optional[bool] = None  # None = both, True = only collected, False = only uncollected
    search: Optional[str] = None
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (min_x, min_y, max_x, max_y)
    tags: Optional[Set[str]] = None

    def matches(self, marker: Marker, is_collected: bool) -> bool:
        """Check if a marker satisfies all specified filter conditions."""
        if self.categories is not None and marker.category_id not in self.categories:
            return False
        if self.regions is not None and marker.region_id not in self.regions:
            return False
        if self.layers is not None and marker.layer not in self.layers:
            return False
        if self.collected is not None and is_collected != self.collected:
            return False
        if self.bounding_box is not None:
            min_x, min_y, max_x, max_y = self.bounding_box
            if not (min_x <= marker.coordinates.x <= max_x and min_y <= marker.coordinates.y <= max_y):
                return False
        if self.search:
            s = self.search.lower().strip()
            if not (
                s in marker.name.lower()
                or s in marker.description.lower()
                or s in marker.id.lower()
                or any(s in tag.lower() for tag in marker.tags)
            ):
                return False
        if self.tags is not None and not any(tag in self.tags for tag in marker.tags):
            return False
        return True
