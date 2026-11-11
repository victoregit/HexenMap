"""Bounded photo viewport: zoom renders only the visible crop, never a huge bitmap."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk
from src.live.theme import BG,MUTED,place_dialog


class PhotoViewer:
    def __init__(self,parent,image,on_close=lambda:None,*,native=None,game=None):
        self.image=image.copy();self.on_close=on_close;self.zoom=1.;self.offset=None;self.job=None
        self.window=tk.Toplevel(parent);self.window.title('Foto do local · Hexen Map')
        if native is not None and game is not None:
            self.window.withdraw();self.window.overrideredirect(True)
        self.window.configure(bg=BG);self.window.minsize(300,240)
        toolbar=ttk.Frame(self.window,padding=8);toolbar.pack(fill='x')
        ttk.Button(toolbar,text='Ajustar à janela',command=self.fit,takefocus=False).pack(side='left')
        ttk.Button(toolbar,text='Fechar',command=self.close,takefocus=False).pack(side='right')
        hint=ttk.Label(toolbar,text='Roda: zoom · arraste para mover · Esc: fechar',foreground=MUTED,wraplength=380)
        hint.pack(side='left',padx=10,fill='x',expand=True)
        hint.bind('<Configure>',lambda event:hint.configure(wraplength=max(100,event.width)) if int(hint.cget('wraplength'))!=max(100,event.width) else None)
        self.canvas=tk.Canvas(self.window,bg=BG,highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.fit())
        self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<Button-1>',self.start_drag)
        self.canvas.bind('<B1-Motion>',self.drag)
        self.window.bind('<Escape>',lambda e:(self.close(),'break')[1])
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        if native is not None and game is not None:
            from src.overlay.window_tracker import GameWindowRect
            width=min(900,max(1,game.width-24));height=min(650,max(1,game.height-24))
            x=game.x+(game.width-width)//2;y=game.y+(game.height-height)//2
            self.window.geometry(f'{width}x{height}{x:+d}{y:+d}');self.window.update_idletasks()
            from src.live.noactivate import materialize_controls
            materialize_controls(self.window)
            hwnd=native.popup(self.window.winfo_id(),game)
            native.place(hwnd,GameWindowRect(x,y,width,height))
        else:place_dialog(self.window,parent,(900,650))
        self.fit()

    def scale(self):
        return min(self.canvas.winfo_width()/self.image.width,self.canvas.winfo_height()/self.image.height)*self.zoom
    def fit(self):
        self.zoom=1.;self.offset=None;self.schedule()
    def schedule(self):
        if self.job is None:self.job=self.window.after(16,self.draw)
    def draw(self):
        self.job=None;w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height());scale=self.scale()
        if scale<=0:return
        if self.offset is None:self.offset=((w-self.image.width*scale)/2,(h-self.image.height*scale)/2)
        ox,oy=self.offset
        left=max(0,int(-ox/scale));top=max(0,int(-oy/scale))
        right=min(self.image.width,int((w-ox)/scale)+1);bottom=min(self.image.height,int((h-oy)/scale)+1)
        self.canvas.delete('all')
        if right<=left or bottom<=top:return
        image=self.image.crop((left,top,right,bottom))
        image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.LANCZOS)
        self.photo=ImageTk.PhotoImage(image,master=self.window)
        self.canvas.create_image(ox+left*scale,oy+top*scale,image=self.photo,anchor='nw')
    def wheel(self,event):
        if self.offset is None:self.draw()
        old=self.scale();ox,oy=self.offset
        self.zoom=max(1.,min(8.,self.zoom*(1.2 if event.delta>0 else 1/1.2)))
        ratio=self.scale()/old;self.offset=(event.x-(event.x-ox)*ratio,event.y-(event.y-oy)*ratio)
        self.schedule();return 'break'
    def start_drag(self,event):self.origin=(event.x,event.y,self.offset or (0,0))
    def drag(self,event):
        x,y,(ox,oy)=self.origin;self.offset=(ox+event.x-x,oy+event.y-y);self.schedule()
    def contains(self,x,y):
        return (self.window.winfo_rootx()<=x<self.window.winfo_rootx()+self.window.winfo_width()
                and self.window.winfo_rooty()<=y<self.window.winfo_rooty()+self.window.winfo_height())
    def close(self):
        if self.job is not None:self.window.after_cancel(self.job)
        self.window.destroy();self.image=None;self.photo=None;self.on_close()
