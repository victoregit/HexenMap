"""User-supplied identity assets, decoded once; animation runs only while visible."""
from bisect import bisect_right
from functools import lru_cache
import time
import json
import tkinter as tk

from PIL import Image, ImageTk

from src.live.storage import bundle_dir

TRANSPARENT = '#010203'


@lru_cache(maxsize=1)
def badge_frames(size):
    frames=[];durations=[]
    assets=bundle_dir()/'data/assets/brand'
    timing=json.loads((assets/'animations.json').read_text(encoding='utf-8'))
    badge=timing['minimized']
    with Image.open(assets/badge['file']) as source:
        side=badge['frame_size'];columns=badge['columns']
        for index in range(badge['frames']):
            x=index%columns*side;y=index//columns*side
            frame=source.crop((x,y,x+side,y+side)).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
            # Windows color-key transparency cannot blend half-transparent edges.
            frame.putalpha(frame.getchannel('A').point(lambda a:255 if a>=128 else 0))
            frames.append(frame)
            durations.append(badge['durations_ms'][index])
    return tuple(frames),tuple(durations)


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
