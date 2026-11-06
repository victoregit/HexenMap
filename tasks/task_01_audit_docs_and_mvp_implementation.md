# Task Specification: Open Source Audit, Architecture, and MVP Implementation

## Objective
Implement Phase 1 through 5 of the "Genshin Interactive Overlay" project:
1. Comprehensive OSS Audit of Jude-Chaer/genshin-overlay, EliteMasterEric/Teyvat.moe, and kongying-tavern.
2. Architecture specification comparing Tauri+React, C+++ImGui, and Python+Win32/OpenCV desktop modular architecture.
3. Data sources documentation and licensing/legal assessment.
4. Product roadmap and reproducible performance benchmarks.
5. Production-ready, modular MVP with clean code and tests covering all required system modules.
6. Execution and verification of all automated tests and benchmarks.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Detailed Requirements

### 1. Documentation Deliverables (to be placed in `docs/` and root `README.md`)
- `/mnt/d/Projects/GenshinGemWish/docs/OSS_AUDIT.md`:
  - Detailed audit of the 3 reference projects:
    - `Jude-Chaer/genshin-overlay`: Screen capture, OpenCV SIFT/RANSAC homography, ImGui DirectX/OpenGL overlay, transparent window, click-through, hotkeys, license analysis (No license = All Rights Reserved; code cannot be copied, only clean-room independent implementation of concepts).
    - `EliteMasterEric/Teyvat.moe`: Marker data structure, categories, layered maps, collected markers, local storage persistence, routes, license analysis (GNU GPL-3.0 copyleft risk, archived status, data model extraction).
    - `kongying-tavern` (genshin-map / cv-tracker / map-client): Visual tracking via OpenCV template matching on fixed minimap, position sync, overlay implementation, layer representation, license analysis (MulanPSL-1.0 permissive, sub-repo variations).
  - Comparative matrix: Features, Licenses, Reusable Concepts, Blockers/Risks, Architectural takeaways.
  - Strict boundary rules: What is reused conceptually vs what must be written from scratch (clean-room).

- `/mnt/d/Projects/GenshinGemWish/docs/ARCHITECTURE.md`:
  - Comparative analysis of architectures:
    - Option A: Tauri + React + TypeScript + native OpenCV
    - Option B: C++ + ImGui + OpenCV
    - Option C: Modular Python Desktop (Tkinter/CustomTkinter/Win32 ctypes + OpenCV + NumPy)
    - Evaluation criteria: RAM consumption, CPU/GPU, render latency, overlay ease, maintenance, CV integration, Windows 10/11 compatibility.
  - Decision record (ADR): Selected architecture rationale and trade-offs.
  - Detailed module specifications:
    - `OverlayManager`: Transparent window, always-on-top, click-through toggling, keyboard hotkeys, compact/expanded modes. Windows Win32 API (`WS_EX_LAYERED`, `WS_EX_TRANSPARENT`, `WS_EX_TOPMOST`, `SetLayeredWindowAttributes`) with cross-platform mock/fallback for Linux/testing.
    - `MapRenderer`: Map view, panning, zooming, region handling, marker rendering, layers.
    - `MarkerRepository`: Marker schema, loading, category filtering, bounding box queries.
    - `ProgressManager`: Manual collected/uncollected tracking, atomic persistence, export/import, versioning, failure recovery.
    - `PositionTracker`: CV-ready modular interface, static test image support, confidence estimation, fallback handling.
    - `PerformanceMonitor`: CPU, RAM, render latency, CV processing latency, p50/p95/p99 calculations.
  - Component diagrams, data flow diagrams, and sequence diagrams.

- `/mnt/d/Projects/GenshinGemWish/docs/DATA_SOURCES.md`:
  - Audit of marker datasets: HoYoLAB Official Map, Kongying Tavern dataset, Teyvat.moe dataset.
  - Licensing, Terms of Service, scraping restrictions, redistribution permissions.
  - Definition of standard JSON Marker Schema (`Marker`, `Category`, `Coordinate`, `Region`, `Layer`).
  - Interface for pluggable data importers.

- `/mnt/d/Projects/GenshinGemWish/docs/ROADMAP.md`:
  - Phase 1: MVP (Manual tracking, overlay, persistence, filters, demo dataset).
  - Phase 2: Live CV Minimap Tracking (fixed minimap template matching, SIFT/ORB background thread, rotation/heading support).
  - Phase 3: Route planning, multi-layer underground maps, community sync.
  - Phase 4: Auto-sync and performance tuning.

- `/mnt/d/Projects/GenshinGemWish/docs/BENCHMARKS.md`:
  - Methodology, test environment, metrics collected.
  - Real reproducible benchmark results: Memory consumption (idle vs active), CPU usage, marker filter latency, progress save latency, position tracking simulation latency.
  - p50, p95, p99 measurements.

- `/mnt/d/Projects/GenshinGemWish/README.md`:
  - Project title, badge, vision, safety & ToS compliance statement (strictly external overlay, no memory tampering, no DLL injection, no botting).
  - Architecture overview.
  - Prerequisites and installation.
  - How to run the MVP (interactive demo mode, overlay mode, CLI switches).
  - Running automated tests and benchmarks.
  - Attribution and third-party notices.

---

### 2. Application Source Code (to be placed in `src/` and `data/`)

Directory structure:
```
/mnt/d/Projects/GenshinGemWish/
├── data/
│   └── demo_markers.json
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── overlay/
│   │   ├── __init__.py
│   │   ├── overlay_manager.py
│   │   └── win32_overlay.py
│   ├── map/
│   │   ├── __init__.py
│   │   └── map_renderer.py
│   ├── markers/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── marker_repository.py
│   ├── progress/
│   │   ├── __init__.py
│   │   └── progress_manager.py
│   ├── tracking/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── position_tracker.py
│   └── performance/
│       ├── __init__.py
│       └── performance_monitor.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_overlay_manager.py
│   ├── test_map_renderer.py
│   ├── test_marker_repository.py
│   ├── test_progress_manager.py
│   ├── test_position_tracker.py
│   ├── test_performance_monitor.py
│   └── test_app_integration.py
├── scripts/
│   └── run_benchmarks.py
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

#### Module Specifications:
1. `src/markers/models.py` & `src/markers/marker_repository.py`:
   - Data models: `Marker`, `MarkerCategory`, `MarkerFilter`, `RegionInfo`.
   - `MarkerRepository`:
     - Load markers from JSON.
     - Validate against schema.
     - Filter by category, region, layer, collected status, search term, or bounding box `(min_x, min_y, max_x, max_y)`.
     - Count markers by category.
     - Get all categories and regions.
2. `src/progress/progress_manager.py`:
   - Store collected marker IDs with timestamp.
   - Atomic disk write using temporary file + rename to prevent corruption on crash.
   - Backup creation before save.
   - Versioned storage format (`version: 1`).
   - Export progress to JSON file, import from JSON file.
   - Reset progress with backup option.
3. `src/map/map_renderer.py`:
   - World coordinate to viewport coordinate projection.
   - Viewport pan, zoom with bounds clamping.
   - Region bounds handling (Mondstadt, Liyue, etc.).
   - Layer support (surface vs underground layers).
   - Canvas/terminal/headless rendering output for testing and Tkinter/GUI canvas display.
4. `src/overlay/overlay_manager.py` & `src/overlay/win32_overlay.py`:
   - State management: Compact mode vs Expanded mode vs Hidden.
   - Transparency configuration (`alpha` 0.0 - 1.0).
   - Click-through mode: On Windows, use `ctypes.windll.user32` to set `WS_EX_TRANSPARENT | WS_EX_LAYERED`. In compact mode, click-through is enabled so clicks pass to the game. In expanded mode, click-through is disabled so user can interact.
   - Hotkey handling: Toggling visibility and compact/expanded state.
   - Cross-platform abstraction: Fallback mock implementation when running under Linux/headless for unit tests.
5. `src/tracking/position_tracker.py`:
   - `PositionTrackerInterface` with methods `estimate_position(image) -> PositionEstimate`.
   - `PositionEstimate`: `x, y, confidence, layer, heading_degrees, is_valid`.
   - Support for static image recognition test mode (e.g. template matching or feature matching against reference minimap tiles).
   - Handles low confidence / missing minimap gracefully without crashing.
   - Configurable sampling interval (e.g. 2Hz - 5Hz) to keep CPU low.
6. `src/performance/performance_monitor.py`:
   - Record operation timings: `record_render_time(ms)`, `record_cv_time(ms)`, `record_query_time(ms)`.
   - Query metrics: count, mean, min, max, p50, p95, p99.
   - System resource tracking: CPU usage, memory RSS (using `psutil` or fallback).
   - Formatted summary report generation.
7. `src/app.py`:
   - Main entry point.
   - CLI flags: `--demo`, `--mode {compact,expanded}`, `--headless`, `--stats`, `--data <path>`.
   - Complete GUI implementation using `tkinter` (which is standard and cross-platform) with transparent/overlay styling, compact HUD view, expanded interactive map view, category filtering checklist, search box, click-to-mark collected, and status bar.
   - Graceful shutdown, progress saving on exit.

---

### 3. Verification & Testing Requirements
1. Unit tests:
   - Full test coverage across all 6 core modules.
   - Run via `pytest tests/ -v`.
   - All tests must pass with 0 failures, 0 errors.
2. Benchmarks:
   - Run `python3 scripts/run_benchmarks.py` to produce real measurements.
   - Write the exact recorded numbers (mean, p50, p95, p99, RAM, CPU) into `docs/BENCHMARKS.md`.
3. Adherence to Security Rules:
   - No DLL injection, no reading game memory, no automation/botting, no bypass of anti-cheat.
   - External overlay and visual recognition only.

When finished, provide a detailed summary of all files created and test execution output.
