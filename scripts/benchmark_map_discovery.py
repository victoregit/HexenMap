"""Paired stable-path timing on an existing local capture, without controlling Genshin."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.automatic_maps import AutomaticMapSearch
from src.live.budget_vision import BudgetRecognizer
from src.live.map_registry import installed_scopes
from src.live.motion import MotionRecognizer
from src.live.reference_store import read_spec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with np.load(args.capture,allow_pickle=False) as archive:
        shape=tuple(int(v) for v in archive['shape'])
        frames=archive['frames'][:100].copy()
    root=ROOT/'userData/references/appsample'
    pack=read_spec(root/'as-map-2/surface','appsample','as-map-2','surface','appsample-webmercator-z14',0)
    recognizer=BudgetRecognizer([pack],ROOT/'userData/cache/references','light')
    motion=MotionRecognizer(recognizer)
    search=AutomaticMapSearch(installed_scopes(root),('as-map-2','surface'),root,ROOT/'userData/cache/references',pack)
    baseline=[];additional=[]
    image=np.zeros(shape,np.uint8)
    try:
        for crop in frames:
            image.fill(0);image[:crop.shape[0],:crop.shape[1]]=crop
            stamp=time.monotonic();start=time.perf_counter()
            obs=motion.observe(image,stamp)
            duration=time.perf_counter()-start
            if obs.fresh(stamp):
                start=time.perf_counter();search.tick(image,stamp,obs)
                baseline.append(duration*1000);additional.append((time.perf_counter()-start)*1000)
            time.sleep(max(.001,.05-duration))
        if len(baseline)<10:raise RuntimeError('Not enough independently captured stable frames for comparison')
        ratio=float(np.mean(additional)/np.mean(baseline))
        report={'capture':str(args.capture),'stable_frames':len(baseline),
                'existing_tracker_mean_ms':float(np.mean(baseline)),
                'existing_tracker_p95_ms':float(np.percentile(baseline,95)),
                'automatic_search_additional_mean_ms':float(np.mean(additional)),
                'stable_processing_increase_percent':ratio*100,
                'target_maximum_increase_percent':10,
                'background_search_started':search.future is not None,
                'scope':'paired stable-path replay of Teyvat; does not validate newly added maps in game'}
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report))
        if ratio>.1:raise RuntimeError('Stable processing target exceeded')
    finally:
        search.close();motion.close(wait=True);recognizer.close()


if __name__=='__main__':main()
