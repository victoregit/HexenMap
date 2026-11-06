# Task Specification: Fix Module-Level Tkinter Import and Rebuild Executable

## Objective
Fix the runtime error reported by the user when launching the application:
```text
Traceback (most recent call last):
  File "app.py", line 787, in <module>
  File "app.py", line 776, in main
  File "app.py", line 296, in initialize_gui
  File "app.py", line 491, in _update_gui_layout_for_mode
NameError: name 'tk' is not defined
```
And recompile the standalone `GenshinOverlay.exe` in the project root.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Root Cause Analysis
In `src/app.py`, `import tkinter as tk` was imported locally inside `initialize_gui()` and `_build_gui_widgets()`.
When `initialize_gui()` called `self._update_gui_layout_for_mode()`, the method tried to access `tk.TOP`, `tk.BOTH`, `tk.X` in module scope where `tk` was not defined, raising `NameError: name 'tk' is not defined`.

---

## Requirements

### 1. Module-Level Tkinter Import in `src/app.py`
- At the top of `src/app.py` (after standard imports), import `tkinter` at the module level:
  ```python
  try:
      import tkinter as tk
      from tkinter import ttk, messagebox
      TKINTER_AVAILABLE = True
  except ImportError:
      tk = None  # type: ignore
      ttk = None  # type: ignore
      messagebox = None  # type: ignore
      TKINTER_AVAILABLE = False
  ```
- Clean up redundant local `import tkinter as tk` statements inside `initialize_gui()` and `_build_gui_widgets()`.
- Ensure `initialize_gui()` checks `if not TKINTER_AVAILABLE:` and logs a warning and falls back to headless if not available.
- Audit all methods in `src/app.py` to ensure all usages of `tk` (`tk.TOP`, `tk.BOTH`, `tk.X`, `tk.LEFT`, `tk.RIGHT`, `tk.Frame`, `tk.Canvas`, etc.) are valid.

### 2. Automated Regression Test
- In `tests/test_app_integration.py`, add a test `test_update_gui_layout_for_mode_no_name_error`:
  - Verify that calling `_update_gui_layout_for_mode(OverlayMode.COMPACT)`, `OverlayMode.EXPANDED`, and `OverlayMode.HIDDEN` with a mock or real `root` executes cleanly without raising `NameError`.

### 3. Verification & Rebuild Executable
- Run `pytest tests/ -v` to ensure all tests pass.
- Recompile the standalone Windows executable using Windows Python:
  `"/mnt/c/Users/Usuario/AppData/Local/Programs/Python/Python312/python.exe" scripts/build_exe.py < /dev/null`
- Verify that `/mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe` is updated.
- Verify running the app with Windows Python in demo mode:
  `"/mnt/c/Users/Usuario/AppData/Local/Programs/Python/Python312/python.exe" -c "from src.app import GenshinOverlayApp; app = GenshinOverlayApp(headless=True); print('App imported and initialized successfully')" < /dev/null`
