"""Latest-only preparation of exact, transparent click masks; no Tk/GDI here."""
from concurrent.futures import ThreadPoolExecutor,CancelledError
from functools import lru_cache
import struct
import time
import numpy as np
import cv2
from src.live.marker_art import LEGACY


def nearby_placements(pins,x,y,radius=120):
    """Limit click-mask work, without changing which symbols are rendered."""
    result=[]
    for pin in pins:
        geometry=getattr(pin,'geometry',LEGACY)
        left,top,right,bottom=geometry.bounds(round(pin.x),round(pin.y))
        dx=max(left-x,0,x-right);dy=max(top-y,0,y-bottom)
        if dx*dx+dy*dy<=radius*radius:
            result.append((round(pin.x),round(pin.y),geometry))
    return tuple(result)


@lru_cache(maxsize=256)
def geometry_mask(geometry):
    mask=np.zeros((geometry.bottom-geometry.top,geometry.right-geometry.left),np.uint8)
    for a,c,b,d in geometry.rows or ((geometry.left,geometry.top,geometry.right,geometry.bottom),):
        mask[c-geometry.top:d-geometry.top,a-geometry.left:b-geometry.left]=1
    return mask


def placement_data(placements,cancelled=lambda:False):
    if not placements:return b''
    boxes=[g.bounds(x,y) for x,y,g in placements]
    left=min(b[0] for b in boxes);top=min(b[1] for b in boxes)
    right=max(b[2] for b in boxes);bottom=max(b[3] for b in boxes)
    if (right-left)*(bottom-top)>16*1024**2:
        return region_data((box for x,y,g in placements for box in g.rectangles(x,y)),cancelled)
    mask=np.zeros((bottom-top,right-left),np.uint8);stamps={}
    for index,((x,y,g),(a,c,b,d)) in enumerate(zip(placements,boxes)):
        if index%64==0 and cancelled():raise CancelledError()
        if id(g) not in stamps:stamps[id(g)]=geometry_mask(g)
        view=mask[c-top:d-top,a-left:b-left]
        cv2.bitwise_or(view,stamps[id(g)],dst=view)
    edges=np.diff(np.pad(mask,((0,0),(1,1))),axis=1)
    ys,starts=np.nonzero(edges==1);_,ends=np.nonzero(edges==255)
    rows,indices=np.unique(ys,return_index=True);rectangles=[];last=-2;band=None;start=0
    band_spans=[]
    def finish(end):
        rectangles.extend((a+left,start+top,b+left,end+top) for a,b in band_spans)
    for n,y in enumerate(rows):
        if cancelled():raise CancelledError()
        begin=indices[n];end=indices[n+1] if n+1<len(indices) else len(starts)
        key=(starts[begin:end].tobytes(),ends[begin:end].tobytes())
        if key!=band or y!=last+1:
            finish(last+1);band=key;start=int(y)
            band_spans=list(zip(starts[begin:end].tolist(),ends[begin:end].tolist()))
        last=int(y)
    finish(last+1)
    return encode_region(rectangles)


def encode_region(rectangles):
    if not rectangles:return b''
    data=np.asarray(rectangles,dtype=np.int32)
    bounds=(int(data[:,0].min()),int(data[:,1].min()),int(data[:,2].max()),int(data[:,3].max()))
    return struct.pack('<IIIIiiii',32,1,len(rectangles),data.nbytes,*bounds)+data.tobytes()


def region_data(boxes,cancelled=lambda:False):
    rows={}
    for index,(left,top,right,bottom) in enumerate(boxes):
        if index%256==0 and cancelled():raise CancelledError()
        if right<=left:continue
        for y in range(top,bottom):rows.setdefault(y,[]).append((left,right))
    rectangles=[];band=None;last=-2;start=0
    def finish(bottom):
        if band:
            rectangles.extend((a,start,b,bottom) for a,b in band)
    for y,spans in sorted(rows.items()):
        if cancelled():raise CancelledError()
        merged=[]
        for left,right in sorted(spans):
            if merged and left<=merged[-1][1]:merged[-1]=(merged[-1][0],max(right,merged[-1][1]))
            else:merged.append((left,right))
        if merged!=band or y!=last+1:
            finish(last+1);band=merged;start=y
        last=y
    finish(last+1)
    return encode_region(rectangles)


class InputRegions:
    def __init__(self):
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='PinInput')
        self.key=None;self.future=None;self.generation=0;self.build_ms=0.
        self.ready_key=None;self.ready_raw=None;self.ready_points=frozenset()
        self.scope=None
    def get(self,key,placements,scope=None):
        if scope!=self.scope:self.cancel();self.scope=scope
        if self.future is not None and self.future.done():
            try:
                raw,self.build_ms=self.future.result()
                self.ready_key=self.key;self.ready_raw=raw;self.ready_points=self.points
            except CancelledError:pass
            self.future=None
        if key!=self.key:
            self.generation+=1;generation=self.generation;self.key=key
            self.points=frozenset((x,y,id(g)) for x,y,g in placements)
            if self.future:self.future.cancel()
            def build():
                started=time.perf_counter()
                raw=placement_data(placements,lambda:generation!=self.generation)
                return raw,(time.perf_counter()-started)*1000
            self.future=self.pool.submit(build)
        # A completed partial reveal remains safe if every covered shape is
        # still drawn at exactly the same position. Newly drawn pins join later.
        if self.ready_raw is not None and self.ready_points.issubset(self.points):return self.ready_raw
        return None
    def cancel(self):
        self.generation+=1;self.key=None
        if self.future:self.future.cancel()
        self.future=None
        self.ready_key=None;self.ready_raw=None;self.ready_points=frozenset()
        self.scope=None
    def close(self):
        self.cancel();self.pool.shutdown(wait=False,cancel_futures=True)
