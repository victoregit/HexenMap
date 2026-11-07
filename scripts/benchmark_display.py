"""Reproducible synthetic pan benchmark; explicitly not live-game acceptance."""
from pathlib import Path
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.presentation import DisplayMotion
from src.live.vision import Observation


def benchmark():
    display=DisplayMotion()
    raw_errors=[]; predicted_errors=[]
    # 20 Hz captures, 60 Hz drawing, constant 160 px/s terrain pan.
    for frame in range(60,240):
        now=frame/60
        captured=np.floor(now*20)/20
        obs=Observation('map',captured,np.array([[1.,0.,160*captured],[0.,1.,0.]]),.95,
                        .3,map_id='teyvat',layer_id='surface')
        shown=display.present(obs,now)
        if frame>66:
            raw_errors.append(abs(160*now-obs.world_to_screen[0,2]))
            predicted_errors.append(abs(160*now-shown.world_to_screen[0,2]))
    result={'synthetic_only':True,'scenario':'constant pan; 20 Hz captures / 60 Hz draw',
            'sample_hold_error_mean_px':float(np.mean(raw_errors)),
            'predicted_error_mean_px':float(np.mean(predicted_errors)),
            'live_accepted':False,
            'note':'Does not measure game latency, real optical flow errors, stops or GPU presentation.'}
    output=ROOT/'build/display-benchmark.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': benchmark()
