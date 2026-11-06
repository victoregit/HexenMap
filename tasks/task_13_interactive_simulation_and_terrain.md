# Task Specification: Add Live Animation Loop, Visual Region Outlines, and Clarify Status

## Objective
Enhance the user experience so that when `GenshinOverlay.exe` is opened:
1. The map is dynamically alive: start an active GUI timer (`root.after(100, self._periodic_tick)`) so that in `simulated` mode (default), the player dot, heading cone, and distance to markers continuously animate and update smoothly across the screen at 10 Hz.
2. The canvas visually shows geography: draw stylized regional landmasses/territory outlines for Mondstadt, Dragonspine, Liyue, and The Chasm so the user sees a recognizable game world map under the markers rather than just an empty grid.
3. Provide a Tracking Mode toggle directly in the top bar: buttons for `[Simulated Demo]` and `[Live Genshin CV]` so the user can easily switch without command-line flags.
4. Ensure all tests pass (78+ tests) and recompile `GenshinOverlay.exe`.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Detailed Requirements

### 1. Active Simulation Tick in `src/app.py`
- In `src/app.py`, implement `_schedule_gui_tick(self)`:
  ```python
  def _schedule_gui_tick(self) -> None:
      if not self.is_running or not self.root:
          return
      if self.tracking_mode == "simulated":
          self.redraw_map()
      # Re-schedule every 100ms (10 FPS)
      try:
          self.root.after(100, self._schedule_gui_tick)
      except Exception:
          pass
  ```
- Trigger `self._schedule_gui_tick()` when GUI starts (`initialize_gui` / `start`).
- Now, when the user double-clicks `GenshinOverlay.exe`, the character dot moves along the path, the direction cone turns, and the distance counters update live!

### 2. Stylized Regional Geography on Map Canvas
- In `src/map/map_renderer.py` and `src/app.py`:
  - Define basic regional bounding polygons or stylized landmasses:
    * **Mondstadt**: Central plateau and Cider Lake island (e.g. around x: 1800-2400, y: -1600 to -1000).
    * **Dragonspine**: Mountain peak circle/polygon with ice-blue contour (`#3a506b`, `#1b263b`) around x: 1500-2200, y: -600 to 0.
    * **Liyue**: Northern karst plains, Dihua Marsh, and Liyue Harbor bay around x: 800-1600, y: 200-1200.
    * **The Chasm**: Circular crater around x: 200-600, y: 600-1000.
  - Draw these regional contours on the canvas before drawing grid and markers so players visually recognize the Teyvat continent layout.
  - Draw region title watermarks (e.g. "MONDSTADT", "LIYUE", "DRAGONSPINE") with low opacity font.

### 3. Top Control Bar Enhancements
- In `_build_gui_widgets()`:
  - Add quick tracking buttons:
    * `Mode: [Simulated Demo] [Live CV] [Manual]`
  - Add a button `[Center on Player]` or toggle `Auto-Center: ON`.

### 4. Rebuild & Verification
- Run `pytest tests/` to confirm all tests pass.
- Recompile `GenshinOverlay.exe` with Windows Python.
- Test that `GenshinOverlay.exe` starts and animates.
