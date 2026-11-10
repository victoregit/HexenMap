"""Resizable panel geometry and presentation scale, independent of game pixels."""
import tkinter as tk
from src.live.theme import apply_theme,panel_size


def fitted_size(width,height,scale,bounds):
    left,top,right,bottom=bounds
    maximum=(max(240,right-left-16),max(300,bottom-top-round(48*scale)))
    minimum=(min(round(360*scale),maximum[0]),min(round(440*scale),maximum[1]))
    return tuple(max(lo,min(round(value*scale),hi)) for value,lo,hi in zip((width,height),minimum,maximum))


class PanelLayout:
    def layout_bounds(self):
        x,y=getattr(self,'last_panel_position',(32,80))
        return self.native.work_area(x,y) if hasattr(self.native,'work_area') else self.panel_desktop_bounds()

    def setup_panel_resize(self):
        self._layout_busy=False;self._resize_save=None
        self.root.bind('<Configure>',self.panel_configured,add='+')
        grip=tk.Label(self.shell,text='◢',bg=self.shell.cget('bg'),fg='#B2B4C4',cursor='size_nw_se',font=('Segoe UI',9))
        grip.place(relx=1,rely=1,anchor='se')
        grip.bind('<Button-1>',lambda event:setattr(self,'_resize_origin',(event.x_root,event.y_root,*self.panel_normal_size)))
        grip.bind('<B1-Motion>',self.drag_panel_size)
        grip.bind('<ButtonRelease-1>',lambda event:self.finish_panel_drag())
        self.update_panel_constraints();self.scale_panel_fonts()

    def update_panel_constraints(self):
        if self.panel_collapsed:
            self.root.resizable(False,False);self.root.minsize(40,40);return
        minimum=fitted_size(360,440,self.ui_scale,self.layout_bounds())
        self.root.minsize(*minimum);self.root.resizable(self.panel_detached,self.panel_detached)
        a,b,c,d=self.layout_bounds();self.root.maxsize(max(240,c-a-16),max(300,d-b-round(48*self.ui_scale)))

    def fit_panel_position(self):
        x,y=self.panel_position();a,b,c,d=self.layout_bounds();w,h=self.panel_normal_size
        target=(max(a,min(x,c-w-16)),max(b,min(y,d-h-32)))
        if target!=(x,y):self.move_panel_to(*target)

    def panel_configured(self,event):
        if event.widget is not self.root or self.panel_collapsed or self._layout_busy:return
        if min(event.width,event.height)<100:return
        self.panel_normal_size=(event.width,event.height)
        if self._resize_save is not None:self.root.after_cancel(self._resize_save)
        def save():
            self._resize_save=None
            self.panel_position()
            dpi=self.native.dpi_scale(self.root.winfo_id()) if hasattr(self.native,'dpi_scale') else 1.
            if abs(dpi-getattr(self,'panel_dpi',dpi))>.01:self.change_panel_scale()
            self.fit_panel_position()
            self.finish_panel_drag()
        self._resize_save=self.root.after(350,save)

    def drag_panel_size(self,event):
        x,y,w,h=self._resize_origin
        width,height=fitted_size((w+event.x_root-x)/self.ui_scale,(h+event.y_root-y)/self.ui_scale,self.ui_scale,self.layout_bounds())
        self.root.geometry(f'{width}x{height}')

    def scale_panel_fonts(self):
        factor=self.root._visual_scale
        for name in ('brand_emblem','capture_eye','planet_button','layer_button','search_icon'):
            widget=getattr(self,name,None)
            if widget is None:continue
            if not hasattr(widget,'_base_dimensions'):
                widget._base_dimensions=(int(widget.cget('width')),int(widget.cget('height')))
                widget._icon_scale=1.
            ratio=self.ui_scale/widget._icon_scale
            widget.scale('all',0,0,ratio,ratio);widget._icon_scale=self.ui_scale
            widget.configure(width=round(widget._base_dimensions[0]*self.ui_scale),height=round(widget._base_dimensions[1]*self.ui_scale))
        def visit(widget):
            try:
                if not hasattr(widget,'_panel_font'):
                    parts=widget.tk.splitlist(widget.cget('font'))
                    if len(parts)>1:widget._panel_font=(parts[0],int(parts[1]),*parts[2:])
                if hasattr(widget,'_panel_font'):
                    name,size,*style=widget._panel_font
                    widget.configure(font=(name,max(6,round(size*factor)),*style))
            except (tk.TclError,ValueError):pass
            for child in widget.winfo_children():
                if not isinstance(child,tk.Toplevel):visit(child)
        visit(self.shell)

    def change_panel_scale(self,event=None,reset=False):
        self.close_layers();self.panel_position();self._layout_busy=True
        old=self.ui_scale
        width,height=(360,540) if reset else tuple(v/old for v in self.panel_normal_size)
        percent=int(self.panel_scale_var.get().rstrip('%'))
        self.panel_dpi=self.native.dpi_scale(self.root.winfo_id()) if hasattr(self.native,'dpi_scale') else 1.
        self.root._visual_scale=percent/100;self.ui_scale=self.panel_dpi*percent/100
        apply_theme(self.root,self.ui_scale);self.scale_panel_fonts()
        browser=self.category_browser;browser.ui_scale=self.ui_scale;browser.font_scale=percent/100
        browser.HEIGHT=round(36*self.ui_scale);browser.configure(yscrollincrement=browser.HEIGHT)
        browser.rebuild()
        self.panel_normal_size=fitted_size(width,height,self.ui_scale,self.layout_bounds())
        self.root.geometry('%dx%d'%self.panel_normal_size);self.update_panel_constraints()
        self.root.update_idletasks();self._layout_busy=False;self.fit_panel_position();self.finish_panel_drag()

    def reset_panel_size(self):self.change_panel_scale(reset=True)
