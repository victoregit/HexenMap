"""Map shortcut cycling through locally bundled nation emblems."""
import time
import tkinter as tk
from functools import lru_cache

from PIL import Image, ImageTk

from src.live.nation_selector import icon_image

NATIONS=('mondstadt','liyue','inazuma','sumeru','fontaine','natlan','snezhnaya')
HOLD_MS=2600
FADE_MS=360


@lru_cache(maxsize=56)
def emblem(region,size):
    return icon_image(region,size)


class NationMapButton(tk.Canvas):
    def __init__(self,parent,command,**kwargs):
        super().__init__(parent,width=28,height=28,highlightthickness=0,
                         cursor='hand2',takefocus=1,**kwargs)
        self.index=0;self.job=None;self.fade_started=None;self.photo=None
        for event in ('<Button-1>','<Return>','<space>'):
            self.bind(event,lambda event:command())
        self.bind('<Map>',self.start)
        self.bind('<Unmap>',self.stop)
        self.bind('<Destroy>',self.stop)
        self.bind('<Configure>',lambda event:self.draw())

    def draw(self,amount=0):
        width=max(1,self.winfo_width());height=max(1,self.winfo_height())
        size=max(1,round(min(width,height)*.82))
        current=emblem(NATIONS[self.index],size)
        if amount:
            following=emblem(NATIONS[(self.index+1)%len(NATIONS)],size)
            current=Image.blend(current,following,amount)
        self.photo=ImageTk.PhotoImage(current,master=self)
        self.delete('nation-emblem')
        self.create_image(width/2,height/2,image=self.photo,tags='nation-emblem')

    def start(self,event=None):
        if self.job is not None:return
        self.draw();self.job=self.after(HOLD_MS,self.fade)

    def fade(self):
        self.job=None
        if not self.winfo_ismapped():return
        now=time.monotonic()
        if self.fade_started is None:self.fade_started=now
        amount=min(1,(now-self.fade_started)*1000/FADE_MS)
        self.draw(amount*amount*(3-2*amount))
        if amount>=1:
            self.index=(self.index+1)%len(NATIONS);self.fade_started=None
            self.job=self.after(HOLD_MS,self.fade)
        else:self.job=self.after(33,self.fade)

    def stop(self,event=None):
        if self.job is not None:
            self.after_cancel(self.job);self.job=None
        self.fade_started=None
