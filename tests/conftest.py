"""Pytest fixtures for unit and integration tests."""

import json
import os
import tempfile
import pytest
import numpy as np

from src.markers.models import Marker, MarkerCategory, MarkerCoordinate, RegionBounds, RegionInfo
from src.markers.marker_repository import MarkerRepository
from src.progress.progress_manager import ProgressManager
from src.map.map_renderer import MapRenderer
from src.overlay.overlay_manager import OverlayManager, OverlayMode
from src.overlay.win32_overlay import get_mock_state
from src.performance.performance_monitor import PerformanceMonitor


@pytest.fixture(autouse=True)
def isolate_legacy_native_calls(monkeypatch):
    """Legacy unit tests use made-up HWNDs, never real desktop API calls.

    Live runtime native integration is checked separately against real windows.
    """
    monkeypatch.setattr("src.overlay.win32_overlay.is_windows",lambda:False)
    monkeypatch.setattr("src.overlay.capture_exclusion.is_windows",lambda:False)
    monkeypatch.setattr("src.overlay.window_tracker.is_windows",lambda:False)


@pytest.fixture
def sample_markers_dict():
    """Return dictionary representation of a valid marker dataset."""
    return {
        "version": "1.0.0",
        "categories": [
            {"id": "anemoculus", "name": "Anemoculus", "color": "#6fe7c8"},
            {"id": "geoculus", "name": "Geoculus", "color": "#f3c75f"},
            {"id": "luxurious_chest", "name": "Luxurious Chest", "color": "#f1c40f"},
        ],
        "regions": [
            {
                "id": "mondstadt",
                "name": "Mondstadt",
                "bounds": {"min_x": -3000, "min_y": -4000, "max_x": 1000, "max_y": 0},
            },
            {
                "id": "liyue",
                "name": "Liyue",
                "bounds": {"min_x": -2500, "min_y": 0, "max_x": 2000, "max_y": 4500},
            },
        ],
        "layers": [
            {"id": "surface", "name": "Surface"},
            {"id": "underground", "name": "Underground"},
        ],
        "markers": [
            {
                "id": "m1",
                "name": "Windrise Tree Anemoculus",
                "category_id": "anemoculus",
                "region_id": "mondstadt",
                "layer": "surface",
                "coordinates": {"x": -820.0, "y": -2210.0, "z": 20.0},
                "description": "On the branch",
                "tags": ["tree", "oculi"],
            },
            {
                "id": "m2",
                "name": "Cathedral Belfry Luxurious Chest",
                "category_id": "luxurious_chest",
                "region_id": "mondstadt",
                "layer": "surface",
                "coordinates": {"x": -1618.0, "y": -2595.0, "z": 105.0},
                "description": "Top of bell tower",
                "tags": ["chest", "cathedral"],
            },
            {
                "id": "m3",
                "name": "Wangshu Inn Geoculus",
                "category_id": "geoculus",
                "region_id": "liyue",
                "layer": "surface",
                "coordinates": {"x": 182.0, "y": 1895.0, "z": 135.0},
                "description": "Top finial beam",
                "tags": ["oculi", "wangshu"],
            },
            {
                "id": "m4",
                "name": "Chasm Cave Chest",
                "category_id": "luxurious_chest",
                "region_id": "liyue",
                "layer": "underground",
                "coordinates": {"x": -3460.0, "y": 3625.0, "z": -310.0},
                "description": "Inverted ceiling ruins",
                "tags": ["chest", "underground"],
            },
        ],
    }


@pytest.fixture
def sample_repository(sample_markers_dict):
    repo = MarkerRepository()
    repo.load_from_json(sample_markers_dict)
    return repo


@pytest.fixture
def temp_progress_file(tmp_path):
    # A new profile has no file. An existing empty file is now corruption and
    # must never be silently accepted as an empty collection.
    yield str(tmp_path/'progress.json')


@pytest.fixture
def progress_mgr(temp_progress_file):
    return ProgressManager(filepath=temp_progress_file)


@pytest.fixture
def map_renderer():
    return MapRenderer(viewport_width=800, viewport_height=600, initial_center=(0.0, 0.0), initial_zoom=1.0)


@pytest.fixture
def overlay_mgr():
    mock_state = get_mock_state()
    mock_state.windows.clear()
    return OverlayManager(hwnd=12345, initial_mode=OverlayMode.EXPANDED)


@pytest.fixture
def perf_monitor():
    return PerformanceMonitor()


@pytest.fixture
def synthetic_minimap_pair():
    """Create a synthetic reference map and a matching minimap crop."""
    # Reference terrain image 200x200
    ref_map = np.full((200, 200, 3), 100, dtype=np.uint8)
    # Draw distinct features at (50, 60)
    ref_map[50:70, 60:80] = [220, 150, 40]
    ref_map[55:65, 65:75] = [255, 255, 255]

    # Crop template (30x30 around the feature)
    crop = ref_map[45:75, 55:85].copy()
    return ref_map, crop
