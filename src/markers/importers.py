"""Dataset importers with provenance verification and schema validation.

Supports standard GeoJSON and Community JSON formats, enforcing provenance metadata,
license compatibility checks (CC-BY, MIT, ODbL), and coordinate sanity checks.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from src.markers.models import Marker, MarkerCoordinate

logger = logging.getLogger(__name__)

# Permitted open/community licenses
COMPATIBLE_LICENSES: Set[str] = {
    "mit",
    "cc0",
    "cc-by",
    "cc-by-4.0",
    "cc-by-sa",
    "cc-by-sa-4.0",
    "odbl",
    "apache-2.0",
    "public-domain",
    "custom-permissive",
}


@dataclass
class DatasetProvenance:
    """Provenance and licensing metadata for marker datasets."""
    name: str
    source_url: str = ""
    license_type: str = "Unknown"
    attribution: str = ""
    version: str = "1.0.0"
    is_license_compatible: bool = False
    verified_at: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        norm_license = self.license_type.strip().lower()
        self.is_license_compatible = any(
            lic in norm_license for lic in COMPATIBLE_LICENSES
        )
        if not self.verified_at:
            self.verified_at = time.strftime("%Y-%m-%d")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_url": self.source_url,
            "license_type": self.license_type,
            "attribution": self.attribution,
            "version": self.version,
            "is_license_compatible": self.is_license_compatible,
            "verified_at": self.verified_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatasetProvenance:
        return cls(
            name=str(data.get("name", "Unknown Dataset")),
            source_url=str(data.get("source_url", "")),
            license_type=str(data.get("license_type", "Unknown")),
            attribution=str(data.get("attribution", "")),
            version=str(data.get("version", "1.0.0")),
            is_license_compatible=bool(data.get("is_license_compatible", False)),
            verified_at=data.get("verified_at"),
            notes=str(data.get("notes", "")),
        )


class BaseMarkerImporter(ABC):
    """Abstract contract for marker dataset importers."""

    @abstractmethod
    def import_markers(self, raw_data: str | bytes | Dict[str, Any]) -> Tuple[List[Marker], DatasetProvenance]:
        """Parse raw dataset content and return validated markers and provenance."""
        pass

    def validate_marker(self, marker: Marker) -> bool:
        """Validate marker attributes and coordinate sanity."""
        if not marker.id or not isinstance(marker.id, str):
            return False
        if not marker.name:
            return False
        if not marker.coordinates:
            return False

        # Coordinate numerical sanity check
        x, y, z = marker.coordinates.x, marker.coordinates.y, marker.coordinates.z
        if math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y):
            return False
        if math.isnan(z) or math.isinf(z):
            return False

        # Teyvat coordinate bounds sanity check (-20,000 to +20,000)
        if abs(x) > 20000.0 or abs(y) > 20000.0:
            return False

        return True


class GeoJSONMarkerImporter(BaseMarkerImporter):
    """Importer for standard RFC 7946 GeoJSON FeatureCollections."""

    def import_markers(self, raw_data: str | bytes | Dict[str, Any]) -> Tuple[List[Marker], DatasetProvenance]:
        if isinstance(raw_data, (str, bytes)):
            data = json.loads(raw_data)
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
            raise TypeError(f"Unsupported data type for GeoJSON import: {type(raw_data)}")

        if data.get("type") != "FeatureCollection":
            raise ValueError(f"Expected GeoJSON FeatureCollection, got {data.get('type')}")

        # Extract provenance from top-level metadata
        prov_dict = data.get("provenance") or data.get("properties") or {}
        provenance = DatasetProvenance(
            name=prov_dict.get("name", "GeoJSON Dataset"),
            source_url=prov_dict.get("source_url", ""),
            license_type=prov_dict.get("license", prov_dict.get("license_type", "CC-BY-4.0")),
            attribution=prov_dict.get("attribution", "Open Community"),
            version=prov_dict.get("version", "1.0.0"),
            notes=prov_dict.get("notes", "GeoJSON RFC 7946 format"),
        )

        features = data.get("features", [])
        markers: List[Marker] = []

        for idx, feat in enumerate(features):
            geom = feat.get("geometry") or {}
            if geom.get("type") != "Point":
                continue

            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue

            x = float(coords[0])
            y = float(coords[1])
            z = float(coords[2]) if len(coords) > 2 else 0.0

            props = feat.get("properties") or {}
            marker_id = str(props.get("id") or feat.get("id") or f"geojson_m_{idx}")
            name = str(props.get("name") or f"Marker {marker_id}")
            category_id = str(props.get("category_id") or props.get("category") or "default")
            region_id = str(props.get("region_id") or props.get("region") or "teyvat")
            layer = str(props.get("layer") or "surface")
            description = str(props.get("description") or "")
            tags = [str(t) for t in props.get("tags", [])]

            marker = Marker(
                id=marker_id,
                name=name,
                category_id=category_id,
                region_id=region_id,
                layer=layer,
                coordinates=MarkerCoordinate(x=x, y=y, z=z),
                description=description,
                tags=tags,
            )

            if self.validate_marker(marker):
                markers.append(marker)
            else:
                logger.warning("Rejected invalid marker in GeoJSON: %s", marker_id)

        return markers, provenance


class CommunityJSONMarkerImporter(BaseMarkerImporter):
    """Importer for community JSON marker formats (e.g., Kongying Tavern or Yuanshen map export)."""

    def import_markers(self, raw_data: str | bytes | Dict[str, Any]) -> Tuple[List[Marker], DatasetProvenance]:
        if isinstance(raw_data, (str, bytes)):
            data = json.loads(raw_data)
        elif isinstance(raw_data, dict):
            data = raw_data
        elif isinstance(raw_data, list):
            data = {"markers": raw_data}
        else:
            raise TypeError(f"Unsupported data type for Community JSON import: {type(raw_data)}")

        prov_dict = data.get("provenance") or data.get("metadata") or {}
        provenance = DatasetProvenance(
            name=prov_dict.get("name", "Community Dataset"),
            source_url=prov_dict.get("source_url", ""),
            license_type=prov_dict.get("license", prov_dict.get("license_type", "MIT")),
            attribution=prov_dict.get("attribution", "Community Contributors"),
            version=prov_dict.get("version", "1.0.0"),
            notes=prov_dict.get("notes", "Community JSON schema"),
        )

        raw_markers = data.get("markers") or data.get("data") or []
        markers: List[Marker] = []

        for idx, item in enumerate(raw_markers):
            if not isinstance(item, dict):
                continue

            # Coordinate extraction
            c_data = item.get("coordinates") or item.get("position") or item.get("coords")
            if isinstance(c_data, dict):
                x = float(c_data.get("x", 0.0))
                y = float(c_data.get("y", 0.0))
                z = float(c_data.get("z", 0.0))
            elif isinstance(c_data, (list, tuple)) and len(c_data) >= 2:
                x = float(c_data[0])
                y = float(c_data[1])
                z = float(c_data[2]) if len(c_data) > 2 else 0.0
            else:
                x = float(item.get("x", 0.0))
                y = float(item.get("y", 0.0))
                z = float(item.get("z", 0.0))

            marker_id = str(item.get("id") or f"comm_m_{idx}")
            name = str(item.get("name") or f"Marker {marker_id}")
            category_id = str(item.get("category_id") or item.get("category") or "default")
            region_id = str(item.get("region_id") or item.get("region") or "teyvat")
            layer = str(item.get("layer") or "surface")
            description = str(item.get("description") or "")
            tags = [str(t) for t in item.get("tags", [])]

            marker = Marker(
                id=marker_id,
                name=name,
                category_id=category_id,
                region_id=region_id,
                layer=layer,
                coordinates=MarkerCoordinate(x=x, y=y, z=z),
                description=description,
                tags=tags,
            )

            if self.validate_marker(marker):
                markers.append(marker)
            else:
                logger.warning("Rejected invalid marker in Community JSON: %s", marker_id)

        return markers, provenance
