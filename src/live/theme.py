"""Lunar presentation tokens and reusable Tk assets; no per-capture styling work."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk

BG='#171923'
SURFACE='#202330'
HOVER='#2B2F40'
SELECTED='#332E46'
TEXT='#F0EDF7'
MUTED='#B2B4C4'
ACCENT='#B8A2EE'
ON_ACCENT='#20172F'
CHAMPAGNE='#D5BC83'
BORDER='#3B4053'
SUCCESS='#99CBB4'
FONT='Segoe UI'
CONTROL_RADIUS=12
SURFACE_RADIUS=16


def panel_size(scale,bounds):
    """Logical 360x540, fitted to the available desktop without offscreen controls."""
    left,top,right,bottom=bounds
    scale=max(1.,min(3.,float(scale)))
    return min(round(360*scale),max(240,right-left-16)),min(round(540*scale),max(300,bottom-top-round(48*scale)))


def rounded(canvas,box,*,radius=12,**options):
    x0,y0,x1,y1=box;r=max(0,min(radius,(x1-x0)/2,(y1-y0)/2))
    return canvas.create_polygon(x0+r,y0,x1-r,y0,x1,y0,x1,y0+r,x1,y1-r,x1,y1,x1-r,y1,
        x0+r,y1,x0,y1,x0,y1-r,x0,y0+r,x0,y0,smooth=True,splinesteps=16,**options)


def apply_theme(root,scale=1.):
    """Generate a small 9-slice atlas once per root/scale; ttk retains keyboard semantics."""
    signature=round(max(1.,float(scale)),2)
    if getattr(root,'_lunar_signature',None)==signature:return
    style=ttk.Style(root);style.theme_use('clam')
    images=[];cache=getattr(root,'_lunar_asset_cache',{});root._lunar_asset_cache=cache
    def create_element(name,*args,**kwargs):
        if name not in style.element_names():style.element_create(name,*args,**kwargs)
    prefix='Lunar'+str(round(signature*100))
    def asset(fill,outline=None,radius=CONTROL_RADIUS):
        key=(signature,fill,outline,radius)
        if key in cache:
            photo,r=cache[key];images.append(photo);return photo,r
        r=round(radius*signature);ss=3
        # Tk tiles the center of image elements rather than stretching it.
        # A 3px center caused thousands of alpha blits on wide controls.
        width=max(2*r+5,round(160*signature));height=max(2*r+5,round(48*signature))
        img=Image.new('RGBA',(width*ss,height*ss),(0,0,0,0))
        draw=ImageDraw.Draw(img)
        draw.rounded_rectangle((ss,ss,(width-1)*ss,(height-1)*ss),radius=r*ss,
            fill=fill,outline=outline,width=ss if outline else 1)
        photo=ImageTk.PhotoImage(img.resize((width,height),Image.Resampling.LANCZOS),master=root)
        images.append(photo);cache[key]=(photo,r+1);return photo,r+1
    def element(name,fill,hover,pressed,outline=None):
        normal,border=asset(fill,outline);active,_=asset(hover,outline)
        down,_=asset(pressed,ACCENT);focus,_=asset(fill,ACCENT);disabled,_=asset(SURFACE,BORDER)
        key=prefix+name
        create_element(key,'image',normal,('disabled',disabled),('pressed',down),('focus',focus),('active',active),border=border,padding=0,width=2*border+1,height=2*border+1,sticky='nsew')
        return key
    normal=element('Button',SURFACE,HOVER,SELECTED)
    primary=element('Primary',ACCENT,'#C8B6F5','#A28AD7')
    quiet=element('Quiet',BG,SURFACE,SELECTED)
    selected=element('Selected',SELECTED,HOVER,SELECTED,ACCENT)
    def button_layout(element_name):
        return [(element_name,{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})]
    for name,key,foreground in [('TButton',normal,TEXT),('Primary.TButton',primary,ON_ACCENT),
                                ('Quiet.TButton',quiet,MUTED),('Selected.TButton',selected,TEXT)]:
        style.layout(name,button_layout(key));style.configure(name,background=BG,foreground=foreground,
            font=(FONT,round(9*getattr(root,'_visual_scale',1.))),padding=(round(10*signature),round(6*signature)),borderwidth=0,width=0)
        style.map(name,foreground=[('disabled','#7D8093'),('active',foreground)],
                  background=[('disabled',BG),('active',BG),('pressed',BG),('focus',BG)])
    style.configure('Section.TButton',anchor='w')
    for name,key in [('Nav.TButton',normal),('Nav.Selected.TButton',selected)]:
        style.layout(name,button_layout(key))
        style.configure(name,background=SURFACE,foreground=TEXT,font=(FONT,round(9*getattr(root,'_visual_scale',1.))),padding=(8,6),width=0)
        style.map(name,background=[('active',SURFACE),('focus',SURFACE),('pressed',SURFACE)])
    for name,key,foreground in [('Card.TButton',normal,TEXT),('Card.Primary.TButton',primary,ON_ACCENT),('Card.Quiet.TButton',quiet,MUTED)]:
        style.layout(name,button_layout(key));style.configure(name,background=SURFACE,foreground=foreground,font=(FONT,round(9*getattr(root,'_visual_scale',1.))),padding=(10,6),width=0)
        style.map(name,background=[('active',SURFACE),('focus',SURFACE),('pressed',SURFACE)],foreground=[('disabled',MUTED)])
    style.configure('TFrame',background=BG,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    style.configure('TLabel',background=BG,foreground=TEXT,font=(FONT,round(9*getattr(root,'_visual_scale',1.))))
    style.configure('TCheckbutton',background=BG,foreground=TEXT,font=(FONT,round(9*getattr(root,'_visual_scale',1.))),padding=3)
    style.map('TCheckbutton',background=[('active',BG)],foreground=[('disabled',MUTED)])
    style.configure('TScrollbar',background=BORDER,troughcolor=BG,bordercolor=BG,lightcolor=BG,darkcolor=BG,arrowcolor=MUTED,borderwidth=0,arrowsize=10)
    style.configure('TSeparator',background=BORDER)
    style.configure('TCombobox',fieldbackground=SURFACE,background=SURFACE,foreground=TEXT,arrowcolor=MUTED,padding=5,borderwidth=0,bordercolor=BORDER,lightcolor=SURFACE,darkcolor=SURFACE)
    style.map('TCombobox',fieldbackground=[('readonly',SURFACE)],foreground=[('readonly',TEXT)])
    style.configure('TEntry',fieldbackground=SURFACE,foreground=TEXT,insertcolor=TEXT,padding=7,borderwidth=0,bordercolor=BORDER,lightcolor=SURFACE,darkcolor=SURFACE)
    style.configure('Lunar.TEntry',fieldbackground=SURFACE,foreground=TEXT,insertcolor=TEXT,padding=4,borderwidth=0,bordercolor=SURFACE,lightcolor=SURFACE,darkcolor=SURFACE)
    style.map('Lunar.TEntry',bordercolor=[('focus',SURFACE)])
    style.configure('TNotebook',background=BG,borderwidth=0,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    style.configure('Compact.TNotebook',background=BG,borderwidth=0,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    style.layout('Compact.TNotebook.Tab',[])
    style.layout('Compact.TNotebook',[('Notebook.client',{'sticky':'nswe'})])
    card,r=asset(SURFACE,BORDER,SURFACE_RADIUS);cardkey=prefix+'Card'
    create_element(cardkey,'image',card,border=r,padding=0,width=2*r+1,height=2*r+1,sticky='nsew')
    style.layout('Card.TFrame',[(cardkey,{'sticky':'nswe','children':[('Frame.padding',{'sticky':'nswe'})]})])
    style.configure('Card.TFrame',background=BG)
    field,r=asset(SURFACE,BORDER);fieldkey=prefix+'Field'
    focusedfield,_=asset(SURFACE,ACCENT)
    create_element(fieldkey,'image',field,('focus',focusedfield),border=r,padding=0,width=2*r+1,height=2*r+1,sticky='nsew')
    style.layout('Input.TFrame',[(fieldkey,{'sticky':'nswe','children':[('Frame.padding',{'sticky':'nswe'})]})])
    style.configure('Input.TFrame',background=BG)
    root.configure(bg=BG)
    root._lunar_images=images;root._lunar_signature=signature


class Tooltip:
    """Local label inside the existing panel: no new native window or focus grab."""
    def __init__(self,widget,text):
        self.widget=widget;self.text=text;self.job=None;self.label=None
        for event in ('<Enter>','<FocusIn>'):widget.bind(event,self.schedule,add='+')
        for event in ('<Leave>','<FocusOut>','<ButtonPress>','<Unmap>','<Destroy>'):widget.bind(event,self.hide,add='+')
    def schedule(self,event=None):
        self.hide();self.job=self.widget.after(450,self.show)
    def show(self):
        self.job=None
        if not self.widget.winfo_exists() or not self.widget.winfo_viewable():return
        root=self.widget.winfo_toplevel();width=max(120,min(260,root.winfo_width()-12))
        self.label=tk.Label(root,text=self.text() if callable(self.text) else self.text,bg=HOVER,fg=TEXT,font=(FONT,8),wraplength=width-12,
                            justify='left',padx=6,pady=5,highlightthickness=1,highlightbackground=ACCENT)
        self.label.update_idletasks()
        x=self.widget.winfo_rootx()-root.winfo_rootx()
        y=self.widget.winfo_rooty()-root.winfo_rooty()+self.widget.winfo_height()+4
        x=max(4,min(x,root.winfo_width()-self.label.winfo_reqwidth()-4))
        y=max(4,min(y,root.winfo_height()-self.label.winfo_reqheight()-4))
        self.label.place(x=x,y=y);self.label.lift()
    def hide(self,event=None):
        if self.job is not None:
            try:self.widget.after_cancel(self.job)
            except tk.TclError:pass
            self.job=None
        if self.label is not None:
            try:self.label.destroy()
            except tk.TclError:pass
            self.label=None


def place_dialog(dialog,parent,size):
    """Scale a normal native window and keep it within its owner's desktop."""
    owner=parent.winfo_toplevel();scale=getattr(owner,'_lunar_signature',1.)
    native=getattr(owner,'_lunar_native',None)
    left,top,right,bottom=(native.work_area(owner.winfo_rootx(),owner.winfo_rooty()) if hasattr(native,'work_area') else native.desktop_bounds()) if native else (0,0,owner.winfo_screenwidth(),owner.winfo_screenheight())
    width=min(round(size[0]*scale),right-left-24)
    height=min(round(size[1]*scale),bottom-top-round(48*scale))
    x=max(left,min(owner.winfo_rootx()+16,right-width))
    y=max(top,min(owner.winfo_rooty()+24,bottom-height-32))
    dialog.geometry(f'{width}x{height}{x:+d}{y:+d}');dialog.update_idletasks()
    if native:
        native.panel(dialog.winfo_id());native.move_panel(dialog.winfo_id(),x,y)


def confirm_dialog(title,message,*,parent,bounds=None):
    """Application-owned import preview; cancel/close never applies a merge."""
    result=False
    scale=getattr(parent.winfo_toplevel(),'_lunar_signature',1.)
    apply_theme(parent.winfo_toplevel(),scale)
    dialog=tk.Toplevel(parent);dialog.withdraw();dialog.title(title)
    dialog.configure(bg=BG);dialog.transient(parent);dialog.resizable(False,False)
    native=getattr(parent.winfo_toplevel(),'_lunar_native',None)
    left,top,right,bottom=bounds or ((native.work_area(parent.winfo_rootx(),parent.winfo_rooty()) if hasattr(native,'work_area') else native.desktop_bounds()) if native else (0,0,parent.winfo_screenwidth(),parent.winfo_screenheight()))
    width=min(round(440*scale),right-left-24)
    frame=ttk.Frame(dialog,style='Card.TFrame',padding=round(16*scale));frame.pack(fill='both',expand=True,padx=8,pady=8)
    ttk.Label(frame,text=title,font=(FONT,12,'bold'),background=SURFACE).pack(anchor='w',pady=(0,10))
    ttk.Label(frame,text=message,wraplength=width-round(56*scale),justify='left',background=SURFACE).pack(fill='x',pady=(0,14))
    actions=ttk.Frame(frame);actions.pack(fill='x')
    def finish(accepted=False):
        nonlocal result
        result=accepted;dialog.destroy()
    cancel=ttk.Button(actions,text='Cancelar',command=finish)
    cancel.pack(side='left')
    ttk.Button(actions,text='Mesclar coletas',style='Primary.TButton',command=lambda:finish(True)).pack(side='right')
    dialog.bind('<Escape>',lambda e:finish());dialog.protocol('WM_DELETE_WINDOW',finish)
    dialog.update_idletasks();height=dialog.winfo_reqheight()
    x=max(left,min(parent.winfo_rootx(),right-width));y=max(top,min(parent.winfo_rooty()+40,bottom-height-32))
    dialog.geometry(f'{width}x{height}{x:+d}{y:+d}')
    dialog.deiconify()
    if native:
        native.panel(dialog.winfo_id());native.move_panel(dialog.winfo_id(),x,y)
    dialog.grab_set();cancel.focus_set();parent.wait_window(dialog)
    return result
