"""Replay an explicitly exported minimap test at its recorded cadence.

Extract the diagnostic ZIP into a directory first. This is a technical comparison,
not independent positional ground truth or user approval. AutoMark is not replayed;
its enabled state is retained in each diagnostic record for paired live tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.live.budget_vision import BudgetRecognizer
from src.live.motion import MotionRecognizer
from src.live.reference_store import read_spec


def replay(directory, reference, cache, tracker_type):
    manifest = json.loads((reference / 'manifest.json').read_text(encoding='utf-8'))
    rows = [json.loads(line) for line in (directory / 'frames.jsonl').read_text(encoding='utf-8').splitlines()]
    recognizer = BudgetRecognizer([read_spec(reference, manifest['region'], manifest['map_id'],
                                          manifest['layer'], manifest['coordinate_system'])], cache)
    tracker = tracker_type(recognizer)
    start = time.monotonic()
    gaps = []
    gap_start = None
    results = []
    cpu = time.process_time()
    try:
        for row in rows:
            elapsed = row['elapsed_s']
            time.sleep(max(0., start + elapsed - time.monotonic()))
            stamp = start + elapsed
            frame = None
            filename = row.get('image')
            if filename:
                path = (directory / filename).resolve()
                if path.parent != directory.resolve():
                    raise ValueError('Frame path must remain inside the recording directory')
                crop = cv2.imread(str(path))
                shape = tuple(row['captured_shape'])
                if len(shape) != 3 or not (0 < shape[0] <= 4320 and 0 < shape[1] <= 7680):
                    raise ValueError('Invalid captured dimensions')
                if crop is None or crop.shape[0] > shape[0] or crop.shape[1] > shape[1]:
                    raise ValueError('Invalid minimap crop')
                frame = np.zeros(shape, np.uint8)
                frame[:crop.shape[0], :crop.shape[1]] = crop
            tick = time.perf_counter()
            observation = tracker.observe(frame, stamp)
            diagnostic = tracker.diagnostics() if hasattr(tracker, 'diagnostics') else {}
            gameplay = row.get('tracking', {}).get('surface') == 'minimap'
            valid = observation.fresh(stamp) and observation.surface == 'minimap'
            if gameplay and not valid:
                if gap_start is None:
                    gap_start = elapsed
            elif gap_start is not None:
                gaps.append(elapsed - gap_start)
                gap_start = None
            results.append({'elapsed_s':elapsed, 'gameplay':gameplay, 'valid':valid,
                            'cost_ms':(time.perf_counter()-tick)*1000,
                            'automark':row.get('automark'), 'diagnostic':diagnostic})
        if gap_start is not None:
            gaps.append(rows[-1]['elapsed_s'] - gap_start)
    finally:
        tracker.close(wait=True)
        recognizer.close()
    gameplay = [row for row in results if row['gameplay']]
    reasons = Counter(flow.get('reason', 'external') for row in results
                      if not row['valid'] for flow in row['diagnostic'].get('flow', []))
    return {'frames':len(results), 'gameplay_frames':len(gameplay),
            'valid_gameplay_fraction':sum(row['valid'] for row in gameplay)/len(gameplay) if gameplay else None,
            'gaps_s':gaps, 'rejection_counts':dict(reasons), 'cpu_seconds':time.process_time()-cpu,
            'foreground_ms_p95':float(np.percentile([r['cost_ms'] for r in results],95)) if results else None,
            'independent_ground_truth':False, 'live_approved':False, 'records':results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--reference', type=Path, default=Path('userData/references/appsample/as-map-2/surface'))
    parser.add_argument('--cache', type=Path, default=Path('userData/cache/references'))
    parser.add_argument('--baseline-python', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    trackers = [('current', MotionRecognizer)]
    if args.baseline_python:
        spec = importlib.util.spec_from_file_location('minimap_replay_baseline', args.baseline_python)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        trackers.insert(0, ('baseline', module.MotionRecognizer))
    report = {name:replay(args.recording,args.reference,args.cache,tracker) for name,tracker in trackers}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
