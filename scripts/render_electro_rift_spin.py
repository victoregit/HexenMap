"""Rotate only the Electro emblem; reuse the approved rift without changing it."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

import numpy as np
from PIL import Image,ImageFilter
from scripts import render_electro_rift_climax as approved
from scripts import animation_assets as package

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/HexenMap_Electro_Rift_Spin'
START=2.34
PEAK=2.72
END=4.72
MAX_SPEED=360.0  # degrees/second; smooth at 24 FPS for the threefold emblem.


def angular_motion(t):
    """Analytic integral of eased angular speed, continuous at the speed peak."""
    if t<=START:return 0.,0.
    rise=PEAK-START
    if t<PEAK:
        u=(t-START)/rise
        speed=MAX_SPEED*(3*u*u-2*u*u*u)
        angle=MAX_SPEED*rise*(u**3-.5*u**4)
        return angle,speed
    peak_angle=MAX_SPEED*rise*.5
    fall=END-PEAK
    v=float(np.clip((t-PEAK)/fall,0,1))
    speed=MAX_SPEED*(1-3*v*v+2*v*v*v)
    angle=peak_angle+MAX_SPEED*fall*(v-v**3+.5*v**4)
    return angle,speed


def render(t,texture,symbol,blank):
    # The approved renderer receives a transparent emblem: every rift, crack,
    # fragment, timing, deformation and lighting operation stays exactly intact.
    rift=approved.render(t,texture,blank)
    opening=approved.aperture(t)
    visible=approved.envelope(2.34,4.72,t,rise=.22)*approved.ease(.48,.90,opening)
    if visible<=0:return rift
    center=Image.new('RGBA',(512,512));center.alpha_composite(symbol,(214,215))
    angle,_=angular_motion(t)
    # Rotate a padded carrier about the original fixed center to avoid clipping.
    center=center.rotate(-angle,Image.Resampling.BICUBIC,center=(256,256))
    bloom=approved.fade(center.filter(ImageFilter.GaussianBlur(5.5)),visible*(.24+.08*np.sin(t*2.3)))
    result=Image.alpha_composite(rift,bloom)
    return Image.alpha_composite(result,approved.fade(center,visible))


def main():
    for name in ['source','preview']:(OUT/name).mkdir(parents=True,exist_ok=True)
    texture=approved.prepare()
    symbol=Image.open(approved.REF/'electro-symbol-master.png').convert('RGBA').resize((84,82),Image.Resampling.LANCZOS)
    symbol_hash=hashlib.sha256(symbol.tobytes()).hexdigest()
    blank=Image.new('RGBA',symbol.size)
    package.OUT=OUT;package.COUNT=approved.COUNT;package.FPS=approved.FPS
    effects=[render(i/approved.FPS,texture,symbol,blank) for i in range(approved.COUNT)]
    # Validate the user's explicit scope: only the emblem and its existing halo
    # can change. All other pixels match the approved PNGs exactly in every frame.
    outside=np.ones((512,512),bool);outside[176:336,176:336]=False
    for i,effect in enumerate(effects):
        reference=approved.render(i/approved.FPS,texture,symbol)
        previous=Image.alpha_composite(Image.new('RGBA',(512,512)),reference)
        published=Image.alpha_composite(Image.new('RGBA',(512,512)),effect)
        assert np.array_equal(np.asarray(previous)[outside],np.asarray(published)[outside]),f'Rift changed at frame {i}'
    samples=[angular_motion(t)[1] for t in np.linspace(START,PEAK,100)]
    assert all(a<=b+1e-8 for a,b in zip(samples,samples[1:]))
    samples=[angular_motion(t)[1] for t in np.linspace(PEAK,END,100)]
    assert all(a>=b-1e-8 for a,b in zip(samples,samples[1:]))
    assert angular_motion(START)[1]==0 and angular_motion(END)[1]==0
    assert angular_motion(PEAK)[1]==MAX_SPEED
    assert hashlib.sha256(symbol.tobytes()).hexdigest()==symbol_hash
    base=Image.new('RGBA',(512,512))
    frames=package.export('electro_spin',base,effects)
    package.validate(base,{'electro_spin':(frames,effects)})
    # Preview rendering changes only the output folder, preserving its layout.
    approved.OUT=OUT
    approved.preview(frames)
    report=json.loads((OUT/'validation.json').read_text())
    report['scope']={'rift_pixels_unchanged_outside_emblem':True,'frames_compared':120,'symbol_center':[256,256],'symbol_scale_unchanged':True}
    report['rotation']={'direction':'clockwise','start_seconds':START,'peak_seconds':PEAK,'end_seconds':END,'peak_degrees_per_second':MAX_SPEED,'total_degrees':angular_motion(END)[0],'smooth_acceleration_deceleration_verified':True}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for name in ['rift-master.png','electro-symbol-master.png']:
        shutil.copyfile(approved.REF/name,OUT/'source'/name)
    print(OUT)


if __name__=='__main__':main()
