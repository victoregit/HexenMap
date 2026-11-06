"""Multi-Surface Overlay Manager coordinating native minimap and expanded map projections.

Dynamically switches rendering between the circular gameplay minimap HUD (Marco B)
and the native expanded M-key georeferenced map (Marco A) based on in-game state,
enforcing full click-through transparency and screen capture exclusion.
"""

from __future__ import annotations
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.map.expanded_projector import ExpandedMapProjector, ProjectedMarkerItem
from src.map.minimap_projector import MinimapCircle, MinimapProjector, ProjectedMinimapMarker
from src.map.registration import MapRegistration
from src.markers.models import Marker
from src.overlay.capture_exclusion import set_capture_exclusion
from src.overlay.win32_overlay import set_always_on_top, set_click_through, set_window_transparency
from src.tracking.state_detector import GameState

logger = logging.getLogger(__name__)


class ActiveSurfaceState(str, Enum):
    """The current active transparent overlay display surface."""
    GAMEPLAY_MINIMAP = "gameplay_minimap"    # Overworld gameplay; circular minimap pin overlay
    NATIVE_MAP_OPEN = "native_map_open"      # M-key opened native map; full georeferenced overlay
    MENU_OR_LOADING = "menu_or_loading"      # Cutscene, dialogue, loading screen; overlay hidden
    NO_GAME = "no_game"                      # Genshin Impact not running; fallback HUD / settings


class MultiSurfaceOverlayManager:
    """Coordinates seamless switching between transparent game overlay surfaces."""

    def __init__(
        self,
        hwnd: Optional[int] = None,
        initial_state: ActiveSurfaceState = ActiveSurfaceState.GAMEPLAY_MINIMAP,
        minimap_circle: Optional[MinimapCircle] = None,
        registration: Optional[MapRegistration] = None,
    ) -> None:
        self._hwnd = hwnd
        self._state = initial_state
        self._is_visible = True
        self._click_through_enabled = False
        self._is_map_open = False

        # Subsystem projectors
        self.minimap_projector = MinimapProjector(circle=minimap_circle)
        self.expanded_projector = ExpandedMapProjector(registration=registration or MapRegistration())

        # Callbacks
        self._state_callbacks: List[Callable[[ActiveSurfaceState, ActiveSurfaceState], None]] = []

        if hwnd is not None:
            self.attach_window(hwnd)

    @property
    def hwnd(self) -> Optional[int]:
        return self._hwnd

    @property
    def state(self) -> ActiveSurfaceState:
        return self._state

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @property
    def is_click_through(self) -> bool:
        return self._click_through_enabled

    @property
    def is_map_open(self) -> bool:
        return self._is_map_open

    def add_state_callback(self, cb: Callable[[ActiveSurfaceState, ActiveSurfaceState], None]) -> None:
        """Register callback for surface state transitions."""
        self._state_callbacks.append(cb)

    def attach_window(self, hwnd: int) -> None:
        """Attach native window handle, configure click-through and capture exclusion."""
        self._hwnd = hwnd
        # Set topmost, click-through, and capture exclusion
        set_always_on_top(hwnd, True)
        set_capture_exclusion(hwnd, True)
        self._apply_surface_window_styles()

    def set_map_open(self, is_open: bool) -> None:
        """Inform manager whether native M-key map is open."""
        if self._is_map_open != is_open:
            self._is_map_open = is_open
            if self._state not in (ActiveSurfaceState.MENU_OR_LOADING, ActiveSurfaceState.NO_GAME):
                new_state = ActiveSurfaceState.NATIVE_MAP_OPEN if is_open else ActiveSurfaceState.GAMEPLAY_MINIMAP
                self.set_surface_state(new_state)

    def set_surface_state(self, new_state: ActiveSurfaceState) -> None:
        """Transition to a new surface state."""
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        logger.info("Surface state changed: %s -> %s", old_state.value, new_state.value)

        self._apply_surface_window_styles()

        for cb in self._state_callbacks:
            try:
                cb(new_state, old_state)
            except Exception as e:
                logger.error("Error in surface state callback: %s", e)

    def update_from_game_state(
        self,
        game_state: GameState,
        is_game_running: bool = True,
        is_map_key_active: Optional[bool] = None,
    ) -> None:
        """Evaluate and apply state transition from CV game state detection."""
        if not is_game_running:
            self.set_surface_state(ActiveSurfaceState.NO_GAME)
            return

        if is_map_key_active is not None:
            self._is_map_open = is_map_key_active

        if game_state in (GameState.LOADING_SCREEN, GameState.CUTSCENE_OR_DIALOGUE, GameState.MENU_OPEN):
            self.set_surface_state(ActiveSurfaceState.MENU_OR_LOADING)
        elif game_state == GameState.ACTIVE_GAMEPLAY:
            if self._is_map_open:
                self.set_surface_state(ActiveSurfaceState.NATIVE_MAP_OPEN)
            else:
                self.set_surface_state(ActiveSurfaceState.GAMEPLAY_MINIMAP)
        elif game_state == GameState.UNKNOWN:
            # Keep current state unless in loading, default to gameplay minimap
            if self._state == ActiveSurfaceState.NO_GAME:
                self.set_surface_state(ActiveSurfaceState.GAMEPLAY_MINIMAP)

    def _apply_surface_window_styles(self) -> None:
        """Apply OS window styles appropriate for the current active surface."""
        if self._hwnd is None:
            return

        if self._state == ActiveSurfaceState.GAMEPLAY_MINIMAP:
            # Transparent click-through HUD overlay
            set_click_through(self._hwnd, True)
            self._click_through_enabled = True
            set_window_transparency(self._hwnd, 0.90)
            self._is_visible = True

        elif self._state == ActiveSurfaceState.NATIVE_MAP_OPEN:
            # Native expanded map georeferenced overlay: click-through active to allow game map panning
            set_click_through(self._hwnd, True)
            self._click_through_enabled = True
            set_window_transparency(self._hwnd, 0.95)
            self._is_visible = True

        elif self._state == ActiveSurfaceState.MENU_OR_LOADING:
            # Suspend overlay rendering to prevent visual pollution during cinematics
            set_click_through(self._hwnd, True)
            self._click_through_enabled = True
            set_window_transparency(self._hwnd, 0.0)
            self._is_visible = False

        elif self._state == ActiveSurfaceState.NO_GAME:
            # Game not detected; interactive configuration window (no click-through)
            set_click_through(self._hwnd, False)
            self._click_through_enabled = False
            set_window_transparency(self._hwnd, 1.0)
            self._is_visible = True

    def project_markers(
        self,
        markers: List[Marker],
        player_pos: Tuple[float, float],
        player_heading: float = 0.0,
        active_ids: Optional[Set[str]] = None,
        pan_offset: Tuple[float, float] = (0.0, 0.0),
        zoom: float = 1.0,
    ) -> List[Any]:
        """Project markers based on the current active surface.

        Returns empty list when in MENU_OR_LOADING or NO_GAME state.
        Returns ProjectedMinimapMarker items when in GAMEPLAY_MINIMAP state.
        Returns ProjectedMarkerItem items when in NATIVE_MAP_OPEN state.
        """
        # Strict zero selection rule
        if active_ids is not None and len(active_ids) == 0:
            return []

        if self._state == ActiveSurfaceState.GAMEPLAY_MINIMAP:
            return self.minimap_projector.project_markers(
                markers=markers,
                player_pos=player_pos,
                player_heading=player_heading,
                active_ids=active_ids,
            )

        elif self._state == ActiveSurfaceState.NATIVE_MAP_OPEN:
            if pan_offset != (0.0, 0.0):
                self.expanded_projector.set_pan(pan_offset[0], pan_offset[1])
            if zoom != 1.0:
                self.expanded_projector.set_zoom(zoom)
            return self.expanded_projector.project_markers(
                markers=markers,
                active_ids=active_ids,
            )

        return []
