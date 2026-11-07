"""Offline registration check using reference crops, never live-game acceptance."""
import argparse
import gc
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.reference import load_pack
from src.live.regions import RegionalCatalog
from src.live.vision import TerrainMatcher


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/regional-audit/alignment-check.json')
    args=parser.parse_args()
    catalogs=RegionalCatalog(ROOT/'data/community')
    results=[]
    for meta in catalogs.inventory['maps']:
        region,mapid=meta['region_id'],meta['id']
        directory=ROOT/'userData/references/kongying'/region/mapid/'surface'
        row={'region':region,'map':mapid,'kind':'reference_crop_only','passed':False}
        start=time.perf_counter()
        try:
            pack=load_pack(directory,region_id=region,map_id=mapid,layer_id='surface',coordinate_system='kongying-world')
            terrain=max((pack.terrain,*pack.extra_terrain),key=lambda t:abs(np.linalg.det(t.world_to_image[:,:2])))
            matcher=TerrainMatcher(terrain)
            h,w=terrain.image.shape[:2]
            samples=[]
            # A rectangle's center may be empty ocean. Exercise three distinct
            # detailed patches instead of treating featureless water as a CRS bug.
            positions=np.array([key.pt for key in matcher.keys])
            candidates=[]
            for y in range(0,max(1,h-319),120):
                for x in range(0,max(1,w-319),120):
                    count=int(((positions[:,0]>x+12)&(positions[:,0]<x+308)&
                               (positions[:,1]>y+12)&(positions[:,1]<y+308)).sum())
                    candidates.append((count,x,y))
            chosen=[]
            for count,x,y in sorted(candidates,reverse=True):
                if count<30:continue
                if any(abs(x-a)<160 and abs(y-b)<160 for a,b in chosen):continue
                chosen.append((x,y))
                if len(chosen)==3:break
            for x,y in chosen:
                crop=terrain.image[y:y+320,x:x+320]
                fit=matcher.match(crop)
                if fit is None:
                    samples.append({'matched':False});continue
                expected=np.array([[1,0,-x],[0,1,-y]],dtype=float)@np.vstack((terrain.world_to_image,[0,0,1]))
                probes=np.array([[0,0,1],[319,0,1],[0,319,1],[319,319,1]],dtype=float)
                world=probes@np.vstack((cv2.invertAffineTransform(expected),[0,0,1])).T
                error=float(np.linalg.norm(world@fit[0].T-probes[:,:2],axis=1).max())
                samples.append({'matched':True,'max_corner_error_px':error,'residual_p95_px':fit[2]})
            row.update(samples=samples,passed=len(samples)==3 and all(s.get('matched') and s['max_corner_error_px']<3 for s in samples))
            del matcher,pack,terrain
        except (ValueError,OSError,cv2.error) as exc:
            row['error']=str(exc)
        row['seconds']=round(time.perf_counter()-start,2)
        results.append(row)
        print(f"{region}/{mapid}: {'PASS' if row['passed'] else 'FAIL'}",flush=True)
        gc.collect()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'kind':'offline_reference_crops_not_gameplay','maps':results},ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(r['passed'] for r in results) else 2


if __name__=='__main__':sys.exit(main())
