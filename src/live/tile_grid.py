"""Provider-neutral bounded tile rectangles."""
from src.live.i18n import tr as _tr
def partition_bounds(bounds, side=16, overlap=1):
    """Bound raster memory while retaining common terrain at chunk seams."""
    if side <= overlap or overlap < 0:
        raise ValueError(_tr('Invalid tile partition size'))
    x0,y0,x1,y1=bounds
    if x1<x0 or y1<y0:
        raise ValueError(_tr('Empty tile rectangle'))
    result=[]
    x=x0
    while x<=x1:
        right=min(x+side-1,x1);y=y0
        while y<=y1:
            bottom=min(y+side-1,y1)
            result.append((x,y,right,bottom))
            if bottom==y1: break
            y=bottom-overlap+1
        if right==x1: break
        x=right-overlap+1
    return result
