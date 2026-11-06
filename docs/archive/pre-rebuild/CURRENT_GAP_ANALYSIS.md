# Genshin Gem Wish: Current Codebase Gap Analysis & Architecture Diagnostics

**Date:** 2026-11-02  
**Audience:** Software Architecture Team, Systems Engineers, Open Source Contributors  
**Status:** Remodel Architecture Blueprint (Marco A Baseline)

---

## 1. Executive Summary & Product Vision Pivot

The original Genshin Gem Wish prototype was implemented as an independent standalone window with a custom Tkinter canvas (`1000x700`), a synthetic coordinate grid, stylized landmass polygons, and a simulated player tracker.

### The Problem With the Original Concept
As identified in [`ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md`](file:///mnt/d/Projects/GenshinGemWish/ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md) and [`GenshinGemWish_AUDITORIA_E_REMODELACAO.md`](file:///mnt/d/Projects/GenshinGemWish/GenshinGemWish_AUDITORIA_E_REMODELACAO.md), **Genshin Impact players do not want a second, parallel map on their screen**. Drawing an independent map application forces the player to look away from their game, duplicate navigation, and manage an intrusive separate window.

### The Corrected Product Vision
Genshin Gem Wish must function strictly as an **external, click-through, transparent layer optically registered directly over the native in-game interfaces of Genshin Impact**:

1. **Gameplay Circular Minimap**: Detect the circular minimap region on screen, project active markers relative to the player's position, and clip them strictly within the circular boundaries of the native minimap HUD.
2. **Native Expanded Map (M-Key)**: Detect when the player opens the native game map with `M`, and project active exploration markers onto the exact terrain features of the game's original map, continuously tracking native pan and zoom.

Exploration markers are **geographically fixed in the world of Teyvat**, but their **screen pixel coordinates continuously change** during panning, zooming, player locomotion, and camera rotation.

---

## 2. In-Depth Module-by-Module Codebase Audit

| Subsystem / Function | Current Implementation | Status | Remodeling Action Required |
| :--- | :--- | :--- | :--- |
| [`src/app.py::redraw_map`](file:///mnt/d/Projects/GenshinGemWish/src/app.py#L720-L770) | Draws a 500-unit coordinate grid, stylized landmasses, and marker circles on a private `tk.Canvas`. | **Divergent** | Demote synthetic canvas to an optional debug mode (`--debug-map`). Main operational rendering moves to transparent, click-through overlay windows mapped to native game UI. |
| [`src/app.py::_update_gui_layout_for_mode`](file:///mnt/d/Projects/GenshinGemWish/src/app.py#L480-L510) | Switches between a 420x48 textual HUD and a 1000x700 standalone window. | **Obsolete** | Replace with UI state machine: `GAMEPLAY_MINIMAP`, `NATIVE_MAP_OPEN`, `SETTINGS_PANEL`, and `NO_GAME`. |
| [`src/app.py::get_filtered_markers`](file:///mnt/d/Projects/GenshinGemWish/src/app.py#L273-L290) | Previously converted empty category selections `set()` to `None`, displaying all markers. | **FIXED** | Fixed in Marco A: empty selection `len(selected_categories) == 0` strictly returns `0` markers. Added `active_marker_ids` as single source of truth. |
| [`src/map/map_renderer.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/map_renderer.py) | Camera transformations for internal virtual canvas only (`world_to_viewport`). | **Partial** | Retain for internal calculations; complement with [`src/map/registration.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/registration.py) and [`src/map/expanded_projector.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/expanded_projector.py). |
| [`src/tracking/autotracker_service.py`](file:///mnt/d/Projects/GenshinGemWish/src/tracking/autotracker_service.py) | Instantiated `MinimapTemplateTracker` without providing reference terrain map tiles. | **Incomplete** | Live CV position returns invalid unless reference terrain features or OCR/feature matching are calibrated. |
| [`src/capture/base.py`](file:///mnt/d/Projects/GenshinGemWish/src/capture/base.py) | Hardcoded fixed ratio crop rectangle for minimap (e.g. 1080p -> `(20, 20, 220, 220)`). | **Fragile** | Does not accommodate dynamic HUD scales, custom resolutions, multi-monitor offsets, or DPI scaling. |
| [`src/capture/win32_capture.py`](file:///mnt/d/Projects/GenshinGemWish/src/capture/win32_capture.py) | Windows GDI `BitBlt` capture of target HWND. | **Functional** | Works for Borderless Windowed mode; must ensure overlay window does not contaminate capture frames. |
| [`data/demo_markers.json`](file:///mnt/d/Projects/GenshinGemWish/data/demo_markers.json) | 50 curated demonstration markers in Mondstadt/Liyue. | **Demonstration** | Coordinates are illustrative; cannot be claimed as exhaustive or production-accurate for uncalibrated zones. |
| Hotkeys (`root.bind`) | Tkinter window-level key bindings (`<F11>`, `<F12>`, `<Escape>`). | **Limitation** | Only triggers when Tkinter overlay has active OS window focus, which drops when player interacts with Genshin. |

---

## 3. What Works vs. What Was Simulated

### Fully Functional & Verified Components
1. **Marker Repository & Atomic Progress Management**: [`src/markers/marker_repository.py`](file:///mnt/d/Projects/GenshinGemWish/src/markers/marker_repository.py) and [`src/progress/progress_manager.py`](file:///mnt/d/Projects/GenshinGemWish/src/progress/progress_manager.py) provide robust indexing, category counting, atomic `.tmp -> .bak` file swapping, and full JSON import/export.
2. **Win32 Overlay Window Management**: [`src/overlay/win32_overlay.py`](file:///mnt/d/Projects/GenshinGemWish/src/overlay/win32_overlay.py) correctly applies `WS_EX_LAYERED`, `WS_EX_TRANSPARENT`, and `HWND_TOPMOST` for genuine click-through capability on Windows.
3. **Computer Vision Heading & State Detectors**: [`src/tracking/heading_detector.py`](file:///mnt/d/Projects/GenshinGemWish/src/tracking/heading_detector.py), [`src/tracking/state_detector.py`](file:///mnt/d/Projects/GenshinGemWish/src/tracking/state_detector.py), and [`src/tracking/underground_detector.py`](file:///mnt/d/Projects/GenshinGemWish/src/tracking/underground_detector.py) reliably classify player orientation, loading screens, dialogue letterboxes, and cavern color profiles.
4. **Marco A Geometric Registration**: [`src/map/registration.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/registration.py) and [`src/map/expanded_projector.py`](file:///mnt/d/Projects/GenshinGemWish/src/map/expanded_projector.py) deliver verified sub-pixel alignment (**0.269 px mean error**) between interactive map references and native game screenshots.

### Simulated / Mocked Components Requiring Hardening
1. **Minimap Position Tracking**: `SimulatedPositionTracker` steps along synthetic waypoints for testing. `MinimapTemplateTracker` requires actual downscaled terrain reference crops before it can track in live gameplay.
2. **Game UI State Transition**: Detection of whether the native map (`M`-key) is currently open or whether the player is in gameplay mode currently requires visual UI template matching (e.g. checking the map legend or top-right close cross).

---

## 4. Technical Blockers & Mitigation Strategy

### Blocker 1: Window Capture Contamination
* **Problem**: If an external overlay window sits on top of the Genshin Impact game window, standard GDI `BitBlt` or desktop capture may capture the overlay's own chest pins, corrupting CV state detection.
* **Mitigation**:
  1. Use Windows `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` on Windows 10 (version 2004+) so OS capture APIs render the game window beneath the overlay cleanly.
  2. Alternatively, capture the game window via `PrintWindow` with `PW_RENDERFULLCONTENT` or DXGI Desktop Duplication API.

### Blocker 2: Global Low-Level Hotkeys Without Input Injection
* **Problem**: Standard Tkinter bindings require window focus. If the player is playing Genshin, focus belongs to `GenshinImpact.exe`.
* **Mitigation**:
  1. Implement a non-intrusive Windows hook via `RegisterHotKey(NULL, hotkey_id, MOD_NOREPEAT, VK_F11)` or low-level keyboard hook `WH_KEYBOARD_LL`.
  2. Under no circumstance synthesize keyboard or mouse events into the game process.

### Blocker 3: Dynamic Minimap Calibration Across Displays
* **Problem**: 1080p, 1440p, 4K, ultrawide (21:9), and custom UI scaling factors alter the pixel diameter and offset of the top-left circular minimap.
* **Mitigation**:
  1. Implement an automated circle detector (Hough circle transform constrained to the top-left screen quadrant).
  2. Provide an explicit user calibration preview in the Settings dialog where users can visually adjust center `(cx, cy)` and radius `r`.

---

## 5. Architectural Alignment Matrix

```
[ Genshin Impact Borderless Window ]
                 │
   (Screen Capture without overlay contamination)
                 ▼
     [ Game UI State Detector ]
        ├── GAMEPLAY_MINIMAP  ──► [ MinimapProjector (Circle Mask) ]  ──► Overlay Surface 1
        ├── NATIVE_MAP_OPEN   ──► [ ExpandedMapProjector (Pan/Zoom) ] ──► Overlay Surface 2
        └── LOADING / DIALOGUE──► Suspend overlays (zero visual noise)
                 ▲
                 │
   [ MarkerSelectionState ]  (Single Source of Truth: active_marker_ids)
                 ▲
                 │
[ Settings Panel / Category Filter / Search Dialog ]
```

With Marco A now implemented and verified, the architectural gap between the legacy standalone window and the georeferenced native overlay is definitively bridged.
