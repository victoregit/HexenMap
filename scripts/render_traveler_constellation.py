"""HexenMap motion based on inspected in-game references, with immutable masters."""
from pathlib import Path
import json
import math
import shutil
import zipfile

import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

from scripts import animation_assets as pipeline

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'data/source/brand'
OUT=ROOT/'artifacts/HexenMap_Traveler_Loading'
COUNT=48
SIZE=512
# Pixel coordinates inspected on the actual 710x566 Hydro Traveler capture.
SOURCE_NODES=[(284,97),(350,211),(157,253),(207,449),(463,513),(594,260)]
EDGES=list(zip(range(5),range(1,6)))


def smooth(a,b,t):
    v=np.clip((t-a)/(b-a),0,1)
    return v*v*(3-2*v)


def extract_traveler():
    original=Image.open(REF/'traveler-hydro.png').convert('RGBA')
    image=np.asarray(original).astype(float)
    r,g,b=image[:,:,:3].transpose(2,0,1)
    local_background=cv2.GaussianBlur(g,(0,0),6)
    alpha=np.uint8(np.clip((g-local_background-3)*8,0,255)*((g-r>15)&(b-g>12)&(g>55)))
    count,labels,stats,_=cv2.connectedComponentsWithStats(np.uint8(alpha>30))
    keep=np.zeros(alpha.shape,np.uint8)
    for index in range(1,count):
        if stats[index,cv2.CC_STAT_AREA]>=65:keep[labels==index]=255
    keep=cv2.dilate(keep,np.ones((3,3),np.uint8))
    alpha=np.minimum(alpha,keep)
    matte=Image.fromarray(alpha)
    erase=ImageDraw.Draw(matte)
    # Separate the gameplay node links and stellar flares from the ornamental
    # illustration; these connections are animated below at their exact positions.
    for a,b in EDGES:erase.line([SOURCE_NODES[a],SOURCE_NODES[b]],fill=0,width=7)
    for x,y in SOURCE_NODES:erase.ellipse((x-29,y-29,x+29,y+29),fill=0)
    matte=matte.filter(ImageFilter.GaussianBlur(.30))
    rgba=Image.new('RGBA',original.size,(72,159,205,0));rgba.putalpha(matte)
    crop=(105,12,630,546)
    artwork=rgba.crop(crop).resize((424,432),Image.Resampling.LANCZOS)
    layer=Image.new('RGBA',(512,512));layer.alpha_composite(artwork,(44,40))
    nodes=[(44+(x-crop[0])*424/(crop[2]-crop[0]),40+(y-crop[1])*432/(crop[3]-crop[1])) for x,y in SOURCE_NODES]
    return layer,nodes


def opacity(image,value):
    copy=image.copy()
    copy.putalpha(copy.getchannel('A').point(lambda a:round(a*float(np.clip(value,0,1)))))
    return copy


def loading_effect(t,art,nodes):
    fade=float(1-smooth(.80,1,t))
    artwork_visibility=float(smooth(.00,.18,t))*.64*fade
    result=opacity(art,artwork_visibility)
    aa=3;core=Image.new('RGBA',(1536,1536));glow=core.copy()
    progress=float(smooth(.06,.66,t))*5
    for i,(a,b) in enumerate(EDGES):
        amount=float(np.clip(progress-i,0,1))
        if not amount:continue
        p=nodes[a];q=nodes[b]
        end=tuple(x+(y-x)*amount for x,y in zip(p,q))
        pipeline.line(glow,p,end,(48,213,253),5.8,fade*.43)
        pipeline.line(core,p,end,(59,214,246),2.2,fade*.95)
        pipeline.line(core,p,end,(166,253,255),.75,fade*.88)
    sweep=float(smooth(.64,.83,t))*5
    if .64<t<.84:
        edge=min(4,int(sweep));v=sweep-edge
        p,q=nodes[edge],nodes[edge+1]
        end=tuple(a+(b-a)*v for a,b in zip(p,q))
        previous=tuple(a+(b-a)*max(0,v-.16) for a,b in zip(p,q))
        pipeline.line(glow,previous,end,(194,249,255),6,fade*.38)
        pipeline.line(core,previous,end,(232,255,255),2.0,fade*.95)
    for i,node in enumerate(nodes):
        appear=float(smooth(i-1-.10,i-1+.12,progress)) if i else float(smooth(0,.06,t))
        visibility=appear*fade
        arrival=math.exp(-((progress-(i-1))/.24)**2)*.32 if i else 0
        radius=10.5+arrival*7+(math.exp(-((sweep-i)/.28)**2)*1.4 if t>.64 else 0)
        # Reference-style multi-ray stellar nodes: white core, warm inner edge,
        # turquoise outer light and a faint horizontal optical streak.
        pipeline.star(glow,node,radius*1.9,visibility*.53,color=(77,226,255))
        pipeline.star(core,node,radius,visibility,color=(255,216,169))
        pipeline.star(core,node,radius*.69,visibility,color=(255,254,242))
        x,y=node
        pipeline.line(glow,(x-29,y),(x+29,y),(163,228,255),1.7,visibility*.35)
        pipeline.line(core,(x-14,y),(x+14,y),(249,235,237),.65,visibility*.60)
    # No artwork regeneration: same isolated game illustration in every frame.
    glow=glow.filter(ImageFilter.GaussianBlur(3.2*aa))
    light=Image.alpha_composite(glow,core).resize((512,512),Image.Resampling.LANCZOS)
    return Image.alpha_composite(result,light)


def main():
    for name in ['source','preview']:(OUT/name).mkdir(parents=True,exist_ok=True)
    art,nodes=extract_traveler()
    effects=[loading_effect(i/48,art,nodes) for i in range(48)]
    pipeline.OUT=OUT;pipeline.COUNT=48;pipeline.FPS=24
    base=Image.new('RGBA',(512,512))
    frames=pipeline.export('loading',base,effects)
    pipeline.validate(base,{'loading':(frames,effects)})
    art.save(OUT/'source/traveler-ornament.png')
    shutil.copyfile(REF/'traveler-hydro.png',OUT/'source/traveler-hydro.png')
    print(OUT)


if __name__=='__main__':main()
