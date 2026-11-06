"""Multi-scale regional reference tile manager for minimap computer vision tracking.

Indexes and retrieves calibrated terrain tiles across Teyvat regions (Dragonspine,
Mondstadt, Liyue, Chasm) with spatial bounding queries, scale pyramids, and in-memory caching.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)


@dataclass
class ReferenceTile:
    """A georeferenced map terrain tile at a specific scale pyramid level."""
    tile_id: str
    region_id: str
    bounds: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    scale_level: int = 1
    image_path: Optional[str] = None
    width: int = 256
    height: int = 256

    def intersects(self, query_bounds: Tuple[float, float, float, float]) -> bool:
        """Check if query bounds (min_x, min_y, max_x, max_y) overlap this tile."""
        q_min_x, q_min_y, q_max_x, q_max_y = query_bounds
        t_min_x, t_min_y, t_max_x, t_max_y = self.bounds
        return not (
            q_max_x < t_min_x
            or q_min_x > t_max_x
            or q_max_y < t_min_y
            or q_min_y > t_max_y
        )

    def contains_point(self, x: float, y: float) -> bool:
        t_min_x, t_min_y, t_max_x, t_max_y = self.bounds
        return t_min_x <= x <= t_max_x and t_min_y <= y <= t_max_y


class ReferenceTileManager:
    """Manages multi-scale reference tiles with spatial indexing and LRU tile cache."""

    def __init__(self, cache_max_tiles: int = 64) -> None:
        self.cache_max_tiles = cache_max_tiles
        self._tiles: Dict[str, ReferenceTile] = {}
        self._tile_cache: Dict[str, np.ndarray] = {}
        self._initialize_default_regional_tiles()

    def _initialize_default_regional_tiles(self) -> None:
        """Register default known regions and Dragonspine calibrated tile definitions."""
        # Dragonspine reference region: ~ [400, 1000] to [1200, 1800]
        self.add_tile(
            ReferenceTile(
                tile_id="dragonspine_center_s1",
                region_id="dragonspine",
                bounds=(400.0, 1000.0, 1200.0, 1800.0),
                scale_level=1,
                image_path=os.path.join("data", "reference", "dragonspine_terrain_s1.png"),
            )
        )
        # Mondstadt Windrise & City region
        self.add_tile(
            ReferenceTile(
                tile_id="mondstadt_windrise_s1",
                region_id="mondstadt",
                bounds=(-500.0, -500.0, 500.0, 500.0),
                scale_level=1,
            )
        )
        # Liyue Harbor & Plains
        self.add_tile(
            ReferenceTile(
                tile_id="liyue_harbor_s1",
                region_id="liyue",
                bounds=(500.0, -1500.0, 1800.0, -200.0),
                scale_level=1,
            )
        )

    def add_tile(self, tile: ReferenceTile) -> None:
        """Register a reference tile in the spatial index."""
        self._tiles[tile.tile_id] = tile

    def get_tile(self, tile_id: str) -> Optional[ReferenceTile]:
        """Retrieve tile metadata by identifier."""
        return self._tiles.get(tile_id)

    def get_tiles_for_region(self, region_id: str, scale_level: Optional[int] = None) -> List[ReferenceTile]:
        """Query all registered tiles belonging to a specific region and optional scale."""
        results = [
            t for t in self._tiles.values()
            if t.region_id == region_id and (scale_level is None or t.scale_level == scale_level)
        ]
        return results

    def get_tiles_for_bounds(
        self,
        bounds: Tuple[float, float, float, float],
        scale_level: Optional[int] = None,
    ) -> List[ReferenceTile]:
        """Retrieve all tiles overlapping the specified bounding box (min_x, min_y, max_x, max_y)."""
        return [
            t for t in self._tiles.values()
            if t.intersects(bounds) and (scale_level is None or t.scale_level == scale_level)
        ]

    def get_tile_image(self, tile: ReferenceTile) -> np.ndarray:
        """Fetch image matrix for a tile from disk or in-memory cache, generating synthetic fallback if missing."""
        if tile.tile_id in self._tile_cache:
            return self._tile_cache[tile.tile_id]

        img: Optional[np.ndarray] = None
        if tile.image_path and os.path.exists(tile.image_path) and cv2 is not None:
            try:
                img = cv2.imread(tile.image_path)
            except Exception as e:
                logger.debug("Failed reading tile %s from %s: %s", tile.tile_id, tile.image_path, e)

        # Procedural fallback generator if image file not on disk
        if img is None:
            img = self._generate_procedural_tile(tile)

        # Cache management
        if len(self._tile_cache) >= self.cache_max_tiles:
            # Drop oldest tile
            oldest_key = next(iter(self._tile_cache))
            del self._tile_cache[oldest_key]

        self._tile_cache[tile.tile_id] = img
        return img

    def _generate_procedural_tile(self, tile: ReferenceTile) -> np.ndarray:
        """Generate a procedural mock terrain image for testing and simulation."""
        h, w = tile.height, tile.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Region-specific base colors
        if tile.region_id == "dragonspine":
            img[:, :] = (230, 220, 210)  # Snow blue-white
        elif tile.region_id == "liyue":
            img[:, :] = (90, 140, 160)   # Mountain ochre
        else:
            img[:, :] = (80, 150, 90)    # Mondstadt green

        # Add mock elevation grid
        step = max(16, w // 8)
        img[::step, :] = (60, 60, 60)
        img[:, ::step] = (60, 60, 60)

        return img

    def clear_cache(self) -> None:
        """Clear cached image textures."""
        self._tile_cache.clear()
