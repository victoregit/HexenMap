"""Expanded Map Projector for Native In-Game Map (M-Key).

Projects georeferenced markers onto the native game map interface, maintaining
alignment under map panning and zooming without drawing a redundant synthetic canvas.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from src.map.registration import MapRegistration
from src.markers.models import Marker


@dataclass
class ProjectedMarkerItem:
    """Representation of an exploration marker projected onto screen pixel coordinates."""
    marker_id: str
    name: str
    category_id: str
    layer: str
    screen_x: float
    screen_y: float
    is_visible: bool
    color: str = "#f3c75f"
    radius: float = 14.0
    label: str = ""


class ExpandedMapProjector:
    """Engine for projecting world markers onto native Genshin expanded map coordinates."""

    def __init__(
        self,
        registration: MapRegistration,
        viewport_width: int = 1359,
        viewport_height: int = 729,
        initial_pan: Tuple[float, float] = (0.0, 0.0),
        initial_zoom: float = 1.0,
    ) -> None:
        self.registration = registration
        self.viewport_width = max(100, int(viewport_width))
        self.viewport_height = max(100, int(viewport_height))
        self.pan_x = float(initial_pan[0])
        self.pan_y = float(initial_pan[1])
        self.zoom_scale = max(0.1, min(10.0, float(initial_zoom)))

    def set_viewport_size(self, width: int, height: int) -> None:
        """Update viewport screen bounds."""
        self.viewport_width = max(100, int(width))
        self.viewport_height = max(100, int(height))

    def set_pan(self, pan_x: float, pan_y: float) -> None:
        """Set native map translation pan offset in screen pixels."""
        self.pan_x = float(pan_x)
        self.pan_y = float(pan_y)

    def set_zoom(self, zoom: float) -> None:
        """Set native map zoom multiplier clamped to reasonable bounds."""
        self.zoom_scale = max(0.1, min(10.0, float(zoom)))

    def project_markers(
        self,
        markers: List[Marker],
        active_ids: Optional[Set[str]] = None,
        cull_margin: float = 30.0,
    ) -> List[ProjectedMarkerItem]:
        """Project candidate markers into screen pixel coordinates.

        Strict Safety Constraint: If registration is not calibrated or has insufficient
        confidence, returns an empty list to avoid rendering displaced/hallucinated markers.

        Args:
            markers: List of candidate markers.
            active_ids: Explicit set of active marker IDs (single source of truth).
            cull_margin: Pixel margin around screen viewport bounds.

        Returns:
            List of ProjectedMarkerItem instances with screen positions.
        """
        # Rejection criteria: if registration is invalid, do not project markers!
        if not self.registration.is_calibrated:
            return []

        # If active_ids is explicitly an empty set, return zero markers
        if active_ids is not None and len(active_ids) == 0:
            return []

        cx = self.viewport_width / 2.0
        cy = self.viewport_height / 2.0
        results: List[ProjectedMarkerItem] = []

        for m in markers:
            # Filter by active marker IDs if specified
            if active_ids is not None and m.id not in active_ids:
                continue

            try:
                base_px, base_py = self.registration.project(m.coordinates.x, m.coordinates.y)
            except ValueError:
                continue

            # Apply game pan and zoom relative to viewport center
            dx = base_px - cx
            dy = base_py - cy
            sx = cx + dx * self.zoom_scale + self.pan_x
            sy = cy + dy * self.zoom_scale + self.pan_y

            # Frustum culling with safety margin
            in_bounds = (
                -cull_margin <= sx <= (self.viewport_width + cull_margin)
                and -cull_margin <= sy <= (self.viewport_height + cull_margin)
            )

            # Resolve category color
            color = "#f3c75f"
            cat_lower = m.category_id.lower()
            if "luxurious" in cat_lower:
                color = "#f1c40f"
            elif "precious" in cat_lower:
                color = "#e67e22"
            elif "exquisite" in cat_lower:
                color = "#3498db"
            elif "common" in cat_lower:
                color = "#95a5a6"
            elif "anemo" in cat_lower or "geo" in cat_lower or "oculus" in cat_lower:
                color = "#6fe7c8"
            elif "statue" in cat_lower or "waypoint" in cat_lower:
                color = "#4da6ff"

            results.append(
                ProjectedMarkerItem(
                    marker_id=m.id,
                    name=m.name,
                    category_id=m.category_id,
                    layer=m.layer,
                    screen_x=float(sx),
                    screen_y=float(sy),
                    is_visible=in_bounds,
                    color=color,
                    radius=14.0 * min(1.5, max(0.7, self.zoom_scale)),
                    label=m.name,
                )
            )

        return results

    def render_overlay_frame(
        self,
        base_image: np.ndarray,
        projected_markers: List[ProjectedMarkerItem],
    ) -> np.ndarray:
        """Render high-contrast, georeferenced chest pins directly onto the game screenshot.

        Ensures the underlying game landscape remains visible without synthetic backgrounds.

        Args:
            base_image: Native in-game screenshot BGR or BGRA numpy array.
            projected_markers: List of ProjectedMarkerItem instances.

        Returns:
            New image array with overlay markers rendered.
        """
        output = base_image.copy()
        h, w = output.shape[:2]

        for item in projected_markers:
            if not item.is_visible:
                continue

            ix = int(round(item.screen_x))
            iy = int(round(item.screen_y))
            if not (0 <= ix < w and 0 <= iy < h):
                continue

            r = int(round(item.radius))

            # Parse hex color to BGR
            hex_c = item.color.lstrip("#")
            if len(hex_c) == 6:
                r_val = int(hex_c[0:2], 16)
                g_val = int(hex_c[2:4], 16)
                b_val = int(hex_c[4:6], 16)
                bgr = (b_val, g_val, r_val)
            else:
                bgr = (95, 199, 243)

            if cv2 is not None:
                # 1. Outer dark drop shadow for contrast against snow
                cv2.circle(output, (ix + 1, iy + 2), r + 2, (15, 15, 20), -1)

                # 2. Glowing outer halo
                cv2.circle(output, (ix, iy), r + 2, (255, 255, 255), 2)

                # 3. Vibrant filled pin circle
                cv2.circle(output, (ix, iy), r, bgr, -1)

                # 4. Inner chest graphic accent (stylized chest latch/band)
                inner_r = max(3, r // 2)
                cv2.circle(output, (ix, iy), inner_r, (25, 25, 30), -1)
                cv2.circle(output, (ix, iy), max(1, inner_r - 2), (255, 255, 255), -1)

                # 5. Top latch line
                cv2.line(output, (ix - r + 3, iy), (ix + r - 3, iy), (25, 25, 30), 2)
            else:
                # Pure numpy fallback placeholder if cv2 not loaded
                y1 = max(0, iy - r)
                y2 = min(h, iy + r + 1)
                x1 = max(0, ix - r)
                x2 = min(w, ix + r + 1)
                output[y1:y2, x1:x2] = bgr

        return output
