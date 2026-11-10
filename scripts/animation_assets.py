"""Export and validate approved RGBA animation assets."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'
SIZE=512
COUNT=48
FPS=24
AA=3
IVORY=(255,245,220)

def blank():
    return Image.new('RGBA',(SIZE*AA,SIZE*AA))


def line(layer,p,q,color,width,opacity=1):
    if opacity<=0:return
    ImageDraw.Draw(layer).line(tuple(round(v*AA) for v in (*p,*q)),
                              fill=(*color,round(255*min(1,opacity))),width=max(1,round(width*AA)))


def star(layer,p,r,opacity=1,color=IVORY):
    if opacity<=0:return
    x,y=p
    shape=[(x,y-r),(x+r*.23,y-r*.23),(x+r,y),(x+r*.23,y+r*.23),
           (x,y+r),(x-r*.23,y+r*.23),(x-r,y),(x-r*.23,y-r*.23)]
    ImageDraw.Draw(layer).polygon([(round(a*AA),round(b*AA)) for a,b in shape],
                                 fill=(*color,round(255*min(1,opacity))))


def finish(core,glow):
    # The glow is a small secondary layer, never a blur applied to the emblem.
    glow=glow.filter(ImageFilter.GaussianBlur(2.4*AA))
    result=Image.alpha_composite(glow,core)
    return result.resize((SIZE,SIZE),Image.Resampling.LANCZOS)


def timings():
    # PNG/WebP use ms; distribute rounding so the cycle is exactly 2000 ms.
    return [round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(COUNT)]


def export(name,base,effects):
    directory=OUT/name
    for child in ['frames','effects']:(directory/child).mkdir(parents=True,exist_ok=True)
    rows=(len(effects)+7)//8
    sheet=Image.new('RGBA',(4096,512*rows))
    effect_sheet=sheet.copy()
    frames=[]
    for i,effect in enumerate(effects):
        frame=Image.alpha_composite(base,effect)
        frames.append(frame)
        frame.save(directory/'frames'/f'frame_{i:03}.png')
        effect.save(directory/'effects'/f'effect_{i:03}.png')
        xy=(i%8*512,i//8*512)
        sheet.paste(frame,xy);effect_sheet.paste(effect,xy)
    sheet.save(directory/f'{name}_spritesheet.png')
    effect_sheet.save(directory/f'{name}_effects_spritesheet.png')
    frames[0].save(directory/f'{name}.webp',save_all=True,append_images=frames[1:],
                   duration=timings(),loop=0,lossless=True,exact=True,minimize_size=False)
    # Transparent GIF alternative: single palette and explicit background disposal.
    swatches=Image.new('RGB',(512*8,512*rows))
    for i,frame in enumerate(frames):
        bg=Image.new('RGBA',frame.size,'#171922');bg.alpha_composite(frame)
        swatches.paste(bg.convert('RGB'),(i%8*512,i//8*512))
    palette=swatches.quantize(colors=255)
    gifs=[]
    for frame in frames:
        gif=frame.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE)
        indices=np.asarray(gif).copy()
        indices[np.asarray(frame.getchannel('A'))<96]=255
        output=Image.fromarray(indices,mode='P')
        output.putpalette(palette.getpalette()[:765]+[0,0,0])
        gifs.append(output)
    gifs[0].save(directory/f'{name}.gif',save_all=True,append_images=gifs[1:],
                  duration=[(round((i+1)*100/FPS)-round(i*100/FPS))*10 for i in range(len(frames))],loop=0,transparency=255,disposal=2,optimize=False)
    # Dark/light playback previews retain smooth alpha blending and common colors.
    for label,color in [('dark','#171922'),('light','#f4f1ea')]:
        previews=[]
        for frame in frames:
            bg=Image.new('RGBA',frame.size,color);bg.alpha_composite(frame)
            previews.append(bg.convert('RGB'))
        previews[0].save(OUT/'preview'/f'{name}_{label}.webp',save_all=True,
                       append_images=previews[1:],duration=timings(),loop=0,lossless=True)
    return frames


def validate(base,animations):
    fingerprint=hashlib.sha256(base.tobytes()).hexdigest()
    report={'base_sha256':fingerprint,'size':[512,512],'fps':FPS,'frames':COUNT,
            'duration_ms':sum(timings()),'spritesheet_size':[4096,512*((COUNT+7)//8)],
            'base_is_immutable':True,'animations':{}}
    for name,(frames,effects) in animations.items():
        differences=[]
        for frame,effect in zip(frames,effects):
            assert hashlib.sha256(base.tobytes()).hexdigest()==fingerprint
            expected=Image.alpha_composite(base,effect)
            assert frame.tobytes()==expected.tobytes()
            a=np.asarray(effect.getchannel('A'))
            assert not a[:5].any() and not a[-5:].any() and not a[:,:5].any() and not a[:,-5:].any()
            untouched=a==0
            assert np.array_equal(np.asarray(frame)[untouched],np.asarray(base)[untouched])
        # Compare visible premultiplied colors, not irrelevant RGB under alpha=0.
        differences=[]
        first=previous=None
        for frame in frames:
            a=np.asarray(frame).astype(np.float32)
            a[:,:,:3]*=a[:,:,3,None]/255
            if first is None:first=a
            if previous is not None:differences.append(float(np.abs(previous-a).mean()))
            previous=a
        differences.append(float(np.abs(previous-first).mean()))
        with Image.open(OUT/name/f'{name}.webp') as decoded:
            assert decoded.n_frames==COUNT
            assert decoded.info.get('loop')==0
        with Image.open(OUT/name/f'{name}_spritesheet.png') as atlas:
            assert atlas.size==(4096,512*((COUNT+7)//8))
            for i,frame in enumerate(frames):
                cell=atlas.crop((i%8*512,i//8*512,i%8*512+512,i//8*512+512))
                assert cell.tobytes()==frame.tobytes()
        report['animations'][name]={'frames':len(frames),'seam_mean_delta':differences[-1],
                                    'max_mean_delta':max(differences),'unaffected_pixels_exact':True}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')



