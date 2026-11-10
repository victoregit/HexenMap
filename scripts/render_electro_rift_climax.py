"""Slower unstable Electro rift: mesh distortion, growing cracks, and timed climax."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import zipfile

import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
from scripts import animation_assets as package

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/HexenMap_Electro_Rift_Spin'
REF=ROOT/'data/source/brand'
FPS=24
COUNT=120
DURATION=5.0
SIZE=512
Y,X=np.mgrid[:SIZE,:SIZE].astype(np.float32)


def array_smooth(a,b,t):
    value=np.clip((t-a)/(b-a),0,1)
    return value*value*(3-2*value)


def fade(image,alpha):
    result=image.copy()
    result.putalpha(result.getchannel('A').point(lambda value:round(value*float(np.clip(alpha,0,1)))))
    return result


def ease(a,b,t):
    v=float(np.clip((t-a)/(b-a),0,1))
    return v*v*(3-2*v)


def envelope(start,end,t,rise=.22):
    return ease(start,start+(end-start)*rise,t)*(1-ease(end-(end-start)*.35,end,t))


def aperture(t):
    keys=[(.86,0),(1.30,.04),(1.78,.095),(2.06,.19),(2.48,1.02),(2.72,1.0),(3.84,1.0),(4.98,0)]
    if t<=keys[0][0]:return 0.
    for (ta,va),(tb,vb) in zip(keys,keys[1:]):
        if ta<t<=tb:
            s=ease(ta,tb,t)
            # Acceleration into the release, rather than a uniform opening.
            if ta==2.06:s=((t-ta)/(tb-ta))**1.6
            return va+(vb-va)*s
    return 0.


def prepare():
    image=Image.open(REF/'rift-master.png').convert('RGBA')
    alpha=image.getchannel('A').point(lambda value:0 if value<5 else value)
    image.putalpha(alpha);image=image.crop(alpha.getbbox())
    texture=image.resize((450,164),Image.Resampling.LANCZOS).resize((436,176),Image.Resampling.LANCZOS)
    pad=Image.new('RGBA',(512,512));pad.alpha_composite(texture,(38,168))
    rgba=np.asarray(pad).astype(np.float32)/255
    rgba[:,:,:3]*=rgba[:,:,3,None]
    return rgba


def remap_rift(texture,t,opening):
    # Different portions of the rim distort at different speeds and amplitudes.
    # This is a material deformation, not a moving/scaled rigid eye image.
    x=(X-256)/218
    wave=4.9*np.sin(9.2*x-3.2*t)+2.4*np.sin(18.4*x+4.1*t+.8)
    wave*=np.maximum(0,1-x*x)**.6
    asym=1+.095*np.sin(7*x-2.6*t)+.035*np.sin(21*x+3.4*t)
    local_height=max(.006,opening)*asym
    shift_y=wave*min(1,opening*2)
    shear=(2.2*np.sin((Y-256)*.045+2*t)+1.6*np.sin(12*x-1.8*t))*min(1,opening*2)
    width=1+.014*math.sin(2.1*t+.3)
    map_x=((X-256)/width+256+shear).astype(np.float32)
    map_y=((Y-256-shift_y)/local_height+256).astype(np.float32)
    warped=cv2.remap(texture,map_x,map_y,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    a=np.clip(warped[:,:,3],0,1)
    rgb=np.divide(warped[:,:,:3],a[:,:,None],out=np.zeros_like(warped[:,:,:3]),where=a[:,:,None]>.0001)
    # Advect light along the torn rim, leaving the dark void largely untouched.
    brightness=np.max(rgb,axis=2)
    rim=np.clip((brightness-.27)/.5,0,1)
    moving=np.sin((X-256)*.035-4.7*t)+.35*np.sin((Y-256)*.09+3.1*t)
    gain=1+rim*(.12*moving+.12*math.exp(-((t-2.46)/.18)**2))
    rgb=np.clip(rgb*gain[:,:,None],0,1)
    # A cold, almost black cavity creates contrast with the hot Electro edge.
    visibility=envelope(.82,5,t,rise=.1)
    result=np.dstack([rgb,np.clip(a*visibility,0,1)])
    return Image.fromarray(np.uint8(np.clip(result*255,0,255)))


def slash(t):
    u=X-256;v=Y-256
    head=-218+ease(.32,.93,t)*436
    reveal=(1-array_smooth(head-3,head+2,u))*array_smooth(-232,-214,u)
    edge=1-array_smooth(207,234,np.abs(u))
    power=ease(0,.32,t)*(1-ease(1.85,2.60,t))
    # Once cut, the hairline holds under pressure before the main rupture.
    charge=.35+.65*ease(.92,2.10,t)
    core=np.exp(-(v/1.0)**2)*reveal*edge*power*charge
    aura=np.exp(-(v/7.5)**2)*reveal*edge*power*.30
    tip=np.exp(-((u-head)/7)**2-(v/3.3)**2)*edge*power*.8
    pulse=math.exp(-((t-2.27)/.13)**2)
    release=np.exp(-(v/4.2)**2)*(1-array_smooth(165,228,np.abs(u)))*pulse*.45
    alpha=np.clip(core+aura+tip+release,0,1)
    white=np.clip(core+tip+release,0,1)
    rgb=np.array([86,41,250])[None,None,:]*(1-white[:,:,None])+np.array([247,242,255])[None,None,:]*white[:,:,None]
    return Image.fromarray(np.uint8(np.dstack([rgb,alpha*255])))


# Timed, fixed-seed discharge events. Each crack grows, bends and dies; none is
# regenerated randomly per frame or stays frozen for the full open-eye phase.
CRACKS=[
 (.85,1.40,-.60,-1,23), (1.22,1.80,.54,1,28), (1.66,2.22,-.23,1,33),
 (2.08,2.68,.18,-1,55), (2.18,2.88,-.63,-1,48), (2.35,3.04,.57,1,53),
 (2.77,3.43,-.39,1,41), (3.13,3.79,.46,-1,44), (3.49,4.10,-.69,1,35),
 (3.89,4.47,.10,-1,43), (4.22,4.83,.59,1,29),
]


def edge_y(x,side,t,opening):
    # Follow the actual deformed eye's general lid boundary, with subtle travel.
    normalized=(x-256)/218
    hull=max(0,1-normalized*normalized)**1.35
    bend=(4.9*math.sin(9.2*normalized-3.2*t)+2.4*math.sin(18.4*normalized+4.1*t+.8))*max(0,1-normalized*normalized)**.6
    return 256+side*53*opening*hull+bend*min(1,opening*2)


def electricity(t,opening,material):
    raster=np.asarray(material)
    def anchor(x,side):
        column=int(np.clip(round(x),3,508))
        band=raster[:,column-3:column+4]
        hot=(band[:,:,0]>100)&(band[:,:,1]>60)&(band[:,:,3]>48)
        rows=np.where(hot)[0]
        if len(rows)>5:
            return float(np.quantile(rows,.12 if side<0 else .88))
        return edge_y(x,side,t,opening)
    core=package.blank();glow=package.blank()
    for i,(start,end,position,side,length) in enumerate(CRACKS):
        if not start<t<end:continue
        age=(t-start)/(end-start)
        strength=envelope(start,end,t)*(.78+.22*math.sin(math.pi*age))
        grow=ease(0,.46,age)
        x=256+position*205+5*math.sin(3*t+i)
        y=anchor(x,side)
        direction=-1 if position<0 else 1
        reach=length*grow
        # The fracture has angular, hand-authored bends, not sinusoidal noodles.
        points=[(x,y),(x+direction*8,y+side*reach*.26),
                (x-direction*(5+2*math.sin(8*age+i)),y+side*reach*.56),
                (x+direction*11,y+side*reach*.73),
                (x+direction*19,y+side*reach)]
        for p,q in zip(points,points[1:]):
            package.line(glow,p,q,(119,55,255),5.0,strength*.43)
            package.line(core,p,q,(175,128,255),1.9,strength*.90)
            package.line(core,p,q,(243,225,255),.70,strength*.90)
        branch=points[2]
        tip=(branch[0]-direction*16*grow,branch[1]+side*11*grow)
        package.line(glow,branch,tip,(105,104,255),3,strength*.23)
        package.line(core,branch,tip,(190,166,255),.75,strength*.75)
    # A few slivers detach during the climax, echoing cut, fractured space.
    draw=ImageDraw.Draw(core)
    for i,(position,side) in enumerate([(-.71,-1),(-.38,1),(.35,-1),(.68,1)]):
        birth=2.25+i*.11;end=birth+.83
        if not birth<t<end:continue
        age=(t-birth)/(end-birth);strength=envelope(birth,end,t)*.78
        x=256+position*205+math.copysign(9*age,position)
        y=anchor(x,side)+side*(6+22*age)
        angle=.3+i*.9+age*.6
        length=11+4*i;vertices=[]
        for a,b in [(0,-length*.5),(3,length*.18),(-2,length*.5)]:
            xx=x+a*math.cos(angle)-b*math.sin(angle)
            yy=y+a*math.sin(angle)+b*math.cos(angle)
            vertices.append((round(xx*3),round(yy*3)))
        draw.polygon(vertices,fill=(67,32,126,round(135*strength)))
        draw.line(vertices+[vertices[0]],fill=(183,135,255,round(220*strength)),width=2)
    glow=glow.filter(ImageFilter.GaussianBlur(2.1*3))
    return Image.alpha_composite(glow,core).resize((512,512),Image.Resampling.LANCZOS)


def inner_energy(t,opening):
    image=Image.new('RGBA',(512,512))
    visibility=envelope(2.05,4.55,t)*min(1,opening)*.23
    if visibility<=0:return image
    a=np.asarray(image).copy();x=(X-256)/140;y=(Y-256)/46
    rho=x*x+y*y
    band=np.exp(-((rho-.7-.08*math.sin(t*2))/.13)**2)
    # A faint interior depth contour, displaced with the cavity, not a spinner.
    alpha=np.uint8(band*visibility*255)
    a[:,:,:3]=[82,30,158];a[:,:,3]=alpha
    return Image.fromarray(a)


def render(t,texture,symbol):
    opening=aperture(t)
    result=slash(t)
    material=Image.new('RGBA',(512,512))
    if opening>.001:
        material=remap_rift(texture,t,opening)
        result=Image.alpha_composite(result,material)
        result=Image.alpha_composite(result,inner_energy(t,opening))
    result=Image.alpha_composite(result,electricity(t,opening,material))
    # All material and discharge layers share one fixed direction of the slash.
    result=result.rotate(8,Image.Resampling.BICUBIC,center=(256,256))
    visible=envelope(2.34,4.72,t,rise=.22)*ease(.48,.90,opening)
    if visible>0:
        # The symbol remains anchored, with an evolving halo behind it.
        center=Image.new('RGBA',(512,512));center.alpha_composite(symbol,(214,215))
        bloom=fade(center.filter(ImageFilter.GaussianBlur(5.5)),visible*(.24+.08*math.sin(t*2.3)))
        result=Image.alpha_composite(result,bloom)
        result=Image.alpha_composite(result,fade(center,visible))
    return result


def preview(frames):
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    durations=package.timings()
    for label,color in [('dark','#100b19'),('light','#eae7ef')]:
        sequence=[]
        for frame in frames:
            bg=Image.new('RGBA',(512,512),color);bg.alpha_composite(frame);sequence.append(bg.convert('RGB'))
        sequence[0].save(OUT/'preview'/f'electro_climax_{label}.webp',save_all=True,append_images=sequence[1:],duration=durations,loop=0,lossless=True)
    sequence=[]
    for i,frame in enumerate(frames):
        bg=Image.new('RGBA',(920,420),'#100b19');d=ImageDraw.Draw(bg)
        for size,x,y,label in [(384,4,0,'Ampliado'),(192,470,100,'192 px'),(76,758,155,'76 px')]:
            bg.alpha_composite(frame.resize((size,size),Image.Resampling.LANCZOS),(x,y));d.text((x+size/2,384),label,font=font,fill='#e5dafa',anchor='mt')
        sequence.append(bg.convert('RGB'))
    sequence[0].save(OUT/'preview/electro_climax_sizes.webp',save_all=True,append_images=sequence[1:],duration=durations,loop=0,lossless=True)
    film=Image.new('RGBA',(2048,584),'#100b19');d=ImageDraw.Draw(film)
    for column,(sec,label) in enumerate([(1.12,'1 · Corte suspenso'),(2.10,'2 · Pressão / rasgo'),(2.63,'3 · Ruptura'),(3.36,'4 · Olho instável')]):
        film.alpha_composite(frames[round(sec*24)],(column*512,0));d.text((column*512+256,540),label,font=font,fill='#e5dafa',anchor='mt')
    film.save(OUT/'preview/electro_climax_sequence.png')


# The renderer is shared by the approved spinning-emblem export.
