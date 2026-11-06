# Review Task 17: Verification of Marco A Georeferenced Overlay & Documentation

## Objective
Perform a rigorous, thorough code and documentation review of the deliverables produced for Marco A based on the user's instructions in `ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md` and `GenshinGemWish_AUDITORIA_E_REMODELACAO.md`.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Artifacts to Review

### 1. Technical Documentation
- `/mnt/d/Projects/GenshinGemWish/docs/CURRENT_GAP_ANALYSIS.md`:
  - Check thoroughness of codebase gap analysis, line references, architectural blockers (anti-contamination of capture, low-level hotkeys without focus, dynamic scaling).
- `/mnt/d/Projects/GenshinGemWish/docs/GAME_MAP_REGISTRATION.md`:
  - Check mathematical formulation of coordinate transformations (Canonical World -> Screen Pixel Space), affine transformation matrix, RANSAC, confidence score, and low-confidence rejection rules.
- `/mnt/d/Projects/GenshinGemWish/docs/REMODEL_ROADMAP.md`:
  - Check Milestones A through D, acceptance criteria, and pixel error thresholds.

### 2. Domain & Projection Implementation
- `/mnt/d/Projects/GenshinGemWish/src/map/registration.py`:
  - Mathematical correctness of `MapRegistration`, least squares, RANSAC, reprojection error computation, and threshold rejection.
- `/mnt/d/Projects/GenshinGemWish/src/map/expanded_projector.py`:
  - Correctness of `ExpandedMapProjector`, pan/zoom deltas, frustum culling, transparent pin rendering without modifying the underlying game map.
- `/mnt/d/Projects/GenshinGemWish/src/app.py`:
  - Verification of the bug fix: `get_filtered_markers` must return 0 markers when `selected_categories` is empty.
  - Property `active_marker_ids` as single source of truth.

### 3. Visual Verification Script & Output Evidence
- `/mnt/d/Projects/GenshinGemWish/scripts/verify_marco_a.py`:
  - Code that executes the calibration on real user screenshots (`data/reference/01_interactive_map_chests.png` and `data/reference/03_native_expanded_map.png`).
- Generated image evidence:
  - `/mnt/d/Projects/GenshinGemWish/data/reference/marco_a_overlay_result.png`
  - `/mnt/d/Projects/GenshinGemWish/data/reference/marco_a_comparison.png`
- Measured pixel alignment error (mean $< 2.0\text{ px}$, p95 $< 4.0\text{ px}$).

### 4. Automated Tests & Executable
- `/mnt/d/Projects/GenshinGemWish/tests/test_expanded_map_projection.py` (86 tests total passing).
- `/mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe` and `README.md`.

Provide your structured review report and explicit final verdict: "APPROVED" or "CHANGES_REQUESTED".
