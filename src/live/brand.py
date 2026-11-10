"""User-supplied identity assets, decoded once; animation runs only while visible."""
from bisect import bisect_right
from functools import lru_cache
import time
import json
import math
import tkinter as tk

from PIL import Image, ImageFilter, ImageTk

from src.live.storage import bundle_dir

TRANSPARENT = '#010203'


def badge_symbol_angle(elapsed_seconds):
    """Clockwise only, with smooth acceleration and an exact three-turn loop."""
    frequency=2*math.pi/21
    return (360/7*elapsed_seconds+20/frequency*
            (math.sin(frequency*(elapsed_seconds-17.5))-math.sin(-frequency*17.5)))


def badge_playback(frames,symbol):
    """An unstable open eye is the resting button; the cut is occasional."""
    # Only the rift deforms back and forth. The emblem has its own continuous
    # clockwise timeline and is never read backwards with these frames.
    idle=list(range(65,89))+list(range(87,65,-1))
    result=[frames[idle[i%len(idle)]] for i in range(336)]
    # A slower seven-second closing/cut/opening accent, once per 21s cycle.
    accent=list(range(89,120))+list(range(65))
    for i in range(168):
        index=accent[min(len(accent)-1,i*len(accent)//168)]
        frame=frames[index]
        # Keep a living eye underneath the thin cut and the transparent tail.
        # This also retains a visible clickable center with Win32 color-keying.
        if index<60 or index>96:
            base=frames[idle[(336+i)%len(idle)]]
            strength=min(1.,max(0.,(60-index)/12 if index<60 else (index-96)/12))
            under=base.copy()
            under.putalpha(under.getchannel('A').point(lambda a:round(a*strength)))
            frame=Image.alpha_composite(under,frame)
        result.append(frame)
    size=frames[0].width
    carrier=Image.new('RGBA',(size,size))
    symbol=symbol.resize((max(1,round(size*84/512)),max(1,round(size*82/512))),Image.Resampling.LANCZOS)
    carrier.alpha_composite(symbol,(round(size*214/512),round(size*215/512)))
    for i,frame in enumerate(result):
        emblem=carrier.rotate(-badge_symbol_angle(i/24),Image.Resampling.BICUBIC,center=(size/2,size/2))
        glow=emblem.filter(ImageFilter.GaussianBlur(max(.5,size*5.5/512)))
        glow.putalpha(glow.getchannel('A').point(lambda a:round(a*.3)))
        result[i]=Image.alpha_composite(Image.alpha_composite(frame,glow),emblem)
    durations=[round((i+1)*1000/24)-round(i*1000/24) for i in range(len(result))]
    return tuple(result),tuple(durations)


@lru_cache(maxsize=1)
def badge_frames(size):
    frames=[];durations=[]
    assets=bundle_dir()/'data/assets/brand'
    timing=json.loads((assets/'animations.json').read_text(encoding='utf-8'))
    badge=timing['minimized']
    with Image.open(assets/'minimized-rift.png') as source:
        side=badge['frame_size'];columns=badge['columns']
        for index in range(badge['frames']):
            x=index%columns*side;y=index//columns*side
            frame=source.crop((x,y,x+side,y+side)).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
            frames.append(frame)
            durations.append(badge['durations_ms'][index])
    with Image.open(assets/'electro-symbol.png') as symbol:
        frames,durations=badge_playback(frames,symbol.convert('RGBA'))
    for frame in frames:
        # Windows color-key transparency cannot blend half-transparent edges.
        frame.putalpha(frame.getchannel('A').point(lambda a:255 if a>=128 else 0))
    return frames,durations


def animation_frame(durations,elapsed_ms):
    ends=[];total=0
    for duration in durations:
        total+=duration;ends.append(total)
    position=max(0,elapsed_ms)%total
    index=bisect_right(ends,position)
    return index,max(1,round(ends[index]-position))


def apply_app_icon(root):
    path=bundle_dir()/'data/assets/brand'
    with Image.open(path/'app.png') as source:
        images=[ImageTk.PhotoImage(source.convert('RGBA').resize((n,n),Image.Resampling.LANCZOS),master=root)
                for n in (16,32,48,64,128,256)]
    root.iconphoto(True,*images)
    root._hexen_icons=images
    root.iconbitmap(str(path/'app.ico'))


class AnimatedBadge(tk.Canvas):
    def __init__(self,parent,size=76):
        super().__init__(parent,width=size,height=size,bg=TRANSPARENT,
                         highlightthickness=0,cursor='hand2',takefocus=1)
        frames,self.durations=badge_frames(size)
        self.images=[ImageTk.PhotoImage(frame,master=self) for frame in frames]
        self.item=self.create_image(size/2,size/2,image=self.images[0])
        self.timer=None;self.epoch=None;self._start_offset_ms=0
        self.bind('<Map>',self.start)
        self.bind('<Unmap>',self.stop)
        self.bind('<Destroy>',self.stop)

    def start(self,event=None):
        self.stop();self.epoch=time.monotonic()-self._start_offset_ms/1000
        self._start_offset_ms=0;self._tick()

    def play_from(self,elapsed_ms):
        self._start_offset_ms=elapsed_ms%sum(self.durations)
        if self.winfo_viewable():self.start()

    def stop(self,event=None):
        if self.timer is not None:
            self.after_cancel(self.timer);self.timer=None

    def _tick(self):
        self.timer=None
        if not self.winfo_viewable():return
        index,delay=animation_frame(self.durations,(time.monotonic()-self.epoch)*1000)
        self.itemconfigure(self.item,image=self.images[index])
        self.timer=self.after(delay,self._tick)
