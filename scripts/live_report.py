"""Summarize recorded live recognition; never turn synthetic tests into acceptance."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import statistics


def summarize(path: Path) -> dict:
    with path.open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    durations={"map":0.0,"minimap":0.0,"hidden":0.0}
    for left,right in zip(rows,rows[1:]):
        delta=float(right["monotonic_s"])-float(left["monotonic_s"])
        # Exclude pauses between runs; never count time that wasn't sampled.
        if 0<delta<=1:
            durations[left["surface"]]+=delta
    valid=[row for row in rows if row["surface"] in {"map","minimap"}]
    active=durations["map"]+durations["minimap"]
    coverage={}
    for left,right in zip(rows,rows[1:]):
        delta=float(right['monotonic_s'])-float(left['monotonic_s'])
        if 0<delta<=1 and left['surface'] in {'map','minimap'}:
            key='/'.join(left.get(k,'legacy') for k in ['region','map','layer'])
            coverage[key]=coverage.get(key,0)+delta
    return {
        "sampled_seconds":round(sum(durations.values()),1),
        "recognized_seconds":round(active,1),
        "by_surface_seconds":{k:round(v,1) for k,v in durations.items()},
        "recognition_latency_median_ms":statistics.median(float(r["latency_ms"]) for r in valid) if valid else None,
        "thirty_minutes_recognized":active>=1800,
        "recognized_by_coverage_seconds":{k:round(v,1) for k,v in coverage.items()},
        "acceptance_complete":False,
        "note":"Recognition time is not proof of item accuracy, user exploration, click-through, or game FPS impact.",
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    user=Path(__file__).resolve().parents[1]/'userData'
    default=user/'live-session-v2.csv'
    if not default.exists(): default=user/'live-session.csv'
    parser.add_argument("log",type=Path,nargs="?",default=default)
    args=parser.parse_args()
    print(json.dumps(summarize(args.log),indent=2))
