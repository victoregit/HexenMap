# Task Specification: Phase 2 — Live Computer Vision Minimap Tracking

## Objective
Implement Phase 2 of the **Genshin Interactive Overlay** product roadmap:
Deliver an end-to-end, high-performance, non-invasive live Computer Vision autotracking subsystem capable of tracking player coordinates, player heading angle, and subterranean layer in real-time at 5 Hz with minimal CPU overhead.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Deliverables & Subsystem Architecture

### 1. Screen Capture Subsystem (`src/capture/`)
Create `src/capture/`:
- `src/capture/__init__.py`
- `src/capture/base.py`:
  - `ScreenCaptureInterface(ABC)`:
    - `find_game_window() -> Optional[Tuple[int, int, int, int]]` (returns `(x, y, width, height)`)
    - `capture_frame(rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]`
    - `capture_minimap(client_rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]`
    - `is_game_running() -> bool`
- `src/capture/win32_capture.py`:
  - Windows screen capture using Win32 GDI / BitBlt / Desktop Duplication APIs via `ctypes.windll.user32` and `ctypes.windll.gdi32`.
  - Resolution-aware minimap crop coordinates calculation:
    * Standard 1080p (1920x1080): Minimap crop region `(30, 20, 220, 220)`.
    * Dynamic scaling for 1440p (2560x1440), 4K (3840x2160), and 720p (1280x720).
  - Robust cross-platform mock (`MockScreenCapture`) for non-Windows environments, synthetic frame generation, and unit testing.

### 2. Specialized CV Subsystems (`src/tracking/`)
Enhance `src/tracking/`:
- `src/tracking/heading_detector.py`:
  - `PlayerHeadingDetector`:
    - Analyzes center of minimap crop for player directional indicator arrow/cone.
    - Uses color thresholding in HSV space + contour orientation / moments or template rotation matching.
    - Returns `heading_degrees: float` in $[0.0, 360.0)$ (0° = North, 90° = East, 180° = South, 270° = West) and confidence score $[0.0, 1.0]$.
    - Handles case where player is stationary or arrow is obscured.
- `src/tracking/state_detector.py`:
  - `GameStateDetector`:
    - Fast heuristics to detect:
      1. Loading screen (uniform dark or bright frame, low standard deviation).
      2. Cutscene / Dialogue (top and bottom black letterbox bars or dialogue banner).
      3. Active gameplay (rich minimap content with edges and color variance).
    - Returns `GameState: Enum (ACTIVE_GAMEPLAY, LOADING_SCREEN, CUTSCENE_OR_DIALOGUE, MENU_OPEN, UNKNOWN)`.
    - Enables CV to suspend execution during loading screens/dialogue to save 100% of CV CPU usage.
- `src/tracking/underground_detector.py`:
  - `UndergroundCaveDetector`:
    - Analyzes minimap color histogram and luminosity.
    - Classifies whether the active minimap view corresponds to `surface` terrain or `underground` caverns (e.g. The Chasm underground or subterranean Sumeru ruins).
    - Returns `detected_layer: str` ("surface" or "underground") and confidence.
- `src/tracking/autotracker_service.py`:
  - `AutoTrackerService`:
    - Background thread worker running at configurable frequency (default 5 Hz / 200 ms interval).
    - Coordinates screen capture, game state check, position estimation, heading detection, and underground detection.
    - Thread-safe state synchronization with callbacks (`on_position_updated(estimate)`).
    - Graceful start, stop, pause, resume methods.
    - Reports timings to `PerformanceMonitor`.

### 3. Application GUI Integration (`src/app.py`)
- Update `GenshinOverlayApp`:
  - Add Auto-Tracker controls: Toggle between `Manual`, `Simulated`, and `Live CV`.
  - Draw player location indicator on map canvas: render player dot with directional heading cone/arrow rotating in real-time.
  - Automatically center map on player when tracking is active (with user pan override).
  - Auto-switch active layer selector if `underground` is detected.
  - In Compact HUD view: show real-time player coordinates `(X, Y, Z)`, current heading direction (N, NE, E, SE, S, SW, W, NW), and distance to closest uncollected marker.

### 4. Comprehensive Testing & Benchmarking
- Add test modules in `tests/`:
  - `tests/test_screen_capture.py`: Window rect resolution, scaling calculations, capture bounds, mock frame generation.
  - `tests/test_heading_detector.py`: Synthetic arrow images with known angles (0°, 45°, 90°, 180°, 270°), verifying heading accuracy within ±3°.
  - `tests/test_state_detector.py`: Game state detection across loading screens, letterbox cutscenes, and gameplay frames.
  - `tests/test_underground_detector.py`: Surface vs underground palette classification.
  - `tests/test_autotracker_service.py`: Thread start/stop/pause, callback triggering, exception handling, rate limiting.
- Update `scripts/run_benchmarks.py`:
  - Add microbenchmarks for:
    * Screen capture crop latency
    * Heading detection latency
    * Game state detection latency
    * Full tracking pipeline iteration latency
- Update `docs/BENCHMARKS.md` and `docs/ROADMAP.md` reflecting completed Phase 2 milestones.

---

## Constraints
- External execution only: zero memory reading, zero DLL injection, zero anticheat interference.
- All 46 existing tests must continue to pass; all new tests must pass with 100% success rate.
- Adhere to clean-room development rules.

Please run the test suite and benchmark suite when complete, and provide a comprehensive report of all created and updated files with absolute paths.
