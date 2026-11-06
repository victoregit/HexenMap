"""Map rendering, projection, viewport manipulation, and layer management."""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from src.markers.models import Marker, RegionBounds


@dataclass
class ViewportState:
    """Current state of map camera viewport."""
    center_x: float = 0.0      # World X coordinate at center of viewport
    center_y: float = 0.0      # World Y coordinate at center of viewport
    zoom: float = 0.5          # Pixels per world unit (higher = more zoomed in)
    width: int = 800           # Viewport width in pixels
    height: int = 600          # Viewport height in pixels
    min_zoom: float = 0.05
    max_zoom: float = 5.0
    active_layer: str = "surface"
    active_region: Optional[str] = None


@dataclass
class MarkerRenderItem:
    """Render representation of a marker in viewport space."""
    marker: Marker
    vx: float
    vy: float
    is_collected: bool
    color: str
    radius: float
    label: str
    is_visible: bool


@dataclass
class PlayerRenderItem:
    """Render representation of player position in viewport space."""
    vx: float
    vy: float
    heading: float  # degrees (0 = North, 90 = East)
    confidence: float
    is_valid: bool


class MapRenderer:
    """Engine for projecting world coordinates into screen/viewport space with pan and zoom."""

    def __init__(
        self,
        viewport_width: int = 800,
        viewport_height: int = 600,
        initial_center: Tuple[float, float] = (0.0, 0.0),
        initial_zoom: float = 0.25,
    ) -> None:
        self.state = ViewportState(
            center_x=initial_center[0],
            center_y=initial_center[1],
            zoom=initial_zoom,
            width=viewport_width,
            height=viewport_height,
        )

    def set_viewport_dimensions(self, width: int, height: int) -> None:
        """Update viewport pixel dimensions."""
        self.state.width = max(100, int(width))
        self.state.height = max(100, int(height))

    def world_to_viewport(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates (wx, wy) to screen viewport pixel coordinates (vx, vy).

        World coordinate origin (0, 0) corresponds to viewport center when center_x=0, center_y=0.
        Note: Screen Y goes downwards, while world Y can be positive downwards or upwards.
        In Genshin map conventions, world Y grows downwards or upwards; here we treat standard Cartesian:
        vx = width/2 + (wx - center_x) * zoom
        vy = height/2 + (wy - center_y) * zoom
        """
        vx = (self.state.width / 2.0) + (wx - self.state.center_x) * self.state.zoom
        vy = (self.state.height / 2.0) + (wy - self.state.center_y) * self.state.zoom
        return vx, vy

    def viewport_to_world(self, vx: float, vy: float) -> Tuple[float, float]:
        """Convert screen viewport pixel coordinates (vx, vy) to world coordinates (wx, wy)."""
        wx = self.state.center_x + (vx - self.state.width / 2.0) / self.state.zoom
        wy = self.state.center_y + (vy - self.state.height / 2.0) / self.state.zoom
        return wx, wy

    def pan_by(self, delta_pixel_x: float, delta_pixel_y: float) -> None:
        """Pan map viewport by screen pixel deltas."""
        world_dx = delta_pixel_x / self.state.zoom
        world_dy = delta_pixel_y / self.state.zoom
        self.state.center_x -= world_dx
        self.state.center_y -= world_dy

    def center_on(self, world_x: float, world_y: float) -> None:
        """Center the viewport on a specific world coordinate."""
        self.state.center_x = float(world_x)
        self.state.center_y = float(world_y)

    def set_zoom(self, zoom: float) -> None:
        """Set zoom scale factor clamped to min/max range."""
        self.state.zoom = max(self.state.min_zoom, min(self.state.max_zoom, float(zoom)))

    def zoom_at(self, factor: float, screen_x: float, screen_y: float) -> None:
        """Zoom in or out while keeping the world point under screen_x, screen_y stationary."""
        old_zoom = self.state.zoom
        new_zoom = max(self.state.min_zoom, min(self.state.max_zoom, old_zoom * factor))
        if new_zoom == old_zoom:
            return

        # World coordinate under the mouse before zoom
        world_x, world_y = self.viewport_to_world(screen_x, screen_y)

        # Update zoom
        self.state.zoom = new_zoom

        # Adjust center so world point remains under screen_x, screen_y
        self.state.center_x = world_x - (screen_x - self.state.width / 2.0) / new_zoom
        self.state.center_y = world_y - (screen_y - self.state.height / 2.0) / new_zoom

    def fit_bounds(self, bounds: RegionBounds, padding: float = 40.0) -> None:
        """Adjust center and zoom to fit the specified bounding box inside the viewport."""
        bw = abs(bounds.max_x - bounds.min_x)
        bh = abs(bounds.max_y - bounds.min_y)
        if bw <= 0 or bh <= 0:
            return

        self.state.center_x = (bounds.min_x + bounds.max_x) / 2.0
        self.state.center_y = (bounds.min_y + bounds.max_y) / 2.0

        avail_w = max(100.0, self.state.width - 2 * padding)
        avail_h = max(100.0, self.state.height - 2 * padding)

        zoom_x = avail_w / bw
        zoom_y = avail_h / bh
        fit_zoom = min(zoom_x, zoom_y)
        self.set_zoom(fit_zoom)

    def set_layer(self, layer_id: str) -> None:
        """Switch active layer (e.g., 'surface' vs 'underground')."""
        self.state.active_layer = layer_id

    def set_region(self, region_id: Optional[str]) -> None:
        """Filter by region or None for all."""
        self.state.active_region = region_id

    def prepare_render_list(
        self,
        markers: List[Marker],
        collected_ids: Set[str],
        categories_map: Optional[Dict[str, Any]] = None,
        player_coords: Optional[Tuple[float, float, float]] = None,  # (wx, wy, heading)
    ) -> Dict[str, Any]:
        """Compute pixel render items for visible markers and player indicator.

        Returns dictionary containing:
        - 'markers': list of MarkerRenderItem
        - 'player': Optional[PlayerRenderItem]
        - 'viewport_bounds': (min_wx, min_wy, max_wx, max_wy)
        """
        # Determine world bounds currently in view
        min_wx, min_wy = self.viewport_to_world(0, 0)
        max_wx, max_wy = self.viewport_to_world(self.state.width, self.state.height)
        if min_wx > max_wx:
            min_wx, max_wx = max_wx, min_wx
        if min_wy > max_wy:
            min_wy, max_wy = max_wy, min_wy

        # Margin around viewport to include markers slightly off-screen
        margin = 50.0 / self.state.zoom
        min_wx -= margin
        min_wy -= margin
        max_wx += margin
        max_wy += margin

        render_markers: List[MarkerRenderItem] = []
        for marker in markers:
            # Check layer filter
            if self.state.active_layer and marker.layer != self.state.active_layer:
                continue

            # Check region filter
            if self.state.active_region and marker.region_id != self.state.active_region:
                continue

            mx = marker.coordinates.x
            my = marker.coordinates.y

            # Fast viewport cull
            is_in_bounds = (min_wx <= mx <= max_wx) and (min_wy <= my <= max_wy)
            vx, vy = self.world_to_viewport(mx, my)

            is_collected = marker.id in collected_ids

            # Lookup category color
            color = "#3498db"
            if categories_map and marker.category_id in categories_map:
                cat = categories_map[marker.category_id]
                color = getattr(cat, "color", "#3498db") if not isinstance(cat, dict) else cat.get("color", "#3498db")

            radius = 7.0 if not is_collected else 5.0

            render_markers.append(
                MarkerRenderItem(
                    marker=marker,
                    vx=vx,
                    vy=vy,
                    is_collected=is_collected,
                    color=color,
                    radius=radius,
                    label=marker.name,
                    is_visible=is_in_bounds,
                )
            )

        # Player render item
        player_item = None
        if player_coords:
            px, py, heading = player_coords
            pvx, pvy = self.world_to_viewport(px, py)
            player_item = PlayerRenderItem(
                vx=pvx,
                vy=pvy,
                heading=heading,
                confidence=1.0,
                is_valid=True,
            )

        return {
            "markers": render_markers,
            "player": player_item,
            "viewport_bounds": (min_wx, min_wy, max_wx, max_wy),
        }

    def find_marker_at_screen_pos(
        self,
        screen_x: float,
        screen_y: float,
        markers: List[Marker],
        collected_ids: Set[str],
        tolerance_px: float = 14.0,
    ) -> Optional[Marker]:
        """Find the nearest marker to a click position in screen pixels."""
        closest_marker: Optional[Marker] = None
        min_dist_sq = tolerance_px * tolerance_px

        for marker in markers:
            if self.state.active_layer and marker.layer != self.state.active_layer:
                continue
            if self.state.active_region and marker.region_id != self.state.active_region:
                continue

            vx, vy = self.world_to_viewport(marker.coordinates.x, marker.coordinates.y)
            dist_sq = (vx - screen_x) ** 2 + (vy - screen_y) ** 2
            if dist_sq <= min_dist_sq:
                min_dist_sq = dist_sq
                closest_marker = marker

        return closest_marker

    def get_regional_landmasses(self) -> List[Dict[str, Any]]:
        """Return stylized landmass polygons, colors, and watermark positions for Teyvat regions."""
        return DEFAULT_REGIONAL_LANDMASSES


# Stylized regional geography / landmass definitions for Teyvat continent
DEFAULT_REGIONAL_LANDMASSES: List[Dict[str, Any]] = [
    {
        "id": "mondstadt",
        "name": "MONDSTADT",
        "polygon": [
            (-2700.0, -3600.0), (-1600.0, -3800.0), (-800.0, -3600.0),
            (-200.0, -3200.0), (400.0, -2600.0), (200.0, -1900.0),
            (-300.0, -1500.0), (-800.0, -1300.0), (-1800.0, -1500.0),
            (-2500.0, -2200.0), (-2800.0, -3000.0),
        ],
        "fill": "#17212b",
        "outline": "#273748",
        "label_pos": (-1200.0, -2400.0),
    },
    {
        "id": "cider_lake",
        "name": "",
        "polygon": [
            (-1800.0, -2700.0), (-1400.0, -2800.0), (-1200.0, -2600.0),
            (-1300.0, -2300.0), (-1700.0, -2350.0),
        ],
        "fill": "#121922",
        "outline": "#1e2b3a",
        "label_pos": (-1500.0, -2550.0),
    },
    {
        "id": "dragonspine",
        "name": "DRAGONSPINE",
        "polygon": [
            (-300.0, -300.0), (500.0, -600.0), (1200.0, -200.0),
            (1400.0, 500.0), (1000.0, 1200.0), (300.0, 1100.0),
            (-400.0, 500.0),
        ],
        "fill": "#1b263b",
        "outline": "#3a506b",
        "label_pos": (500.0, 300.0),
    },
    {
        "id": "dragonspine_peak",
        "name": "",
        "polygon": [
            (100.0, -100.0), (600.0, -300.0), (900.0, 200.0),
            (700.0, 700.0), (200.0, 600.0),
        ],
        "fill": "#23344d",
        "outline": "#4d6b8a",
        "label_pos": (500.0, 300.0),
    },
    {
        "id": "liyue",
        "name": "LIYUE",
        "polygon": [
            (-2200.0, 200.0), (-600.0, 100.0), (500.0, 400.0),
            (1600.0, 800.0), (1900.0, 2200.0), (1600.0, 3800.0),
            (800.0, 4400.0), (-500.0, 4200.0), (-1600.0, 3600.0),
            (-2200.0, 2200.0), (-2400.0, 1200.0),
        ],
        "fill": "#23211c",
        "outline": "#413b2e",
        "label_pos": (-200.0, 2300.0),
    },
    {
        "id": "liyue_dihua",
        "name": "",
        "polygon": [
            (-1200.0, 1000.0), (-200.0, 800.0), (600.0, 1400.0),
            (400.0, 2800.0), (-600.0, 3000.0), (-1400.0, 2200.0),
        ],
        "fill": "#29261f",
        "outline": "#4e4635",
        "label_pos": (-300.0, 1800.0),
    },
    {
        "id": "chasm",
        "name": "THE CHASM",
        "polygon": [
            (-4200.0, 2600.0), (-3600.0, 2100.0), (-2600.0, 2300.0),
            (-2200.0, 3200.0), (-2500.0, 4100.0), (-3500.0, 4400.0),
            (-4300.0, 3700.0),
        ],
        "fill": "#261c1c",
        "outline": "#4d3232",
        "label_pos": (-3300.0, 3200.0),
    },
    {
        "id": "chasm_inner",
        "name": "",
        "polygon": [
            (-3800.0, 2800.0), (-3400.0, 2500.0), (-2800.0, 2600.0),
            (-2600.0, 3200.0), (-2800.0, 3800.0), (-3400.0, 4000.0),
            (-3900.0, 3600.0),
        ],
        "fill": "#1c1414",
        "outline": "#5e3838",
        "label_pos": (-3300.0, 3200.0),
    },
]
