"""Verification and Visual Demonstration for Marco B: Circular Gameplay Minimap Overlay.

Calibrates and validates projection of exploration markers inside the native circular
minimap HUD (02_circular_minimap.png) relative to player position.
Verifies mathematical boundary enforcement: strictly 0 pixels leak outside the minimap circle.
"""

from __future__ import annotations
import math
import os
import sys

import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.verify_marco_a import extract_chests_from_interactive_reference
from src.map.minimap_projector import MinimapCircle, MinimapProjector


def verify_marco_b() -> int:
    """Run Marco B minimap circle detection, relative projection, stencil masking, and verification."""
    print("=" * 70)
    print("GENSHIN GEM WISH - MARCO B: CIRCULAR GAMEPLAY MINIMAP OVERLAY VERIFICATION")
    print("=" * 70)

    ref_dir = os.path.join(PROJECT_ROOT, "data", "reference")
    img_interactive_path = os.path.join(ref_dir, "01_interactive_map_chests.png")
    img_minimap_path = os.path.join(ref_dir, "02_circular_minimap.png")

    if not os.path.exists(img_minimap_path):
        print(f"[!] Missing reference minimap image: {img_minimap_path}")
        return 1
    if not os.path.exists(img_interactive_path):
        print(f"[!] Missing reference interactive map image: {img_interactive_path}")
        return 1

    # 1. Load native minimap crop
    img_minimap = cv2.imread(img_minimap_path)
    h_mm, w_mm = img_minimap.shape[:2]
    print(f"[*] Loaded Native Minimap: {w_mm}x{h_mm} pixels")

    # 2. Detect Minimap Circle Geometry
    projector = MinimapProjector()
    circle = projector.detect_minimap_circle(img_minimap)
    print(f"[*] Minimap Circle Geometry:")
    print(f"    Center (cx, cy): ({circle.center_x:.1f}, {circle.center_y:.1f}) px")
    print(f"    Radius (R):      {circle.radius:.1f} px")

    # 3. Load calibrated Dragonspine chests from reference map
    chests = extract_chests_from_interactive_reference(img_interactive_path)
    print(f"[*] Loaded {len(chests)} exploration markers from reference dataset.")

    # 4. Relative Player Projection
    # Player positioned in Dragonspine snowy plateau near chest cluster
    player_pos = (210.0, 250.0)
    player_heading = 100.8  # Measured from 02_circular_minimap.png player cone
    scale = 0.85            # Reference units to minimap pixel scale

    projected_markers = projector.project_markers(
        markers=chests,
        player_pos=player_pos,
        player_heading=player_heading,
        minimap_rotation=False,  # Standard North-up mode
        scale=scale,
        circle=circle,
    )

    inside_markers = [p for p in projected_markers if p.is_inside_circle]
    print(f"[*] Projected {len(projected_markers)} candidate markers relative to player {player_pos}.")
    print(f"[*] Markers within minimap circle perimeter: {len(inside_markers)}")

    # 5. Render Stencil-Masked Minimap Overlay
    overlay_result = projector.render_minimap_overlay(img_minimap, projected_markers, circle)

    out_result_path = os.path.join(ref_dir, "marco_b_minimap_result.png")
    cv2.imwrite(out_result_path, overlay_result)
    print(f"[+] Saved minimap overlay result to: {out_result_path}")

    # 6. Mathematical Verification of Zero Pixel Leakage Outside Circle
    y_coords, x_coords = np.ogrid[:h_mm, :w_mm]
    dist_from_c = np.sqrt((x_coords - circle.center_x) ** 2 + (y_coords - circle.center_y) ** 2)
    outside_mask = dist_from_c > circle.radius

    total_outside_pixels = int(np.sum(outside_mask))
    pixel_diff = np.abs(overlay_result.astype(int) - img_minimap.astype(int))
    outside_diff = pixel_diff[outside_mask]
    leaked_pixels = int(np.count_nonzero(outside_diff.sum(axis=1)))

    print("\n--- Strict Circular Stencil Boundary Enforcement ---")
    print(f"  Total Pixels Outside Circle Radius: {total_outside_pixels}")
    print(f"  Modified / Leaked Pixels:           {leaked_pixels}")
    if leaked_pixels == 0:
        print("  Boundary Status:                    PASS (100% Zero Leakage)")
    else:
        print(f"  Boundary Status:                    FAIL ({leaked_pixels} leaked pixels)")
        return 1

    # 7. Generate Side-by-Side Comparison Image with Header Banner
    banner_h = 55
    comp_w = w_mm * 2
    comp_h = h_mm + banner_h

    comparison = np.zeros((comp_h, comp_w, 3), dtype=np.uint8)
    comparison[:banner_h, :] = (25, 28, 36)

    # Title text
    cv2.putText(
        comparison,
        "GENSHIN GEM WISH - MARCO B: CIRCULAR GAMEPLAY MINIMAP OVERLAY",
        (16, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        comparison,
        f"Center: ({circle.center_x:.1f}, {circle.center_y:.1f}) | Radius: {circle.radius:.1f}px | Leaked Pixels: {leaked_pixels} (STRICT 0) | Active Pins: {len(inside_markers)}",
        (16, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (111, 231, 200),
        1,
        cv2.LINE_AA,
    )

    # Left: Original minimap with detected circular perimeter outline
    left_img = img_minimap.copy()
    cv2.circle(
        left_img,
        (int(round(circle.center_x)), int(round(circle.center_y))),
        int(round(circle.radius)),
        (0, 255, 120),
        1,
        cv2.LINE_AA,
    )

    # Place left and right images
    comparison[banner_h:, :w_mm] = left_img
    comparison[banner_h:, w_mm:] = overlay_result

    # Column Sub-headers
    cv2.putText(
        comparison,
        "[A] Original In-Game Minimap",
        (12, banner_h + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        comparison,
        "[B] Stencil-Masked Chest Overlay",
        (w_mm + 12, banner_h + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (111, 231, 200),
        1,
        cv2.LINE_AA,
    )

    out_comp_path = os.path.join(ref_dir, "marco_b_comparison.png")
    cv2.imwrite(out_comp_path, comparison)
    print(f"[+] Saved comparison image to: {out_comp_path}")

    print("\n" + "=" * 70)
    print("MARCO B VERIFICATION SUCCESSFUL: 0 Pixels Leaked | Circular Mask Complete")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(verify_marco_b())
