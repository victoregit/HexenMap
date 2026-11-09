"""Native minimap player-glyph validation; no directional guidance."""
import math
import cv2
import numpy as np


def glyph_area_range(height):
    # The player glyph scales with the HUD, not with the detected map radius.
    # A large minimap or a faint view cone must not require a larger arrow.
    scale=height/1080
    return max(5,18*scale*scale),max(40,500*scale*scale)


def valid_glyph(component):
    contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:return False
    contour=max(contours,key=cv2.contourArea);hull=cv2.convexHull(contour)
    perimeter=cv2.arcLength(hull,True)
    if perimeter<=0:return False
    vertices=cv2.approxPolyDP(hull,perimeter*.035,True)
    area=cv2.contourArea(hull)
    return 3<=len(vertices)<=6 and area>0 and cv2.contourArea(contour)/area>=.5


def pointer_shape(frame,circle,center_fraction=.12):
    if circle is None or frame is None or frame.ndim!=3:return None
    x,y,r=circle;h,w=frame.shape[:2];margin=max(12,round(r*.27))
    left=max(0,round(x)-margin);top=max(0,round(y)-margin)
    crop=frame[top:min(h,round(y)+margin+1),left:min(w,round(x)+margin+1)]
    if crop.size==0:return None
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    # Cyan water/ice can join the glyph into one huge component. Segment by
    # local chroma contrast instead of treating the entire lake as the arrow.
    chroma=hsv[:,:,1].astype(np.float32)*hsv[:,:,2]/255.
    hue=cv2.inRange(hsv,(80,70,140),(110,255,255))
    core=max(5,round(r*.15));cx=round(x)-left;cy=round(y)-top
    center=chroma[max(0,cy-core):cy+core+1,max(0,cx-core):cx+core+1]
    if center.size==0:return None
    threshold=max(100.,float(center.max())*.88)
    mask=np.uint8((hue>0)&(chroma>=threshold))*255
    legacy=cv2.inRange(hsv,(80,100,160),(110,255,255))
    minimum,maximum=glyph_area_range(h)
    for candidate_mask,lo,hi,shape_check in ((legacy,.015*r*r,.07*r*r,False),(mask,minimum,maximum,True)):
        count,labels,stats,centers=cv2.connectedComponentsWithStats(candidate_mask)
        candidates=[]
        for i in range(1,count):
            _,_,aw,ah,area=stats[i];px,py=centers[i]+[left,top]
            component=np.uint8(labels==i)*255
            if (lo<area<hi and .5<aw/max(ah,1)<2 and (not shape_check or valid_glyph(component))
                    and math.hypot(px-x,py-y)<max(5,r*center_fraction)):
                candidates.append(i)
        if len(candidates)==1:
            return np.uint8(labels==candidates[0])*255,centers[candidates[0]]
    return None
