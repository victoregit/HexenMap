"""Short non-blocking transition from the real panel into its approved rift badge."""
from functools import lru_cache
import time
import tkinter as tk

from PIL import Image,ImageDraw,ImageFilter,ImageTk

from src.live.brand import TRANSPARENT
from src.live.storage import bundle_dir

DURATION_MS=820
HANDOFF_MS=3000


def ease(a,b,t):
    value=max(0.,min(1.,(t-a)/(b-a)))
    return value*value*(3-2*value)


@lru_cache(maxsize=1)
def handoff_frame():
    import json
    assets=bundle_dir()/'data/assets/brand'
    config=json.loads((assets/'animations.json').read_text(encoding='utf-8'))['minimized']
    elapsed=0;index=0
    for index,duration in enumerate(config['durations_ms']):
        if elapsed+duration>HANDOFF_MS:break
        elapsed+=duration
    side=config['frame_size'];columns=config['columns']
    with Image.open(assets/config['file']) as atlas:
        x=index%columns*side;y=index//columns*side
        return atlas.crop((x,y,x+side,y+side)).convert('RGBA')


def transition_frame(snapshot,poster,progress,size,source_origin,target_center,compact_size,source_size=None):
    """Draw one frame in overlay coordinates without touching live widgets."""
    p=max(0.,min(1.,progress))
    canvas=Image.new('RGBA',size)
    w,h=snapshot.size if snapshot is not None else source_size;ox,oy=source_origin
    start=(ox+w/2,oy+h/2)
    travel=ease(.60,1,p)
    center=tuple(a+(b-a)*travel for a,b in zip(start,target_center))
    shrink=ease(.54,1,p)
    width=max(1,round(w+(compact_size-w)*shrink))
    height=max(1,round(h*(1-ease(.23,.67,p))))
    if snapshot is not None and p<.67:
        # Preview-only image: runtime clips live controls instead of capturing them.
        left=round((w-width)/2);top=round(ease(.23,.67,p)*h/2)
        body=snapshot.crop((left,top,left+width,top+height))
        opacity=1-ease(.51,.67,p)
        if opacity<1:body.putalpha(body.getchannel('A').point(lambda alpha:round(alpha*opacity)))
        canvas.alpha_composite(body,(round(start[0]-width/2),round(start[1]-height/2)))
    # The sword cut crosses the panel before its upper/lower halves collapse.
    cut_opacity=ease(0,.06,p)*(1-ease(.34,.65,p))
    if cut_opacity>0:
        light=Image.new('RGBA',size);draw=ImageDraw.Draw(light)
        span=w*.95
        end=-span/2+span*ease(0,.25,p)
        def point(x):return center[0]+x,center[1]-x*.11
        left=point(-span/2);right=point(end)
        draw.line([left,right],fill=(133,62,255,round(220*cut_opacity)),width=7)
        light=light.filter(ImageFilter.GaussianBlur(3.0))
        draw=ImageDraw.Draw(light)
        draw.line([left,right],fill=(235,213,255,round(255*cut_opacity)),width=2)
        canvas=Image.alpha_composite(canvas,light)
    opacity=ease(.32,.62,p)
    if opacity>0:
        side=max(1,round(w+(compact_size-w)*shrink))
        rift=poster.resize((side,side),Image.Resampling.LANCZOS)
        if opacity<1:rift.putalpha(rift.getchannel('A').point(lambda alpha:round(alpha*opacity)))
        canvas.alpha_composite(rift,(round(center[0]-side/2),round(center[1]-side/2)))
    return canvas


class PanelCollapseTransition:
    def __init__(self,root,native,bounds,target,compact_size,on_done):
        self.root=root;self.native=native;self.on_done=on_done
        self.poster=handoff_frame();self._root_hidden=False
        self.compact_size=compact_size;self.timer=None;self.active=True
        left,top,right,bottom=bounds;tx,ty=target
        self.source_size=(right-left,bottom-top)
        margin=12
        x=min(left,tx)-margin;y=min(top,ty)-margin
        width=max(right,tx+compact_size)-x+margin
        height=max(bottom,ty+compact_size)-y+margin
        self.size=(width,height);self.origin=(left-x,top-y)
        self.target=(tx+compact_size/2-x,ty+compact_size/2-y)
        self.window=tk.Toplevel(root);self.window.withdraw()
        try:
            self.window.overrideredirect(True);self.window.attributes('-topmost',True)
            self.window.attributes('-transparentcolor',TRANSPARENT)
            self.window.configure(bg=TRANSPARENT)
            self.window.geometry(f'{width}x{height}{x:+d}{y:+d}')
            self.canvas=tk.Canvas(self.window,width=width,height=height,bg=TRANSPARENT,highlightthickness=0)
            self.canvas.pack();self.item=self.canvas.create_image(0,0,anchor='nw')
            self.window.bind('<Destroy>',self._destroyed)
            self.window.protocol('WM_DELETE_WINDOW',self.finish)
            self.window.bind('<Button-1>',lambda event:self.finish())
            self.window.update_idletasks()
            native.panel(self.window.winfo_id())
            if hasattr(native,'transition_panel'):native.transition_panel(self.window.winfo_id())
            self._paint(0)
        except Exception:
            self.cancel();raise

    def _paint(self,progress):
        w,h=self.source_size
        closed=ease(.23,.67,progress)
        width=round(w+(self.compact_size-w)*ease(.54,1,progress))
        top=round(h*closed/2);bottom=max(top,round(h-h*closed/2))
        self.native.panel_mask(self.root.winfo_id(),((w-width)/2,top,(w+width)/2,bottom))
        if progress>=.67 and not self._root_hidden:
            self.root.withdraw();self._root_hidden=True
        frame=transition_frame(None,self.poster,progress,self.size,self.origin,self.target,self.compact_size,self.source_size)
        # Same Win32 color-key treatment as the existing collapsed badge.
        frame.putalpha(frame.getchannel('A').point(lambda alpha:255 if alpha>=128 else 0))
        self.image=ImageTk.PhotoImage(frame,master=self.window)
        self.canvas.itemconfigure(self.item,image=self.image)

    def start(self):
        self.started=time.monotonic()
        self.window.deiconify();self.window.lift()
        self.timer=self.window.after(16,self._tick)

    def _tick(self):
        self.timer=None
        if not self.active:return
        elapsed=(time.monotonic()-self.started)*1000
        if elapsed>=DURATION_MS:self.finish();return
        try:
            self._paint(elapsed/DURATION_MS)
            self.timer=self.window.after(16,self._tick)
        except (tk.TclError,OSError):self.finish()

    def _destroyed(self,event):
        if event.widget is self.window:self.cancel()

    def finish(self):
        if not self.active:return
        callback=self.on_done;self.on_done=None
        self.cancel()
        if callback:callback()

    def cancel(self):
        self.active=False;self.on_done=None
        try:self.native.panel_mask(self.root.winfo_id(),None)
        except (OSError,tk.TclError):pass
        window=self.window;self.window=None
        if window is None:return
        if self.timer is not None:
            try:window.after_cancel(self.timer)
            except tk.TclError:pass
            self.timer=None
        try:window.destroy()
        except tk.TclError:pass
