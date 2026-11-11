"""Compare adjacent-frame motion on a local minimap recording (not absolute tracking)."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.motion import MotionRecognizer,follow
from src.live.vision import Observation,detect_circle,gray


def validate(directory):
    rows=[json.loads(line) for line in (directory/'frames.jsonl').read_text(encoding='utf-8').splitlines()]
    motion=MotionRecognizer(SimpleNamespace(pack=SimpleNamespace()))
    previous=previous_row=circle=None
    records=[]
    try:
        for index,row in enumerate(rows):
            if not row.get('image') or row.get('tracking',{}).get('surface')!='minimap':
                previous=previous_row=circle=None
                continue
            path=(directory/row['image']).resolve()
            if path.parent!=directory.resolve():raise ValueError('Frame outside recording directory')
            crop=cv2.imread(str(path))
            h,w,channels=row['captured_shape']
            if not (0<h<=4320 and 0<w<=7680 and channels==3):raise ValueError('Invalid recorded geometry')
            if crop is None or crop.shape[0]>h or crop.shape[1]>w:raise ValueError('Invalid recorded crop')
            frame=np.zeros((h,w,channels),np.uint8)
            frame[:crop.shape[0],:crop.shape[1]]=crop
            if circle is None:circle=detect_circle(frame)
            if circle is None:continue
            current=gray(frame)
            if previous is not None and previous.shape==current.shape:
                obs=Observation('minimap',previous_row['elapsed_s'],np.eye(2,3),.95,circle=circle)
                tick=time.perf_counter();raw=follow(previous,current,obs,row['elapsed_s']);raw_ms=(time.perf_counter()-tick)*1000
                motion.flow_attempts=[]
                tick=time.perf_counter();recovered=motion._follow(previous,current,obs,row['elapsed_s']);new_ms=(time.perf_counter()-tick)*1000
                records.append({'frame':index,'elapsed_s':row['elapsed_s'],'raw_valid':raw is not None,
                    'recovered_valid':recovered is not None,'raw_ms':raw_ms,'new_ms':new_ms,
                    'attempts':list(motion.flow_attempts)})
            previous=current;previous_row=row
    finally:motion.close()
    return {'kind':'adjacent-frame motion; each pair starts from identity, without cumulative uncertainty',
        'absolute_tracking_validated':False,'independent_ground_truth':False,'live_approved':False,
        'pairs':len(records),'raw_valid':sum(r['raw_valid'] for r in records),
        'recovered_valid':sum(r['recovered_valid'] for r in records),
        'recovered_failures':dict(Counter(r['attempts'][-1].get('reason') for r in records if not r['recovered_valid'])),
        'original_path_p95_ms':float(np.percentile([r['raw_ms'] for r in records],95)) if records else None,
        'recovery_path_p95_ms':float(np.percentile([r['new_ms'] for r in records],95)) if records else None,
        'records':records}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=validate(args.recording)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))
