# Task 03: Polishing Reviewer Suggestions

## Objective
Implement the non-blocking recommendations provided by the Code Reviewer Agent in `task_02_code_review.md`:
1. In `README.md`: Add a prominent "Display Mode Configuration & Troubleshooting" section emphasizing that Genshin Impact must be run in **Borderless Windowed Mode** (`Alt + Enter` or in-game Settings > Graphics > Display Mode) because Windows Desktop Window Manager (DWM) overlays cannot overlay exclusive fullscreen games without intrusive hooking.
2. In `src/app.py`: In `initialize_gui`, add a robust top-level HWND resolution fallback for Windows (e.g. checking `ctypes.windll.user32.GetParent(hwnd)` if `hwnd` is a child canvas window) to ensure `WS_EX_TRANSPARENT` applies to the window frame on all Windows versions.
3. Verify with `pytest tests/` to confirm all 45 tests continue to pass.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`
