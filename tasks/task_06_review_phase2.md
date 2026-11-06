# Code Review Task: Phase 2 — Live Computer Vision Minimap Tracking

## Objective
Perform a rigorous, line-by-line review of the Phase 2 implementation produced by the Developer Agent:
1. Screen capture abstraction (`src/capture/base.py`, `src/capture/win32_capture.py`, `src/capture/__init__.py`).
2. Specialized CV tracking modules:
   - `src/tracking/heading_detector.py`
   - `src/tracking/state_detector.py`
   - `src/tracking/underground_detector.py`
   - `src/tracking/autotracker_service.py`
3. Application GUI updates in `src/app.py` (live tracking modes, player indicator, heading cone, compact HUD).
4. Automated test suites in `tests/`:
   - `tests/test_screen_capture.py`
   - `tests/test_heading_detector.py`
   - `tests/test_state_detector.py`
   - `tests/test_underground_detector.py`
   - `tests/test_autotracker_service.py`
5. Updated benchmark suite `scripts/run_benchmarks.py`, `docs/BENCHMARKS.md`, and `docs/ROADMAP.md`.

---

## Review Criteria
1. **Safety and Non-Invasiveness**:
   - Verify that all screen capture uses external desktop / window capture APIs (BitBlt / GDI / Desktop Duplication) with zero DLL injection, zero memory scanning (`ReadProcessMemory`), and zero game tampering.
2. **Computational Efficiency & Resource Management**:
   - Verify that CV template matching is properly gated by `GameStateDetector` to ensure 0% CV CPU usage during loading screens, cutscenes, and menus.
   - Verify that the background thread runs at a controlled rate (5 Hz) with thread-safe callbacks.
3. **Accuracy and Edge Cases**:
   - Check heading angle mathematics ($[0^\circ, 360^\circ)$), boundary handling, color thresholding robustness.
   - Check resolution scaling calculations across 720p, 1080p, 1440p, and 4K.
4. **Code Quality and Modularity**:
   - Check typing, dataclasses, docstrings, cross-platform mock fallback for Linux/WSL CI.
5. **Testing**:
   - Verify all 77 tests are sound and pass cleanly.

Provide your structured review report and explicit final verdict: "APPROVED" or "CHANGES_REQUESTED".

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`
