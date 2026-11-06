# Task 07: Fix Benchmark Script State Check Typo

## Objective
In `scripts/run_benchmarks.py` line 182:
Change:
```python
if st not in (GameStateDetector,):
```
To:
```python
if st not in (GameState.LOADING_SCREEN, GameState.CUTSCENE_OR_DIALOGUE):
```
And verify with `pytest tests/` and `python3 scripts/run_benchmarks.py`.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`
