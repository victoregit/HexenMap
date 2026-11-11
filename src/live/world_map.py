"""Independent, offline Teyvat map; no capture, tracking or game commands."""
from src.live.i18n import tr as _tr
import ctypes as ct
import math,time
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk,messagebox
import numpy as np
from PIL import ImageTk
from src.live.theme import BG,TEXT,MUTED,ACCENT,place_dialog,Tooltip
from src.live.world_tiles import WorldTiles,screen_to_world
from src.live.world_index import WorldIndex
from src.live.map_registry import installed_scopes,map_name,scope_name
from src.live.presentation import MarkerCanvas
from src.live.marker_art import draw_pin,marker_geometry,LEGACY
from src.live.marker_menu import MarkerMenu
from src.overlay.window_tracker import GameWindowRect


class MapCardNative:
    def __init__(self,native,owner):self.native,self.owner=native,owner
    def popup(self,child,rect):
        self.native.panel(child);hwnd=self.native.u.GetAncestor(child,2) or child
        self.native.set_style(hwnd,-8,self.owner);return hwnd
    def place(self,hwnd,rect):
        self.native.u.SetWindowPos(hwnd,ct.c_void_p(0),rect.x,rect.y,rect.width,rect.height,0x10|0x40)


class WorldMap:
    def __init__(self,app):
        self.app=app;self.window=tk.Toplevel(app.root);self.window.title(_tr('Mapa geral · Hexen Map'))
        self.window.configure(bg=BG);self.window.minsize(520,380)
        self.window._lunar_signature=app.root._lunar_signature;self.window._lunar_native=app.native
        self.window._visual_scale=getattr(app.root,'_visual_scale',1.)
        self.scopes=installed_scopes()
        if not self.scopes:self.scopes=[('as-map-2','surface')]
        obs=app.session.observation
        current=(obs.map_id,obs.layer_id) if obs.fresh(time.monotonic()) else None
        self.recognized_scope=current
        saved=tuple(app.settings.get('world_map',{}).get('scope',()))
        self.scope=current if current in self.scopes else saved if saved in self.scopes else self.scopes[0]
        self.tiles=WorldTiles(map_id=self.scope[0],layer=self.scope[1]);self.photos={};self.card=None;self.closed=False
        self.index=None;self.index_source=id(app.session.items)
        self.index_future=self.tiles.pool.submit(WorldIndex,app.session.items,*self.scope)
        self.zoom=9.;a,b,c,d=self.tiles.bounds;self.cx=(a+c)/2;self.cy=(b+d)/2
        self.dirty=True;self.need_fit=True;self.job=None;self.last_progress=0.;self.collected=set();self.shown=[];self.clusters={}
        toolbar=ttk.Frame(self.window,padding=8);toolbar.pack(fill='x')
        ttk.Button(toolbar,text='−',width=3,command=lambda:self.zoom_at(-.5)).pack(side='left')
        ttk.Button(toolbar,text='+',width=3,command=lambda:self.zoom_at(.5)).pack(side='left',padx=3)
        ttk.Button(toolbar,text=_tr('Ver mapa inteiro'),command=self.fit).pack(side='left',padx=5)
        ttk.Button(toolbar,text=_tr('Desfazer'),command=self.undo).pack(side='left')
        self.reveal=tk.BooleanVar();ttk.Checkbutton(toolbar,text=_tr('Mostrar coletados'),variable=self.reveal,command=self.invalidate).pack(side='right')
        selection=ttk.Frame(self.window);selection.pack(fill='x',padx=10)
        self.scope_names={scope_name((m,l)):(m,l) for m,l in self.scopes}
        self.scope_var=tk.StringVar(value=next(k for k,v in self.scope_names.items() if v==self.scope))
        self.scope_box=ttk.Combobox(selection,textvariable=self.scope_var,values=list(self.scope_names),state='readonly',width=34)
        self.scope_box.pack(side='left',fill='x',expand=True)
        self.scope_box.bind('<<ComboboxSelected>>',lambda event:self.select_scope(self.scope_names[self.scope_var.get()]))
        area_button=ttk.Button(selection,text=_tr('Área atual'),command=self.current_area)
        area_button.pack(side='right',padx=(6,0))
        Tooltip(area_button,_tr('Voltar ao último mapa reconhecido no jogo, sem alterar o rastreamento.'))
        self.canvas=tk.Canvas(self.window,bg='#19252D',highlightthickness=0);self.canvas.pack(fill='both',expand=True,padx=8,pady=6)
        self.status=tk.StringVar(value=_tr('Carregando mapa local…'));ttk.Label(self.window,textvariable=self.status,foreground=MUTED).pack(fill='x',padx=10)
        ttk.Label(self.window,text=_tr('Arraste para navegar · roda para zoom · clique no ponto para coletar | AppSample / HoYoverse'),foreground=MUTED,font=('Segoe UI',8),wraplength=800).pack(fill='x',padx=10,pady=(2,8))
        self.renderer=MarkerCanvas(self.canvas,self.draw_pin)
        self.canvas.bind('<Configure>',lambda event:self.fit() if self.need_fit else self.invalidate())
        self.canvas.bind('<MouseWheel>',lambda event:self.zoom_at(.25 if event.delta>0 else -.25,event.x,event.y))
        self.canvas.bind('<Button-1>',self.start_drag);self.canvas.bind('<B1-Motion>',self.drag);self.canvas.bind('<ButtonRelease-1>',self.release)
        self.window.bind('<Escape>',lambda event:self.close_card())
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        place_dialog(self.window,app.root,(1000,700));self.fit();self.poll()
        scale=getattr(app.root,'_lunar_signature',1.)
        bounds=app.native.work_area(self.window.winfo_rootx(),self.window.winfo_rooty())
        self.window.minsize(min(round(520*scale),bounds[2]-bounds[0]-24),min(round(380*scale),bounds[3]-bounds[1]-round(48*scale)))

    def select_scope(self,scope):
        if scope not in self.scopes or scope==self.scope:return
        self.close_card();self.index_future.cancel();self.tiles.close()
        self.scope=scope;self.index=None;self.photos.clear();self.shown=[];self.clusters={}
        self.renderer.clear();self.canvas.delete('tiles')
        self.tiles=WorldTiles(map_id=scope[0],layer=scope[1])
        self.index_future=self.tiles.pool.submit(WorldIndex,self.app.session.items,*scope)
        self.scope_var.set(next(k for k,v in self.scope_names.items() if v==scope))
        self.app.settings['world_map']={'scope':list(scope)}
        try:self.app.persist_settings()
        except OSError as exc:self.status.set(_tr('Falha ao salvar preferências: {0}',exc))
        self.fit();self.invalidate()

    def current_area(self):
        obs=self.app.session.observation
        fresh=obs.fresh(time.monotonic())
        scope=(obs.map_id,obs.layer_id) if fresh else getattr(self.app,'last_recognized_scope',None) or self.recognized_scope
        if scope in self.scopes:
            self.recognized_scope=scope
            self.select_scope(scope)
            if fresh and obs.player is not None:
                self.cx,self.cy=obs.player;self.clamp();self.invalidate()
            else:self.fit()
        else:self.status.set(_tr('Localização atual ainda não reconhecida.'))

    def invalidate(self):self.dirty=True
    def fit(self):
        if min(self.canvas.winfo_width(),self.canvas.winfo_height())<100:self.need_fit=True;return
        self.need_fit=False
        self.close_card();a,b,c,d=self.tiles.bounds
        width=max(1,self.canvas.winfo_width()-32);height=max(1,self.canvas.winfo_height()-32)
        self.zoom=max(8.,min(16.,14+math.log2(min(width/(c-a),height/(d-b)))))
        self.cx=(a+c)/2;self.cy=(b+d)/2;self.invalidate()
    def zoom_at(self,delta,x=None,y=None):
        self.close_card();w=self.canvas.winfo_width();h=self.canvas.winfo_height()
        x=w/2 if x is None else x;y=h/2 if y is None else y
        wx,wy=screen_to_world(x,y,w,h,self.cx,self.cy,self.zoom)
        self.zoom=max(8.,min(16.,self.zoom+delta));scale=2**(self.zoom-14)
        self.cx=wx-(x-w/2)/scale;self.cy=wy-(y-h/2)/scale;self.clamp();self.invalidate();return 'break'
    def clamp(self):
        a,b,c,d=self.tiles.bounds;self.cx=max(a,min(c,self.cx));self.cy=max(b,min(d,self.cy))
    def start_drag(self,event):
        self.close_card();self.origin=(event.x,event.y,self.cx,self.cy);self.moved=False
    def drag(self,event):
        x,y,cx,cy=self.origin;dx,dy=event.x-x,event.y-y;self.moved|=abs(dx)+abs(dy)>4
        scale=2**(self.zoom-14);self.cx=cx-dx/scale;self.cy=cy-dy/scale;self.clamp();self.invalidate()
    def release(self,event):
        if self.moved:return
        hits=[p for p in self.shown if p.geometry.contains(p.x,p.y,event.x,event.y)]
        hits.sort(key=lambda p:(p.x-event.x)**2+(p.y-event.y)**2)
        if not hits:return
        pin=hits[0]
        if pin.item.id in self.clusters:
            group=self.clusters[pin.item.id];self.cx,self.cy=self.index.xy[group].mean(axis=0)
            self.zoom_at(1.);return
        items=[p.item for p in hits if p.item.id not in self.clusters]
        native=self.app.native;hwnd=native.u.GetAncestor(self.window.winfo_id(),2) or self.window.winfo_id()
        rect=GameWindowRect(self.window.winfo_rootx(),self.window.winfo_rooty(),self.window.winfo_width(),self.window.winfo_height(),False,True,hwnd)
        def change(identifier,value):
            try:self.app.session.set_collected(identifier,value,map_scope=self.scope)
            except Exception as exc:
                messagebox.showerror(_tr('Coleta não salva'),_tr(str(exc)),parent=self.window);return
            self.app.refresh_counts()
            self.last_progress=0.;self.close_card();self.invalidate()
        self.card=MarkerMenu(self.window,MapCardNative(native,hwnd),rect,items,self.app.session,change,self.close_card,
                             event.x_root,event.y_root,self.app.marker_hints)
    def undo(self):
        self.close_card();self.app.session.undo(map_scope=self.scope)
        self.app.refresh_counts();self.last_progress=0.;self.invalidate()
    def close_card(self):
        if self.card:card=self.card;self.card=None;card.destroy()
    def draw_pin(self,canvas,category,x,y,**kwargs):
        if category.startswith('cluster:'):
            count=category.split(':')[1]
            canvas.create_oval(x-12,y-12,x+12,y+12,fill='#332E46',outline=ACCENT)
            canvas.create_text(x,y,text=_tr(count),fill=TEXT,font=('Segoe UI',8))
        else:draw_pin(canvas,category,x,y,**kwargs)

    def draw(self):
        self.dirty=False;w=self.canvas.winfo_width();h=self.canvas.winfo_height()
        if min(w,h)<2:return
        scale=2**(self.zoom-14);ox=w/2-self.cx*scale;oy=h/2-self.cy*scale
        self.canvas.delete('tiles');visible_photos={};level=max(12,min(14,int(self.zoom)))
        world_tile=256*2**(14-level);pixels=max(1,math.ceil(world_tile*scale)+1)
        a,b,c,d=self.tiles.bounds
        left,top=screen_to_world(0,0,w,h,self.cx,self.cy,self.zoom)
        right,bottom=screen_to_world(w,h,w,h,self.cx,self.cy,self.zoom)
        for y in range(max(math.floor(b/world_tile),math.floor(top/world_tile)),min(math.ceil(d/world_tile),math.floor(bottom/world_tile)+1)):
            for x in range(max(math.floor(a/world_tile),math.floor(left/world_tile)),min(math.ceil(c/world_tile),math.floor(right/world_tile)+1)):
                key=(level,x,y,pixels);image=self.tiles.get(key)
                if image is None:continue
                photo=self.photos.get(key)
                if photo is None:photo=ImageTk.PhotoImage(image,master=self.window)
                visible_photos[key]=photo
                self.canvas.create_image(round(ox+x*world_tile*scale),round(oy+y*world_tile*scale),image=photo,anchor='nw',tags='tiles')
        self.photos=visible_photos;self.canvas.tag_lower('tiles')
        if self.index is None:return
        selected=self.app.session.selected
        ids=self.index.query((left,top,right,bottom),selected,() if self.reveal.get() else self.collected)
        positions=self.index.xy[ids]*scale+np.array([ox,oy]);self.clusters={};pins=[]
        dpi=self.app.native.dpi_scale(self.window.winfo_id())
        if len(ids)>1500 or (self.zoom<12.5 and len(ids)>150):
            cells=np.floor(positions/(30*dpi)).astype(np.int64)
            keys=cells[:,1]*100000+cells[:,0];order=np.argsort(keys);cuts=np.flatnonzero(np.diff(keys[order]))+1
            for group in np.split(order,cuts):
                members=ids[group];x,y=positions[group].mean(axis=0)
                if len(members)>1:
                    name=f'group:{int(keys[group[0]])}';self.clusters[name]=members
                    pins.append(SimpleNamespace(item=SimpleNamespace(id=name,category=f'cluster:{len(members)}'),x=x,y=y,geometry=LEGACY))
                else:
                    item=self.index.items[int(members[0])]
                    pins.append(SimpleNamespace(item=item,x=x,y=y,geometry=marker_geometry(item.category,'map',dpi)))
        else:
            for i,(x,y) in zip(ids,positions):
                item=self.index.items[int(i)];pins.append(SimpleNamespace(item=item,x=x,y=y,geometry=marker_geometry(item.category,'map',dpi)))
        self.shown=self.renderer.render(pins,lambda key:False if key in self.clusters else self.app.session.is_collected(key),budget_ms=8.)
        if len(self.shown)<len(pins):self.dirty=True
        self.canvas.tag_lower('tiles')
        state=_tr('{0} pontos',f'{len(ids):,}'.replace(',','.'))
        if self.clusters:state+=_tr(' · {0} grupos — clique para aproximar',len(self.clusters))
        if not selected:state='Selecione os tipos de itens no painel para mostrar os pontos.'
        if not self.tiles.levels:state='Imagens locais não instaladas. Os pontos usam o catálogo atual.'
        elif self.tiles.pending:state+=_tr(' · carregando imagens locais…')
        self.status.set(_tr(state))

    def poll(self):
        if self.closed:return
        if self.index is None and self.index_future.done():
            self.index=self.index_future.result();self.dirty=True
        if id(self.app.session.items)!=self.index_source:
            self.close_card();self.index_source=id(self.app.session.items);self.index=None
            self.renderer.clear();self.shown=[];self.clusters={}
            self.index_future=self.tiles.pool.submit(WorldIndex,self.app.session.items,*self.scope)
        now=time.monotonic()
        selection=frozenset(self.app.session.selected)
        if selection!=getattr(self,'selection',None):self.selection=selection;self.dirty=True;self.close_card()
        if now-self.last_progress>=1:
            collected={key for key in self.app.session.progress.get_collected_ids() if self.app.session.is_collected(key)}
            if collected!=self.collected:self.collected=collected;self.dirty=True
            self.last_progress=now
        if self.tiles.poll():self.dirty=True
        if self.dirty:self.draw()
        if self.tiles.pending:self.dirty=True
        self.job=self.window.after(40,self.poll)
    def close(self):
        self.closed=True
        if self.job is not None:self.window.after_cancel(self.job)
        self.close_card();self.index_future.cancel();self.tiles.close();self.photos.clear();self.window.destroy()
        self.app.world_map=None
