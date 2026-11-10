"""Short non-blocking transition from the real panel into its approved rift badge."""
from functools import lru_cache
import math
import time
import tkinter as tk

from PIL import Image,ImageDraw,ImageFilter,ImageTk

from src.live.brand import TRANSPARENT

DURATION_MS=820
HANDOFF_MS=3000


def ease(a,b,t):
    value=max(0.,min(1.,(t-a)/(b-a)))
    return value*value*(3-2*value)


@lru_cache(maxsize=1)
def handoff_frame():
    from src.live.brand import badge_frames,animation_frame
    frames,durations=badge_frames(192)
    index,_=animation_frame(durations,HANDOFF_MS)
    return frames[index].copy()


def sword_cut(size,center,panel_width,p):
    """A tapered travelling blade opens into two Electro eyelids, then dissolves."""
    power=ease(0,.045,p)*(1-ease(.40,.63,p))
    layer=Image.new('RGBA',size)
    if power<=0:return layer
    width=panel_width*.97
    reveal=ease(.015,.22,p)
    opening=ease(.19,.43,p)*(1-ease(.43,.64,p))
    # Small local surface: bloom never blurs a full window-sized image.
    padding=14;local_width=math.ceil(width)+padding*2
    local_height=max(100,math.ceil(width*.25+64))
    glow=Image.new('RGBA',(local_width,local_height));core=Image.new('RGBA',glow.size)
    aura=ImageDraw.Draw(glow);ink=ImageDraw.Draw(core)
    def point(u,side=0):
        x=padding+width*u
        taper=math.sin(math.pi*u)**1.2
        bend=side*18*opening*taper
        return x,local_height/2-(u-.5)*width*.25+bend
    steps=max(2,round(100*reveal))
    for side in (-1,1):
        for index in range(steps):
            a=index/100;b=min(reveal,(index+1)/100)
            if b<=a:continue
            taper=math.sin(math.pi*(a+b)/2)**.65
            alpha=round(255*power*taper)
            points=[point(a,side),point(b,side)]
            aura.line(points,fill=(111,44,255,alpha),width=max(1,round(8*taper)))
            ink.line(points,fill=(177,113,255,alpha),width=max(1,round(3*taper)))
            ink.line(points,fill=(249,239,255,alpha),width=1)
    # The white blade head moves with the cut; there is no stationary flash.
    if .015<p<.26:
        x,y=point(reveal)
        head=round(255*power*(1-ease(.21,.26,p)))
        aura.ellipse((x-7,y-4,x+7,y+4),fill=(167,88,255,head))
        ink.line([(x-10,y),(x+4,y)],fill=(255,248,255,head),width=2)
    # A few anchored splinters read as a tear in space, rather than confetti.
    for u,side,delay in ((.22,-1,.20),(.70,1,.24),(.82,-1,.27)):
        energy=ease(delay,delay+.055,p)*(1-ease(delay+.10,delay+.23,p))
        if energy<=0:continue
        x,y=point(u,side);length=13*energy
        branch=[(x,y),(x+4,y+side*length*.45),(x+2,y+side*length)]
        aura.line(branch,fill=(133,62,255,round(200*energy)),width=3)
        ink.line(branch,fill=(214,172,255,round(200*energy)),width=1)
    bloom=glow.filter(ImageFilter.GaussianBlur(4.5))
    bloom=Image.alpha_composite(bloom,glow.filter(ImageFilter.GaussianBlur(1.3)))
    effect=Image.alpha_composite(bloom,core)
    layer.alpha_composite(effect,(round(center[0]-local_width/2),round(center[1]-local_height/2)))
    return layer


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
    # The blade is confined to the pre-collapse accent. The approved eye and
    # final badge are composited below without altering their pixels or timing.
    if 0<p<.64:
        canvas=Image.alpha_composite(canvas,sword_cut(size,center,w,p))
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
            # Tk's -12 means an offset from the right/bottom edge, not -12
            # desktop pixels. Keep the sign of the coordinate after an explicit
            # '+' so the margin also works at zero and on negative monitors.
            self.window.geometry(f'{width}x{height}+{x}+{y}')
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
