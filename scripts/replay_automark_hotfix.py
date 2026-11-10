"""Replay qualified local recordings; resized variants are explicitly synthetic."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json,time
import cv2,numpy as np
from src.live.automark import ChestSignals
from src.live.vision import Observation


def main():
    root=Path('userData/automark');manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    sessions=[*( (p,True) for p in manifest['validation']['positive_sessions']),
              *( (p,False) for p in manifest['validation']['negative_sessions'])]
    report=[]
    for source,positive in sessions:
        folder=Path(source.replace('\\','/'));frames=json.loads((folder/'session.json').read_text())['frames']
        for width,height in [(1366,768),(1920,1080),(2560,1440)]:
            signals=ChestSignals(root);events=[];times=[]
            for entry in frames:
                frame=cv2.imread(str(folder/entry['file']));original=(frame.shape[1],frame.shape[0])
                if original!=(width,height):frame=cv2.resize(frame,(width,height),interpolation=cv2.INTER_CUBIC)
                stamp=100+entry['elapsed_s'];start=time.perf_counter()
                reading=signals.measure(frame);times.append((time.perf_counter()-start)*1000)
                obs=Observation('minimap',stamp,np.eye(2,3),.99,.2,(100,100,60),(0,0),map_id='as-map-2',layer_id='surface')
                event=signals.advance(reading,obs,stamp,gameplay_confirmed=True)
                if event:events.append(entry['file'])
            assert len(events)==int(positive),(folder,width,height,events)
            row={'session':folder.name,'resolution':[width,height],'synthetic_resize':(width,height)!=original,
                 'events':events,'frames':len(frames),'mean_signal_ms':round(sum(times)/len(times),2)}
            report.append(row);print(json.dumps(row),flush=True)
    Path('build/automark-hotfix-replay.json').write_text(json.dumps({'scope':'Signal sequence only; supplied localized observations; no collection writes',
        'results':report},indent=2),encoding='utf-8')


if __name__=='__main__':main()
