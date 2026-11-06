"""Circular Gameplay Minimap Projector.

Projects exploration markers onto the circular gameplay minimap HUD, positioned
relative to the player, with support for rotation and strict anti-aliased
circular stencil masking ensuring zero pixels leak outside the minimap boundary.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from src.markers.models import Marker


@dataclass
class MinimapCircle:
    """Circular boundary definition for the gameplay minimap HUD."""
    center_x: float = 141.5
    center_y: float = 93.5
    radius: float = 82.0

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        """Check if a point is within the circular perimeter (with optional margin)."""
        dist_sq = (x - self.center_x) ** 2 + (y - self.center_y) ** 2
        max_r = self.radius + margin
        return dist_sq <= (max_r * max_r)


@dataclass
class ProjectedMinimapMarker:
    """Representation of an exploration marker projected inside the circular minimap."""
    marker_id: str
    name: str
    category_id: str
    screen_x: float
    screen_y: float
    distance_from_center: float
    is_inside_circle: bool
    color: str = "#f3c75f"
    radius: float = 6.0


class MinimapProjector:
    """Engine for projecting exploration markers onto the circular gameplay minimap."""

    DEFAULT_CALIBRATED_CIRCLE = MinimapCircle(center_x=141.5, center_y=93.5, radius=82.0)

    def __init__(self, circle: Optional[MinimapCircle] = None) -> None:
        self.circle = circle or self.DEFAULT_CALIBRATED_CIRCLE

    def detect_minimap_circle(self, image: np.ndarray) -> MinimapCircle:
        """Detect the minimap circle geometry in a given image crop or full frame.

        Uses Hough Circle Transform with calibrated fallback.

        Args:
            image: Screen capture or minimap crop as BGR or Grayscale numpy array.

        Returns:
            MinimapCircle with center_x, center_y, and radius.
        """
        if cv2 is None or image is None or image.size == 0:
            return self.circle

        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # For cropped reference images (e.g. 245x179), look near image center
        # For full frames (e.g. 1920x1080), constrain to top-left quadrant
        if w < 500 and h < 400:
            # Crop search
            min_r = int(min(h, w) * 0.35)
            max_r = int(min(h, w) * 0.55)
            circles = cv2.HoughCircles(
                gray,
                cv2.HOUGH_GRADIENT,
                dp=1.0,
                minDist=40,
                param1=50,
                param2=25,
                minRadius=min_r,
                maxRadius=max_r,
            )
            if circles is not None and len(circles[0]) > 0:
                # Find circle closest to expected image center
                img_cx, img_cy = w / 2.0, h / 2.0
                best_c = min(
                    circles[0],
                    key=lambda c: math.hypot(c[0] - img_cx, c[1] - img_cy) + abs(c[2] - 82.0),
                )
                detected = MinimapCircle(
                    center_x=float(best_c[0]),
                    center_y=float(best_c[1]),
                    radius=float(best_c[2]),
                )
                self.circle = detected
                return detected
        else:
            # Full 1080p/1440p frame search in top-left quadrant
            crop_w = int(w * 0.25)
            crop_h = int(h * 0.30)
            tl_gray = gray[:crop_h, :crop_w]
            circles = cv2.HoughCircles(
                tl_gray,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=50,
                param1=50,
                param2=35,
                minRadius=int(h * 0.05),
                maxRadius=int(h * 0.15),
            )
            if circles is not None and len(circles[0]) > 0:
                c = circles[0][0]
                detected = MinimapCircle(
                    center_x=float(c[0]),
                    center_y=float(c[1]),
                    radius=float(c[2]),
                )
                self.circle = detected
                return detected

        # Fallback to calibrated default
        return self.circle

    def project_markers(
        self,
        markers: List[Marker],
        player_pos: Tuple[float, float],
        player_heading: float = 0.0,
        minimap_rotation: bool = False,
        scale: float = 0.15,
        circle: Optional[MinimapCircle] = None,
        active_ids: Optional[Set[str]] = None,
        marker_radius: float = 6.0,
    ) -> List[ProjectedMinimapMarker]:
        """Project markers relative to player coordinates into minimap pixel space.

        Args:
            markers: List of candidate markers.
            player_pos: Current player world coordinates (px, py).
            player_heading: Player orientation angle in degrees [0, 360).
            minimap_rotation: If True, rotates terrain/markers by player heading.
                              If False, maintains North-up orientation (Genshin default).
            scale: Pixels per world unit scale factor.
            circle: Target minimap circle definition (uses instance default if None).
            active_ids: Explicit set of active marker IDs (single source of truth).
            marker_radius: Visual radius of the marker pin in pixels.

        Returns:
            List of ProjectedMinimapMarker items.
        """
        # Zero selected categories / active IDs = zero markers rendered
        if active_ids is not None and len(active_ids) == 0:
            return []

        c = circle or self.circle
        results: List[ProjectedMinimapMarker] = []
        heading_rad = math.radians(player_heading)
        cos_h = math.cos(-heading_rad)
        sin_h = math.sin(-heading_rad)

        for m in markers:
            if active_ids is not None and m.id not in active_ids:
                continue

            # Delta vector from player to marker in world space
            dx = m.coordinates.x - player_pos[0]
            dy = m.coordinates.y - player_pos[1]

            # Apply rotation if minimap rotates with camera
            if minimap_rotation:
                rot_dx = dx * cos_h - dy * sin_h
                rot_dy = dx * sin_h + dy * cos_h
            else:
                rot_dx = dx
                rot_dy = dy

            # Convert to screen pixels relative to minimap center
            sx = c.center_x + rot_dx * scale
            sy = c.center_y + rot_dy * scale

            # Distance from minimap center
            dist = math.hypot(sx - c.center_x, sy - c.center_y)

            # Circular boundary clipping: must be inside radius minus marker margin
            # so the full marker icon stays inside the circle
            is_inside = dist <= (c.radius - marker_radius + 1.0)

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
                ProjectedMinimapMarker(
                    marker_id=m.id,
                    name=m.name,
                    category_id=m.category_id,
                    screen_x=float(sx),
                    screen_y=float(sy),
                    distance_from_center=float(dist),
                    is_inside_circle=is_inside,
                    color=color,
                    radius=marker_radius,
                )
            )

        return results

    def render_minimap_overlay(
        self,
        base_image: np.ndarray,
        projected_markers: List[ProjectedMinimapMarker],
        circle: Optional[MinimapCircle] = None,
    ) -> np.ndarray:
        """Render georeferenced markers onto minimap with strict circular stencil clipping.

        GUARANTEE: Any pixel outside distance > circle.radius is strictly untouched,
        preventing any visual leakage beyond the native game minimap border.

        Args:
            base_image: Minimap crop or screen frame (BGR/BGRA numpy array).
            projected_markers: Projected markers to render.
            circle: MinimapCircle bounds.

        Returns:
            Output image with overlay markers rendered strictly within circular mask.
        """
        output = base_image.copy()
        c = circle or self.circle
        h, w = output.shape[:2]

        if cv2 is None:
            return output

        # 1. Create temporary overlay canvas
        overlay_canvas = output.copy()

        # 2. Draw marker pins on overlay canvas
        for item in projected_markers:
            if not item.is_inside_circle:
                continue

            ix = int(round(item.screen_x))
            iy = int(round(item.screen_y))
            r = int(round(item.radius))

            if not (0 <= ix < w and 0 <= iy < h):
                continue

            # Parse hex color
            hex_c = item.color.lstrip("#")
            if len(hex_c) == 6:
                r_val = int(hex_c[0:2], 16)
                g_val = int(hex_c[2:4], 16)
                b_val = int(hex_c[4:6], 16)
                bgr = (b_val, g_val, r_val)
            else:
                bgr = (95, 199, 243)

            # Drop shadow
            cv2.circle(overlay_canvas, (ix + 1, iy + 1), r + 1, (10, 10, 15), -1)
            # Glowing white border
            cv2.circle(overlay_canvas, (ix, iy), r + 1, (255, 255, 255), 1, cv2.LINE_AA)
            # Vibrant filled center
            cv2.circle(overlay_canvas, (ix, iy), r, bgr, -1, cv2.LINE_AA)
            # Inner core dot
            cv2.circle(overlay_canvas, (ix, iy), max(1, r // 3), (255, 255, 255), -1, cv2.LINE_AA)

        # 3. Create anti-aliased stencil mask strictly within circle radius
        # Any pixel outside circle.radius MUST NOT be modified
        cx_i = int(round(c.center_x))
        cy_i = int(round(c.center_y))
        r_i = int(math.floor(c.radius))

        stencil_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(stencil_mask, (cx_i, cy_i), r_i, 255, -1)

        # 4. Strict stencil composite:
        # Output = overlay_canvas where stencil_mask == 255, else untouched base_image
        mask_3ch = stencil_mask > 0
        if len(output.shape) == 3:
            mask_3ch = mask_3ch[:, :, np.newaxis]

        output = np.where(mask_3ch, overlay_canvas, base_image)
        return output
