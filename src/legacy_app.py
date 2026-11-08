"""Main application entry point for Hexen Map Overlay."""

from __future__ import annotations
import argparse
import logging
import math
import os
import sys
import time

# Ensure project root is in sys.path when running app.py directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from typing import Any, Dict, List, Optional, Set

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore
    TKINTER_AVAILABLE = False

from src.map.map_renderer import MapRenderer
from src.markers.importers import CommunityJSONMarkerImporter, DatasetProvenance, GeoJSONMarkerImporter
from src.markers.marker_repository import MarkerRepository
from src.markers.models import Marker, MarkerFilter
from src.overlay.capture_exclusion import set_capture_exclusion
from src.overlay.global_hotkeys import GlobalHotkeyListener, VK_F11, VK_F12
from src.overlay.multi_surface_manager import ActiveSurfaceState, MultiSurfaceOverlayManager
from src.overlay.overlay_manager import OverlayManager, OverlayMode
from src.overlay.window_tracker import GameWindowRect, GameWindowTracker
from src.performance.performance_monitor import PerformanceMonitor
from src.progress.progress_manager import ProgressManager
from src.tracking.base import PositionEstimate
from src.tracking.position_tracker import SimulatedPositionTracker
from src.tracking.autotracker_service import AutoTrackerService
from src.tracking.reference_tile_manager import ReferenceTile, ReferenceTileManager
from src.tracking.smooth_tracker import ConfidenceGatedTracker, SmoothedPositionTracker
from src.tracking.state_detector import GameState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HexenMap")


def degrees_to_cardinal(deg: float) -> str:
    """Convert compass degrees [0, 360) to 8-point cardinal abbreviation."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int(round((deg % 360.0) / 45.0)) % 8
    return directions[idx]


class HexenMapApp:
    """Full-featured Genshin Impact interactive map overlay application."""

    def __init__(
        self,
        data_path: Optional[str] = None,
        progress_path: Optional[str] = None,
        initial_mode: OverlayMode = OverlayMode.EXPANDED,
        headless: bool = False,
        demo_mode: bool = True,
        tracking_mode: Optional[str] = None,
    ) -> None:
        self.headless = headless
        self.demo_mode = demo_mode
        self.initial_mode = initial_mode
        self.tracking_mode = tracking_mode or ("simulated" if demo_mode else "manual")
        self.auto_center = True

        # Core subsystems
        self.repository = MarkerRepository()
        self.perf_monitor = PerformanceMonitor()

        # Resolve paths
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        app_dir = os.getcwd() if getattr(sys, "frozen", False) else bundle_dir
        self.data_path = data_path or os.path.join(bundle_dir, "data", "demo_markers.json")
        # Fallback to local data folder if running next to data/
        if not os.path.exists(self.data_path) and os.path.exists(os.path.join(app_dir, "data", "demo_markers.json")):
            self.data_path = os.path.join(app_dir, "data", "demo_markers.json")

        self.progress_path = progress_path or os.path.join(app_dir, "userData", "progress.json")

        # Load markers
        if os.path.exists(self.data_path):
            count = self.repository.load_from_json(self.data_path)
            logger.info("Loaded %d markers from %s", count, self.data_path)
        else:
            logger.warning("Marker data file not found: %s", self.data_path)

        # Progress manager
        self.progress = ProgressManager(filepath=self.progress_path)

        # Map renderer
        self.renderer = MapRenderer(viewport_width=800, viewport_height=600)
        # Center initially on Mondstadt Windrise or first marker
        all_markers = self.repository.get_all_markers()
        if all_markers:
            self.renderer.center_on(all_markers[0].coordinates.x, all_markers[0].coordinates.y)

        # Position tracking (simulated for demo/tests)
        self.tracker = SimulatedPositionTracker()

        # Live AutoTracker Service (Phase 2 CV)
        self.autotracker_service = AutoTrackerService(perf_monitor=self.perf_monitor)
        self.autotracker_service.add_position_listener(self._on_live_position_update)
        self.autotracker_service.add_state_listener(self._on_live_state_update)

        if self.tracking_mode == "live_cv" and not self.headless:
            self.autotracker_service.start()

        # Overlay manager
        self.overlay_mgr = OverlayManager(initial_mode=initial_mode)
        self.overlay_mgr.register_mode_callback(self._on_overlay_mode_changed)

        # Multi-surface overlay manager (Marco C)
        self.multi_surface_mgr = MultiSurfaceOverlayManager()
        self.multi_surface_mgr.add_state_callback(self._on_surface_state_changed)

        # Game window tracker (Marco C)
        self.window_tracker = GameWindowTracker()
        self.window_tracker.add_on_moved_callback(self._on_game_window_moved)
        self.window_tracker.add_on_found_callback(self._on_game_window_found)
        self.window_tracker.add_on_lost_callback(self._on_game_window_lost)

        # Global hotkey listener (Marco C)
        self.hotkey_listener = GlobalHotkeyListener()
        self.hotkey_listener.register_hotkey(1, VK_F11, callback=self._on_hotkey_toggle_mode)
        self.hotkey_listener.register_hotkey(2, VK_F12, callback=self._on_hotkey_toggle_visibility)

        # Continuous tracking & confidence gating (Marco D)
        self.confidence_gate = ConfidenceGatedTracker(min_confidence=0.60)
        self.tile_manager = ReferenceTileManager()
        self.dataset_provenance: Optional[DatasetProvenance] = None

        # Filter state
        self.selected_categories: Set[str] = set(self.repository.get_categories().keys())
        self.selected_region: Optional[str] = None
        self.selected_layer: str = "surface"
        self.show_collected: bool = True
        self.search_query: str = ""

        # GUI references (None in headless)
        self.root: Optional[Any] = None
        self.canvas: Optional[Any] = None
        self.is_running: bool = False
        self._drag_start_x: float = 0.0
        self._drag_start_y: float = 0.0
        self.btn_mode_sim: Optional[Any] = None
        self.btn_mode_cv: Optional[Any] = None
        self.btn_mode_manual: Optional[Any] = None
        self.auto_center_btn: Optional[Any] = None

    def _on_live_position_update(self, estimate: PositionEstimate) -> None:
        """Handle background live CV position update with confidence gating and circular EMA."""
        if self.tracking_mode != "live_cv":
            return

        # Confidence gate (< 60% rejected) and circular statistics EMA smoothing (Marco D)
        filtered = self.confidence_gate.process(estimate)
        if not filtered.is_valid:
            return

        # Auto-center camera if enabled and not currently dragging
        if self.auto_center and not getattr(self, "_was_dragged", False):
            self.renderer.center_on(filtered.x, filtered.y)

        # Auto-switch layer if underground cavern is detected
        if filtered.layer != self.selected_layer:
            self.selected_layer = filtered.layer
            self.renderer.set_layer(self.selected_layer)
            if hasattr(self, "layer_var") and self.layer_var:
                try:
                    self.layer_var.set(self.selected_layer)
                except Exception:
                    pass

        if self.root and not self.headless:
            try:
                self.root.after_idle(self.redraw_map)
            except Exception:
                pass

    def load_dataset_with_provenance(self, file_path: str) -> Tuple[int, DatasetProvenance]:
        """Load exploration markers from a verified GeoJSON or Community JSON file with provenance tracking."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if file_path.endswith(".geojson") or '"FeatureCollection"' in content:
            importer = GeoJSONMarkerImporter()
        else:
            importer = CommunityJSONMarkerImporter()

        markers, provenance = importer.import_markers(content)
        self.dataset_provenance = provenance
        for m in markers:
            self.repository.add_marker(m)

        logger.info(
            "Imported %d markers from %s with provenance: %s (License: %s, Compatible: %s)",
            len(markers),
            file_path,
            provenance.name,
            provenance.license_type,
            provenance.is_license_compatible,
        )
        return len(markers), provenance

    def _on_live_state_update(self, state: GameState) -> None:
        """Handle game state change (e.g. loading screen or cutscene)."""
        if self.status_lbl:
            try:
                self.status_lbl.config(text=f"Status: {state.value}")
            except Exception:
                pass
        if hasattr(self, "multi_surface_mgr"):
            self.multi_surface_mgr.update_from_game_state(state, is_game_running=True)

    def _on_hotkey_toggle_mode(self) -> None:
        """Invoked from background hotkey thread when F11 is pressed."""
        if self.root:
            self.root.after_idle(self.overlay_mgr.toggle_mode)
        else:
            self.overlay_mgr.toggle_mode()

    def _on_hotkey_toggle_visibility(self) -> None:
        """Invoked from background hotkey thread when F12 is pressed."""
        if self.root:
            self.root.after_idle(self.overlay_mgr.toggle_visibility)
        else:
            self.overlay_mgr.toggle_visibility()

    def _on_game_window_moved(self, rect: GameWindowRect) -> None:
        """Handle game window repositioning or resizing."""
        logger.debug("Game window repositioned: (%d, %d, %dx%d)", rect.x, rect.y, rect.width, rect.height)

    def _on_game_window_found(self, hwnd: int) -> None:
        """Handle game window detection."""
        logger.info("Genshin Impact game window found (HWND: %s)", hwnd)
        if hasattr(self, "status_lbl") and self.status_lbl:
            try:
                self.status_lbl.config(text="Game: Attached")
            except Exception:
                pass

    def _on_game_window_lost(self) -> None:
        """Handle game window loss (game exited or closed)."""
        logger.info("Genshin Impact game window lost.")
        self.multi_surface_mgr.set_surface_state(ActiveSurfaceState.NO_GAME)
        if hasattr(self, "status_lbl") and self.status_lbl:
            try:
                self.status_lbl.config(text="Game: Not Found")
            except Exception:
                pass

    def _on_surface_state_changed(self, new_state: ActiveSurfaceState, old_state: ActiveSurfaceState) -> None:
        """Handle surface state change between minimap, native expanded map, and menu."""
        logger.info("Active surface changed to: %s", new_state.value)
        if self.root and not self.headless:
            try:
                self.root.after_idle(self.redraw_map)
            except Exception:
                pass

    def set_tracking_mode(self, mode: str) -> None:
        """Switch player position tracking between 'manual', 'simulated', and 'live_cv'."""
        self.tracking_mode = mode
        logger.info("Switched tracking mode to: %s", mode)
        if hasattr(self, "track_var") and getattr(self, "track_var", None):
            try:
                self.track_var.set(mode)
            except Exception:
                pass
        self._update_top_bar_mode_buttons()
        if mode == "live_cv":
            self.autotracker_service.start()
        else:
            self.autotracker_service.pause()
        self.redraw_map()

    def center_on_player(self) -> None:
        """Center map camera on current player coordinates."""
        if self.tracking_mode == "live_cv":
            pos = self.autotracker_service.get_latest_estimate()
        elif self.tracking_mode == "simulated":
            pos = self.tracker.estimate_position()
        else:
            pos = PositionEstimate.invalid()

        if pos.is_valid:
            self._was_dragged = False
            self.renderer.center_on(pos.x, pos.y)
            self.redraw_map()

    def toggle_auto_center(self) -> None:
        """Toggle auto-center camera following."""
        self.auto_center = not self.auto_center
        if hasattr(self, "auto_center_var") and getattr(self, "auto_center_var", None):
            try:
                self.auto_center_var.set(self.auto_center)
            except Exception:
                pass
        if getattr(self, "auto_center_btn", None):
            lbl = "Follow: ON" if self.auto_center else "Follow: OFF"
            fg = "#a3be8c" if self.auto_center else "#d08770"
            try:
                self.auto_center_btn.config(text=lbl, fg=fg)
            except Exception:
                pass
        if self.auto_center:
            self._was_dragged = False
            self.center_on_player()

    def _update_top_bar_mode_buttons(self) -> None:
        """Update top bar mode button highlight styles."""
        if not getattr(self, "btn_mode_sim", None):
            return
        m = self.tracking_mode
        try:
            self.btn_mode_sim.config(
                bg="#2d4263" if m == "simulated" else "#2c313c",
                fg="#61afef" if m == "simulated" else "#abb2bf",
                font=("Segoe UI", 8, "bold" if m == "simulated" else "normal"),
            )
            self.btn_mode_cv.config(
                bg="#2d4263" if m == "live_cv" else "#2c313c",
                fg="#98c379" if m == "live_cv" else "#abb2bf",
                font=("Segoe UI", 8, "bold" if m == "live_cv" else "normal"),
            )
            self.btn_mode_manual.config(
                bg="#2d4263" if m == "manual" else "#2c313c",
                fg="#d19a66" if m == "manual" else "#abb2bf",
                font=("Segoe UI", 8, "bold" if m == "manual" else "normal"),
            )
        except Exception:
            pass

    def _schedule_gui_tick(self) -> None:
        """Periodic GUI timer (10 Hz / 100ms) for smooth simulated movement and live updates."""
        if not self.root:
            return
        if self.is_running and self.tracking_mode == "simulated":
            self.redraw_map()
        # Re-schedule every 100ms (10 FPS)
        try:
            self.root.after(100, self._schedule_gui_tick)
        except Exception:
            pass

    def _on_auto_center_toggle(self) -> None:
        if hasattr(self, "auto_center_var") and getattr(self, "auto_center_var", None):
            self.auto_center = self.auto_center_var.get()
        if getattr(self, "auto_center_btn", None):
            lbl = "Follow: ON" if self.auto_center else "Follow: OFF"
            fg = "#a3be8c" if self.auto_center else "#d08770"
            try:
                self.auto_center_btn.config(text=lbl, fg=fg)
            except Exception:
                pass
        if self.auto_center:
            self._was_dragged = False
            self.redraw_map()

    def _on_overlay_mode_changed(self, mode: OverlayMode) -> None:
        logger.info("Overlay mode switched to: %s", mode.value)
        if self.root and not self.headless:
            self._update_gui_layout_for_mode(mode)

    @property
    def active_marker_ids(self) -> Set[str]:
        """Set of marker IDs conforming to current UI filter state (single source of truth)."""
        return {m.id for m in self.get_filtered_markers()}

    def get_filtered_markers(self) -> List[Marker]:
        """Fetch markers conforming to current UI filter state.

        Strict filtering rule: If zero categories are selected (empty set),
        ZERO markers are returned (never all).
        """
        t0 = time.perf_counter()
        if self.selected_categories is not None and len(self.selected_categories) == 0:
            return []

        marker_filter = MarkerFilter(
            categories=self.selected_categories if self.selected_categories is not None else None,
            regions={self.selected_region} if self.selected_region else None,
            layers={self.selected_layer} if self.selected_layer else None,
            collected=None if self.show_collected else False,
            search=self.search_query if self.search_query else None,
        )
        collected_ids = self.progress.get_collected_ids()
        results = self.repository.filter_markers(marker_filter, collected_ids)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.perf_monitor.record_query_time(elapsed_ms)
        return results

    def find_nearest_marker(self, x: float, y: float) -> Optional[Tuple[Marker, float]]:
        """Find closest uncollected marker to the specified coordinates."""
        markers = self.get_filtered_markers()
        collected_ids = self.progress.get_collected_ids()
        best_marker = None
        min_dist = float("inf")

        for m in markers:
            if m.id in collected_ids:
                continue
            dist = math.hypot(m.coordinates.x - x, m.coordinates.y - y)
            if dist < min_dist:
                min_dist = dist
                best_marker = m

        if best_marker:
            return best_marker, min_dist
        return None

    def toggle_marker_collected(self, marker_id: str) -> bool:
        """Toggle marker collected state and persist."""
        new_state = self.progress.toggle_collected(marker_id)
        self.progress.save()
        logger.info("Toggled marker '%s': collected=%s", marker_id, new_state)
        return new_state

    # -------------------------------------------------------------------------
    # Headless / CLI Execution Loop
    # -------------------------------------------------------------------------
    def run_headless(self, iterations: int = 5) -> None:
        """Run simulated application cycles without GUI (for benchmarks and tests)."""
        logger.info("Starting headless simulation loop (%d iterations)...", iterations)
        self.is_running = True

        for i in range(iterations):
            # 1. Update position estimate
            t_cv0 = time.perf_counter()
            pos = self.tracker.estimate_position()
            t_cv = (time.perf_counter() - t_cv0) * 1000.0
            self.perf_monitor.record_cv_time(t_cv)

            # 2. Render calculations
            t_r0 = time.perf_counter()
            markers = self.get_filtered_markers()
            collected_ids = self.progress.get_collected_ids()
            cats_map = self.repository.get_categories()
            render_items = self.renderer.prepare_render_list(
                markers=markers,
                collected_ids=collected_ids,
                categories_map=cats_map,
                player_coords=(pos.x, pos.y, pos.heading_degrees),
            )
            t_render = (time.perf_counter() - t_r0) * 1000.0
            self.perf_monitor.record_render_time(t_render)

            # 3. Simulate periodic collection
            if i % 2 == 0 and markers:
                self.progress.mark_collected(markers[0].id)
                self.progress.save()

            time.sleep(0.01)

        self.is_running = False
        logger.info("Headless simulation finished.")

    # -------------------------------------------------------------------------
    # Tkinter GUI Implementation
    # -------------------------------------------------------------------------
    def initialize_gui(self) -> None:
        """Set up Tkinter overlay window, canvas, and sidebar controls."""
        if not TKINTER_AVAILABLE or tk is None:
            logger.warning("Tkinter not available; falling back to headless mode.")
            self.headless = True
            return

        try:
            self.root = tk.Tk()
        except Exception as e:
            logger.warning("Could not initialize Tkinter display (%s); running headless.", e)
            self.headless = True
            return

        self.root.title("Hexen Map - Overlay")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1a1c23")

        # Associate with overlay manager (resolving root top-level HWND for Windows)
        try:
            from src.overlay.win32_overlay import get_toplevel_hwnd
            raw_hwnd = self.root.winfo_id()
            hwnd = get_toplevel_hwnd(raw_hwnd)
            self.overlay_mgr.attach_window(hwnd)
            self.multi_surface_mgr.attach_window(hwnd)
            set_capture_exclusion(hwnd, True)
        except Exception as e:
            logger.debug("Failed attaching window handle: %s", e)

        # Start game window tracker and global hotkey listener
        try:
            self.window_tracker.start()
            self.hotkey_listener.start()
        except Exception as e:
            logger.debug("Failed starting tracker or hotkeys: %s", e)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Build main layout
        self._build_gui_widgets()
        self._update_gui_layout_for_mode(self.overlay_mgr.mode)

        # Keyboard hotkeys
        self.root.bind("<F11>", lambda e: self.overlay_mgr.toggle_mode())
        self.root.bind("<F12>", lambda e: self.overlay_mgr.toggle_visibility())
        self.root.bind("<Escape>", lambda e: self.overlay_mgr.set_mode(OverlayMode.COMPACT))

        # Start periodic GUI animation tick
        self._schedule_gui_tick()

    def _build_gui_widgets(self) -> None:
        # Top Control Bar
        self.top_bar = tk.Frame(self.root, bg="#21252f", height=38)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(self.top_bar, text="✦ HEXEN MAP", font=("Segoe UI", 10, "bold"), fg="#e0e6ed", bg="#21252f")
        title_lbl.pack(side=tk.LEFT, padx=(10, 6), pady=6)

        mode_btn = tk.Button(self.top_bar, text="HUD (F11)", font=("Segoe UI", 8), bg="#3b4252", fg="#eceff4", command=self.overlay_mgr.toggle_mode)
        mode_btn.pack(side=tk.LEFT, padx=3)

        save_btn = tk.Button(self.top_bar, text="Save", font=("Segoe UI", 8), bg="#3b4252", fg="#eceff4", command=self.progress.save)
        save_btn.pack(side=tk.LEFT, padx=3)

        # Quick Tracking Mode Switcher
        tk.Label(self.top_bar, text="| Mode:", font=("Segoe UI", 8), fg="#6c7a96", bg="#21252f").pack(side=tk.LEFT, padx=(6, 2))

        self.btn_mode_sim = tk.Button(
            self.top_bar,
            text="Sim Demo",
            font=("Segoe UI", 8, "bold" if self.tracking_mode == "simulated" else "normal"),
            bg="#2d4263" if self.tracking_mode == "simulated" else "#2c313c",
            fg="#61afef" if self.tracking_mode == "simulated" else "#abb2bf",
            command=lambda: self.set_tracking_mode("simulated"),
        )
        self.btn_mode_sim.pack(side=tk.LEFT, padx=2)

        self.btn_mode_cv = tk.Button(
            self.top_bar,
            text="Live CV",
            font=("Segoe UI", 8, "bold" if self.tracking_mode == "live_cv" else "normal"),
            bg="#2d4263" if self.tracking_mode == "live_cv" else "#2c313c",
            fg="#98c379" if self.tracking_mode == "live_cv" else "#abb2bf",
            command=lambda: self.set_tracking_mode("live_cv"),
        )
        self.btn_mode_cv.pack(side=tk.LEFT, padx=2)

        self.btn_mode_manual = tk.Button(
            self.top_bar,
            text="Manual",
            font=("Segoe UI", 8, "bold" if self.tracking_mode == "manual" else "normal"),
            bg="#2d4263" if self.tracking_mode == "manual" else "#2c313c",
            fg="#d19a66" if self.tracking_mode == "manual" else "#abb2bf",
            command=lambda: self.set_tracking_mode("manual"),
        )
        self.btn_mode_manual.pack(side=tk.LEFT, padx=2)

        # Center on Player & Follow Player buttons
        center_btn = tk.Button(
            self.top_bar,
            text="🎯 Center",
            font=("Segoe UI", 8),
            bg="#3b4252",
            fg="#eceff4",
            command=self.center_on_player,
        )
        center_btn.pack(side=tk.LEFT, padx=(6, 2))

        self.auto_center_btn = tk.Button(
            self.top_bar,
            text="Follow: ON" if self.auto_center else "Follow: OFF",
            font=("Segoe UI", 8),
            bg="#3b4252",
            fg="#a3be8c" if self.auto_center else "#d08770",
            command=self.toggle_auto_center,
        )
        self.auto_center_btn.pack(side=tk.LEFT, padx=2)

        self.status_lbl = tk.Label(self.top_bar, text="Ready", font=("Segoe UI", 8), fg="#8892b0", bg="#21252f")
        self.status_lbl.pack(side=tk.RIGHT, padx=10)

        # Main Workspace Container
        self.workspace = tk.Frame(self.root, bg="#1a1c23")
        self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Interactive Map Canvas
        self.canvas = tk.Canvas(self.workspace, bg="#111318", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas Event Bindings (Pan & Zoom & Click)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<MouseWheel>", self._on_canvas_scroll)  # Windows / macOS
        self.canvas.bind("<Button-4>", lambda e: self._zoom(1.15, e.x, e.y))  # Linux zoom in
        self.canvas.bind("<Button-5>", lambda e: self._zoom(0.85, e.x, e.y))  # Linux zoom out
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Right Sidebar (Filter panel)
        self.sidebar = tk.Frame(self.workspace, bg="#1e222d", width=260)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Search Bar
        search_frame = tk.Frame(self.sidebar, bg="#1e222d")
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        search_lbl = tk.Label(search_frame, text="Search:", font=("Segoe UI", 8, "bold"), fg="#abb2bf", bg="#1e222d")
        search_lbl.pack(anchor="w")
        self.search_entry = tk.Entry(search_frame, bg="#282c34", fg="#ffffff", insertbackground="white")
        self.search_entry.pack(fill=tk.X, pady=2)
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Tracking Mode Selector (Manual, Simulated, Live CV)
        track_frame = tk.Frame(self.sidebar, bg="#1e222d")
        track_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)
        tk.Label(track_frame, text="Tracking:", font=("Segoe UI", 8, "bold"), fg="#abb2bf", bg="#1e222d").pack(anchor="w")
        self.track_var = tk.StringVar(value=self.tracking_mode)
        for t_val, t_lbl in [("manual", "Manual"), ("simulated", "Sim"), ("live_cv", "Live CV")]:
            rb = tk.Radiobutton(
                track_frame,
                text=t_lbl,
                variable=self.track_var,
                value=t_val,
                command=lambda: self.set_tracking_mode(self.track_var.get()),
                bg="#1e222d",
                fg="#abb2bf",
                selectcolor="#282c34",
                font=("Segoe UI", 8),
            )
            rb.pack(side=tk.LEFT, padx=1)

        # Auto-center follow player toggle
        self.auto_center_var = tk.BooleanVar(value=self.auto_center)
        follow_chk = tk.Checkbutton(
            self.sidebar,
            text="Follow Player (Auto-Center)",
            variable=self.auto_center_var,
            command=self._on_auto_center_toggle,
            bg="#1e222d",
            fg="#abb2bf",
            selectcolor="#282c34",
            font=("Segoe UI", 8),
        )
        follow_chk.pack(anchor="w", padx=10, pady=2)

        # Region Selector
        region_frame = tk.Frame(self.sidebar, bg="#1e222d")
        region_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)
        tk.Label(region_frame, text="Region:", font=("Segoe UI", 8, "bold"), fg="#abb2bf", bg="#1e222d").pack(anchor="w")
        self.region_var = tk.StringVar(value="All Regions")
        regions = ["All Regions"] + [r.name for r in self.repository.get_regions().values()]
        self.region_combo = ttk.Combobox(region_frame, textvariable=self.region_var, values=regions, state="readonly")
        self.region_combo.pack(fill=tk.X, pady=2)
        self.region_combo.bind("<<ComboboxSelected>>", self._on_region_selected)

        # Layer Selector (Surface vs Underground)
        layer_frame = tk.Frame(self.sidebar, bg="#1e222d")
        layer_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)
        tk.Label(layer_frame, text="Layer:", font=("Segoe UI", 8, "bold"), fg="#abb2bf", bg="#1e222d").pack(anchor="w")
        self.layer_var = tk.StringVar(value="surface")
        btn_s = tk.Radiobutton(layer_frame, text="Surface", variable=self.layer_var, value="surface", command=self._on_layer_changed, bg="#1e222d", fg="#abb2bf", selectcolor="#282c34")
        btn_u = tk.Radiobutton(layer_frame, text="Underground", variable=self.layer_var, value="underground", command=self._on_layer_changed, bg="#1e222d", fg="#abb2bf", selectcolor="#282c34")
        btn_s.pack(side=tk.LEFT, padx=2)
        btn_u.pack(side=tk.LEFT, padx=2)

        # Show Collected Checkbox
        self.show_collected_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(self.sidebar, text="Show Collected", variable=self.show_collected_var, command=self._on_show_collected_toggle, bg="#1e222d", fg="#abb2bf", selectcolor="#282c34")
        chk.pack(anchor="w", padx=10, pady=4)

        # Categories Checklist Scrollbox
        tk.Label(self.sidebar, text="Categories:", font=("Segoe UI", 8, "bold"), fg="#abb2bf", bg="#1e222d").pack(anchor="w", padx=10, pady=(6, 2))
        self.cats_frame = tk.Frame(self.sidebar, bg="#1e222d")
        self.cats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)
        self._populate_category_checkboxes()

        # Compact HUD Mini-Widget (shown when in compact mode)
        self.compact_hud = tk.Frame(self.root, bg="#1a1c23")
        self.hud_label = tk.Label(self.compact_hud, text="Nearest Marker: None", font=("Segoe UI", 9, "bold"), fg="#61afef", bg="#1a1c23")
        self.hud_label.pack(side=tk.LEFT, padx=8, pady=6)
        self.hud_btn = tk.Button(self.compact_hud, text="Expand (F11)", font=("Segoe UI", 8), bg="#3b4252", fg="#eceff4", command=self.overlay_mgr.toggle_mode)
        self.hud_btn.pack(side=tk.RIGHT, padx=6, pady=4)
        self.hud_collect_btn = tk.Button(self.compact_hud, text="✓ Collect", font=("Segoe UI", 8), bg="#2d694d", fg="#ffffff", command=self._on_hud_quick_collect)
        self.hud_collect_btn.pack(side=tk.RIGHT, padx=2, pady=4)

    def _on_hud_quick_collect(self) -> None:
        """Quickly toggle collected state for the closest marker in HUD view."""
        if self.tracking_mode == "live_cv":
            pos = self.autotracker_service.get_latest_estimate()
        elif self.tracking_mode == "simulated":
            pos = self.tracker.estimate_position()
        else:
            pos = PositionEstimate.invalid()
        px = pos.x if pos.is_valid else 0.0
        py = pos.y if pos.is_valid else 0.0
        nearest = self.find_nearest_marker(px, py)
        if nearest:
            nm, dist = nearest
            self.toggle_marker_collected(nm.id)
            self.redraw_map()
            self._populate_category_checkboxes()

    def _populate_category_checkboxes(self) -> None:
        for child in self.cats_frame.winfo_children():
            child.destroy()

        counts = self.repository.count_by_category(self.progress.get_collected_ids())
        categories = self.repository.get_categories()

        for cat_id, cat in categories.items():
            cat_count = counts.get(cat_id, {"total": 0, "collected": 0})
            label_text = f"{cat.name} ({cat_count['collected']}/{cat_count['total']})"
            var = tk.BooleanVar(value=cat_id in self.selected_categories)

            def make_handler(cid: str, v: tk.BooleanVar):
                def handler():
                    if v.get():
                        self.selected_categories.add(cid)
                    else:
                        self.selected_categories.discard(cid)
                    self.redraw_map()
                return handler

            chk = tk.Checkbutton(
                self.cats_frame,
                text=label_text,
                variable=var,
                command=make_handler(cat_id, var),
                bg="#1e222d",
                fg=cat.color,
                selectcolor="#282c34",
                activebackground="#1e222d",
                anchor="w",
            )
            chk.pack(fill=tk.X, pady=1)

    def _update_gui_layout_for_mode(self, mode: OverlayMode) -> None:
        if not self.root:
            return

        if mode == OverlayMode.COMPACT:
            self.top_bar.pack_forget()
            self.workspace.pack_forget()
            self.compact_hud.pack(fill=tk.BOTH, expand=True)
            self.root.geometry("420x48+20+20")
            self.root.overrideredirect(True)
        elif mode == OverlayMode.EXPANDED:
            self.compact_hud.pack_forget()
            self.top_bar.pack(side=tk.TOP, fill=tk.X)
            self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            self.root.geometry("1000x700")
            self.root.overrideredirect(False)
            self.redraw_map()
        elif mode == OverlayMode.HIDDEN:
            self.root.withdraw()
            return

        self.root.deiconify()

    def _on_canvas_press(self, event: Any) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._was_dragged = False

    def _on_canvas_drag(self, event: Any) -> None:
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        if abs(dx) > 3 or abs(dy) > 3:
            self._was_dragged = True
            self.renderer.pan_by(dx, dy)
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self.redraw_map()

    def _on_canvas_release(self, event: Any) -> None:
        if not self._was_dragged:
            # Click event: check for marker hit
            markers = self.get_filtered_markers()
            collected_ids = self.progress.get_collected_ids()
            clicked = self.renderer.find_marker_at_screen_pos(event.x, event.y, markers, collected_ids)
            if clicked:
                new_state = self.toggle_marker_collected(clicked.id)
                self.redraw_map()
                self._populate_category_checkboxes()
                state_str = "Collected" if new_state else "Uncollected"
                if self.status_lbl:
                    self.status_lbl.config(text=f"Marked {clicked.name} as {state_str}")

    def _on_canvas_scroll(self, event: Any) -> None:
        factor = 1.15 if event.delta > 0 else 0.85
        self._zoom(factor, event.x, event.y)

    def _zoom(self, factor: float, screen_x: float, screen_y: float) -> None:
        self.renderer.zoom_at(factor, screen_x, screen_y)
        self.redraw_map()

    def _on_canvas_resize(self, event: Any) -> None:
        self.renderer.set_viewport_dimensions(event.width, event.height)
        self.redraw_map()

    def _on_search_changed(self, event: Any) -> None:
        self.search_query = self.search_entry.get().strip()
        self.redraw_map()

    def _on_region_selected(self, event: Any) -> None:
        reg_name = self.region_var.get()
        if reg_name == "All Regions":
            self.selected_region = None
            self.renderer.set_region(None)
        else:
            for r in self.repository.get_regions().values():
                if r.name == reg_name:
                    self.selected_region = r.id
                    self.renderer.set_region(r.id)
                    bounds = self.repository.get_bounds(r.id)
                    self.renderer.fit_bounds(bounds)
                    break
        self.redraw_map()

    def _on_layer_changed(self) -> None:
        self.selected_layer = self.layer_var.get()
        self.renderer.set_layer(self.selected_layer)
        self.redraw_map()

    def _on_show_collected_toggle(self) -> None:
        self.show_collected = self.show_collected_var.get()
        self.redraw_map()

    def redraw_map(self) -> None:
        """Render markers, grid lines, and player position onto the Tkinter canvas."""
        if not self.canvas:
            return

        t0 = time.perf_counter()
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50:
            cw, ch = 800, 600

        # 1. Get player position estimate and apply auto-center before drawing terrain
        if self.tracking_mode == "live_cv":
            raw_pos = self.autotracker_service.get_latest_estimate()
            pos = self.confidence_gate.process(raw_pos)
        elif self.tracking_mode == "simulated":
            pos = self.tracker.estimate_position()
        else:
            pos = PositionEstimate.invalid()

        # Auto-center camera if enabled and player position is valid and not dragging
        if self.auto_center and pos.is_valid and not getattr(self, "_was_dragged", False):
            self.renderer.center_on(pos.x, pos.y)

        # 2. Stylized Regional Landmasses / Geography Contours under grid & markers
        landmasses = self.renderer.get_regional_landmasses()
        for lm in landmasses:
            poly = lm.get("polygon", [])
            if len(poly) >= 3:
                flat_coords: List[float] = []
                for wx, wy in poly:
                    vx, vy = self.renderer.world_to_viewport(wx, wy)
                    flat_coords.extend([vx, vy])
                fill_col = lm.get("fill", "#181f29")
                out_col = lm.get("outline", "#2b3b4d")
                self.canvas.create_polygon(*flat_coords, fill=fill_col, outline=out_col, width=2)

            # Draw region watermark title
            label_text = lm.get("name")
            if label_text and "label_pos" in lm:
                lwx, lwy = lm["label_pos"]
                lvx, lvy = self.renderer.world_to_viewport(lwx, lwy)
                if -200 <= lvx <= cw + 200 and -200 <= lvy <= ch + 200:
                    font_size = max(9, min(24, int(18 * self.renderer.state.zoom)))
                    self.canvas.create_text(
                        lvx, lvy,
                        text=label_text,
                        fill="#384152",
                        font=("Segoe UI", font_size, "bold"),
                    )

        # 3. Draw subtle grid lines
        grid_step = 500  # world units
        min_wx, min_wy = self.renderer.viewport_to_world(0, 0)
        max_wx, max_wy = self.renderer.viewport_to_world(cw, ch)
        start_gx = int(math.floor(min(min_wx, max_wx) / grid_step)) * grid_step
        end_gx = int(math.ceil(max(min_wx, max_wx) / grid_step)) * grid_step
        start_gy = int(math.floor(min(min_wy, max_wy) / grid_step)) * grid_step
        end_gy = int(math.ceil(max(min_wy, max_wy) / grid_step)) * grid_step

        for gx in range(start_gx, end_gx + 1, grid_step):
            vx, _ = self.renderer.world_to_viewport(gx, 0)
            self.canvas.create_line(vx, 0, vx, ch, fill="#1c202a", width=1)

        for gy in range(start_gy, end_gy + 1, grid_step):
            _, vy = self.renderer.world_to_viewport(0, gy)
            self.canvas.create_line(0, vy, cw, vy, fill="#1c202a", width=1)

        # 4. Prepare render items
        markers = self.get_filtered_markers()
        collected_ids = self.progress.get_collected_ids()
        cats_map = self.repository.get_categories()

        render_data = self.renderer.prepare_render_list(
            markers=markers,
            collected_ids=collected_ids,
            categories_map=cats_map,
            player_coords=(pos.x, pos.y, pos.heading_degrees) if pos.is_valid else None,
        )

        # 4. Draw markers
        for item in render_data["markers"]:
            r = item.radius
            vx, vy = item.vx, item.vy

            if item.is_collected:
                # Dim hollow circle
                self.canvas.create_oval(vx - r, vy - r, vx + r, vy + r, outline=item.color, width=1.5, fill="#161820")
            else:
                # Vibrant filled circle with glow halo
                self.canvas.create_oval(vx - r - 2, vy - r - 2, vx + r + 2, vy + r + 2, outline=item.color, width=1, fill="")
                self.canvas.create_oval(vx - r, vy - r, vx + r, vy + r, fill=item.color, outline="#ffffff", width=1)

            # Label if zoomed in
            if self.renderer.state.zoom >= 0.4:
                self.canvas.create_text(vx, vy + r + 8, text=item.label, fill="#dcdfe4", font=("Segoe UI", 7))

        # 5. Draw Player Marker
        player_item = render_data["player"]
        if player_item and player_item.is_valid:
            pvx = player_item.vx
            pvy = player_item.vy
            rad = math.radians(player_item.heading)

            # Draw rotating directional heading cone
            cone_angle = math.radians(28)
            cone_len = 24
            c1_x = pvx + cone_len * math.sin(rad - cone_angle)
            c1_y = pvy - cone_len * math.cos(rad - cone_angle)
            c2_x = pvx + cone_len * math.sin(rad + cone_angle)
            c2_y = pvy - cone_len * math.cos(rad + cone_angle)
            tip_x = pvx + (cone_len + 5) * math.sin(rad)
            tip_y = pvy - (cone_len + 5) * math.cos(rad)

            # Directional heading cone polygon
            self.canvas.create_polygon(
                pvx, pvy, c1_x, c1_y, tip_x, tip_y, c2_x, c2_y,
                fill="#f39c12", outline="#ffffff", width=1
            )
            # Center player dot
            self.canvas.create_oval(pvx - 6, pvy - 6, pvx + 6, pvy + 6, fill="#e5c07b", outline="#ffffff", width=2)

            # Live CV active beacon ring
            if self.tracking_mode == "live_cv":
                self.canvas.create_oval(pvx - 12, pvy - 12, pvx + 12, pvy + 12, outline="#61afef", width=1.5)

        # 6. Update HUD readout
        nearest = self.find_nearest_marker(pos.x, pos.y) if pos.is_valid else self.find_nearest_marker(0.0, 0.0)
        if self.hud_label:
            if pos.is_valid:
                cardinal = degrees_to_cardinal(pos.heading_degrees)
                coord_info = f"[{pos.x:.0f}, {pos.y:.0f}] 🧭 {pos.heading_degrees:.0f}° {cardinal}"
                if nearest:
                    nm, dist = nearest
                    self.hud_label.config(text=f"{coord_info} | ✦ {nm.name} ({dist:.0f}m)")
                else:
                    self.hud_label.config(text=f"{coord_info} | ✦ Nearest: None")
            else:
                if nearest:
                    nm, dist = nearest
                    self.hud_label.config(text=f"✦ Nearest: {nm.name} ({dist:.0f}m)")
                else:
                    self.hud_label.config(text="✦ Nearest: None")

        # Record render latency
        render_time_ms = (time.perf_counter() - t0) * 1000.0
        self.perf_monitor.record_render_time(render_time_ms)

        if self.status_lbl:
            visible_count = len(render_data["markers"])
            total_collected = len(collected_ids)
            self.status_lbl.config(
                text=f"Visible: {visible_count} | Collected: {total_collected}/{self.repository.total_count} | Zoom: {self.renderer.state.zoom:.2f}x | Latency: {render_time_ms:.1f}ms"
            )

    def start(self) -> None:
        """Start the application main loop."""
        self.is_running = True
        if self.headless or not self.root:
            self.run_headless()
        else:
            self._schedule_gui_tick()
            self.root.mainloop()

    def on_close(self) -> None:
        """Handle application shutdown cleanly."""
        logger.info("Shutting down application...")
        self.is_running = False
        if hasattr(self, "hotkey_listener") and self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception as e:
                logger.debug("Error stopping hotkey listener: %s", e)
        if hasattr(self, "window_tracker") and self.window_tracker:
            try:
                self.window_tracker.stop()
            except Exception as e:
                logger.debug("Error stopping window tracker: %s", e)
        if hasattr(self, "autotracker_service") and self.autotracker_service:
            try:
                self.autotracker_service.stop()
            except Exception as e:
                logger.debug("Error stopping autotracker service: %s", e)
        try:
            self.progress.save()
            logger.info("Progress saved successfully on exit.")
        except Exception as e:
            logger.error("Error saving progress on exit: %s", e)

        if self.root:
            self.root.destroy()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hexen Map - Interactive Map Overlay")
    parser.add_argument("--demo", action="store_true", default=True, help="Run in demo mode with simulated player tracking")
    parser.add_argument("--tracking", choices=["manual", "simulated", "live_cv"], default=None, help="Player position tracking source")
    parser.add_argument("--mode", choices=["compact", "expanded"], default="expanded", help="Initial overlay window mode")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display (for CI and benchmarks)")
    parser.add_argument("--stats", action="store_true", help="Print performance benchmark summary on exit")
    parser.add_argument("--data", type=str, default=None, help="Path to marker JSON dataset")
    parser.add_argument("--progress", type=str, default=None, help="Path to player progress file")
    parser.add_argument("--export-progress", type=str, default=None, help="Export progress to JSON file and exit")
    parser.add_argument("--import-progress", type=str, default=None, help="Import progress from JSON file and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    # Mode selection
    mode = OverlayMode.COMPACT if args.mode == "compact" else OverlayMode.EXPANDED
    tracking = args.tracking
    if tracking is None:
        tracking = "simulated" if args.demo else "manual"

    app = HexenMapApp(
        data_path=args.data,
        progress_path=args.progress,
        initial_mode=mode,
        headless=args.headless,
        demo_mode=args.demo,
        tracking_mode=tracking,
    )

    if args.export_progress:
        app.progress.export_to_json(args.export_progress)
        print(f"Progress exported to {args.export_progress}")
        return 0

    if args.import_progress:
        count = app.progress.import_from_json(args.import_progress)
        print(f"Imported {count} records from {args.import_progress}")
        return 0

    if not args.headless:
        # Check if X11 / Wayland DISPLAY is available
        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and sys.platform != "win32":
            logger.info("No DISPLAY environment detected. Switching automatically to --headless mode.")
            app.headless = True
        else:
            app.initialize_gui()

    app.start()

    if args.stats:
        print("\n" + app.perf_monitor.generate_summary_table())

    return 0


if __name__ == "__main__":
    sys.exit(main())
