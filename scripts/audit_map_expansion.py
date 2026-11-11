"""Offline integrity/alignment audit. Synthetic crops are NOT in-game acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.appsample_catalog import project
from src.live.automatic_maps import AutomaticMapSearch,MapRouter
from src.live.map_registry import maps,installed_scopes
from src.live.reference_store import read_spec
from src.live.vision import Observation


def main():
    root=ROOT/'userData/references/appsample'
    expected=[(key,layer) for key,row in maps().items()
              for layer in ['surface',*[l['layer_id'] for l in row.get('layers',[])]]]
    scopes=installed_scopes(root)
    if set(scopes)!=set(expected):raise ValueError('Incomplete installed map coverage')
    from scripts.package_portable import referenced
    results=[]
    for scope in scopes:
        directory=root/scope[0]/scope[1]
        data=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        spec=read_spec(directory,'appsample',*scope,'appsample-webmercator-z14',0)
        for e in referenced(data):
            path=(directory/e['file']).resolve()
            if not path.is_relative_to(directory.resolve()):raise ValueError('Reference path outside map')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=e['sha256']:raise ValueError(f'Hash mismatch: {path}')
        if scope[1]!='surface':
            layer=next(l for l in maps()[scope[0]]['layers'] if l['layer_id']==scope[1])
            bounds=layer['bounds'];a,b=project(bounds['west'],bounds['north']);c,d=project(bounds['east'],bounds['south'])
            raster=spec.rasters[0]
            np.testing.assert_allclose(raster.matrix@np.array([a,b,1]),[0,0],atol=1e-6)
            np.testing.assert_allclose(raster.matrix@np.array([c,d,1]),[raster.width,raster.height],atol=1e-6)
        results.append({'map':scope[0],'layer':scope[1],'rasters':len(spec.rasters),'integrity':'passed',
                        'live_validation':data.get('validation','unknown')})
    # Test descriptor geometry at several independent positions inside reference
    # rasters. This catches transforms/crop offsets, but not source-to-game drift.
    geometric=[]
    sift=cv2.SIFT_create(nfeatures=1000,contrastThreshold=.025)
    for map_id in maps():
        path=root/map_id/'surface/manifest.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        image=cv2.imread(str(path.parent/data['terrain']['file']),cv2.IMREAD_GRAYSCALE)
        kp,desc=sift.detectAndCompute(image,None)
        matcher=cv2.BFMatcher()
        accepted=0
        # Crops centered on distant strong landmarks, rather than black margins.
        centers=[]
        for point in kp:
            if all(np.linalg.norm(np.array(point.pt)-p)>500 for p in centers):centers.append(np.array(point.pt))
            if len(centers)==3:break
        for center in centers:
            x=max(0,min(image.shape[1]-512,round(center[0])-256));y=max(0,min(image.shape[0]-512,round(center[1])-256))
            crop=image[y:y+512,x:x+512];qk,qd=sift.detectAndCompute(crop,None)
            if qd is None:continue
            pairs=[a for a,b in matcher.knnMatch(qd,desc,k=2) if a.distance<.7*b.distance]
            if len(pairs)<6:continue
            src=np.array([kp[p.trainIdx].pt for p in pairs],np.float32)
            dst=np.array([qk[p.queryIdx].pt for p in pairs],np.float32)
            matrix,inliers=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=2)
            if matrix is None:continue
            expected_matrix=np.array([[1,0,-x],[0,1,-y]],float)
            probes=np.array([[x,y,1],[x+512,y,1],[x,y+512,1]],float)
            error=float(np.max(np.linalg.norm(probes@matrix.T-probes@expected_matrix.T,axis=1)))
            if error<=3:accepted+=1
        if accepted<3:raise ValueError(f'Insufficient geometric checks: {map_id} ({accepted}/3)')
        geometric.append({'map':map_id,'reference_crop_checks':accepted,'limit_px':3,'independent_game_capture':False})
    process=psutil.Process();before=process.memory_info().rss
    search=AutomaticMapSearch(scopes,('as-map-2','surface'),root,ROOT/'userData/cache/references',None)
    stable=Observation('map',0,np.eye(2,3),.9,.1,map_id='as-map-2',layer_id='surface')
    start=time.perf_counter()
    for _ in range(20000):search.tick(None,0,stable)
    overhead_us=(time.perf_counter()-start)*1e6/20000
    stable_delta=(process.memory_info().rss-before)/1024**2
    assert search.router is None and search.future is None
    search.close()
    before=process.memory_info().rss
    router=MapRouter(scopes,root)
    routing_delta=(process.memory_info().rss-before)/1024**2
    if len(router.owners)>1200*len(maps()):raise ValueError('Routing descriptor budget exceeded')
    if stable_delta>32:raise ValueError('Stable discovery memory budget exceeded')
    report={'maps':len(maps()),'scopes':len(scopes),'references':results,'geometry':geometric,
            'stable_search_overhead_us':overhead_us,'stable_additional_rss_MiB':stable_delta,
            'routing_rss_MiB':routing_delta,'routing_descriptors':len(router.owners),
            'in_game_acceptance':'pending: new maps need independent game captures and fullscreen/windowed testing'}
    output=ROOT/'build/map-expansion-audit.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('references','geometry')},ensure_ascii=False))


if __name__=='__main__':main()
