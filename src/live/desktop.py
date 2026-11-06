"""Configuration panel and separate click-through icon surface, all Tk calls on UI thread."""
from __future__ import annotations

import csv
import logging
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS, load_catalog
from src.live.regions import RegionalCatalog
from src.live.icons import draw_marker, ICON_MARGIN
from src.live.marker_menu import MarkerMenu
from src.live.native import Windows
from src.live.motion import MotionRecognizer
from src.live.reference import load_pack, ReferenceUnavailable
from src.live.session import Session, CollectionCount
from src.live.storage import bundle_dir, install_dir, read_settings, write_json, HOTKEY_OPTIONS, parse_hotkey
from src.live.vision import Observation, ScreenRecognizer, LayerRecognizer
from src.overlay.global_hotkeys import GlobalHotkeyListener, MOD_NOREPEAT
from src.overlay.control_key import ControlKeyListener
from src.progress.progress_manager import ProgressManager

logger=logging.getLogger(__name__)


class DesktopApp:
    def __init__(self, reference_dir: Path | None = None):
        self.native=Windows()
        self.native.enable_dpi()
        self.user_dir=install_dir()/"userData"
        self.user_dir.mkdir(exist_ok=True)
        self.settings_path=self.user_dir/"settings.json"
        self.settings=read_settings(self.settings_path)
        self.catalogs=RegionalCatalog(bundle_dir()/"data/community")
        self.package_id=self.settings.get("package",self.catalogs.default_package(self.user_dir/'references'))
        if self.package_id not in self.catalogs.regions and self.package_id!="legacy-mondstadt": self.package_id="legacy-mondstadt"
        items,region,coordinate_system=self.catalogs.load(self.package_id)
        self.coordinate_system=coordinate_system
        self.selection_epoch=0
        self.counts_at=0.0
        self.session=Session(items,
                             ProgressManager(str(self.user_dir/"progress.json")))
        self.session.selected=set(self.settings["categories"]) & CATEGORIES.keys()
        self.session.region_id=region
        self.session.map_id="teyvat"
        self.session.layer_id="surface"
        self.session.territories=self.catalogs.territories
        self.session.rules=self.catalogs.rules
        self.reference_override=reference_dir
        self.reference_root=self.user_dir/'references'
        self.reference_dir=reference_dir or self.user_dir/"references/mondstadt"
        self.recognizer=None
        self.reference_error=""
        self.reference_lock=threading.Lock()
        self.reference_build_lock=threading.Lock()
        self.events=queue.Queue()
        self.latest=queue.Queue(maxsize=1)
        self.stop_event=threading.Event()
        self.listener=None
        self.control_listener=ControlKeyListener()
        self.overlay_hwnd=None
        self.input_hwnd=None
        self.input_boxes=None
        self.overlay_error=""
        self.geometry_key=None
        self.pending_order=[]
        self.control_down=False
        self.visible_pins=[]
        self.marker_menu=None
        self.menu_open=False
        self.menu_deadline=0.0
        self.menu_geometry=None
        self.menu_mouse_down=False
        self.root=tk.Tk()
        self.root.title("Genshin Gem Wish · Exploração")
        self.root.geometry("470x710")
        self.root.minsize(440,690)
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self._panel()
        self.surface=tk.Toplevel(self.root)
        self.surface.withdraw()
        self.surface.overrideredirect(True)
        self.surface.configure(bg="#ff00ff")
        self.surface.attributes("-transparentcolor","#ff00ff")
        self.canvas=tk.Canvas(self.surface,bg="#ff00ff",highlightthickness=0,borderwidth=0)
        self.canvas.pack(fill="both",expand=True)
        self.surface.update_idletasks()
        try: self.overlay_hwnd=self.native.overlay(self.surface.winfo_id())
        except OSError as exc: self.overlay_error=f"Overlay indisponível: {exc}"
        self.input_surface=tk.Toplevel(self.root)
        self.input_surface.withdraw()
        self.input_surface.overrideredirect(True)
        self.input_surface.configure(bg="black")
        self.input_canvas=tk.Canvas(self.input_surface,bg="black",highlightthickness=0,borderwidth=0)
        self.input_canvas.pack(fill="both",expand=True)
        self.input_canvas.bind("<Button-1>",self.open_marker_menu)
        self.input_surface.update_idletasks()
        try: self.input_hwnd=self.native.input_overlay(self.input_surface.winfo_id())
        except OSError as exc: self.overlay_error=f"Interação indisponível: {exc}"
        self.reload_reference()
        self.configure_hotkeys()
        self.control_listener.start()
        self.worker=threading.Thread(target=self._worker,name="LiveRecognition",daemon=True)
        self.worker.start()
        self.root.after(50,self._tick)
        self.root.after(10,self._poll_pointer)

    def _panel(self):
        bg="#101b24";card="#17252e";gold="#cfb982";text="#e7eeeb";muted="#91a9ad"
        self.root.geometry("520x850")
        self.root.minsize(470,680)
        self.root.configure(bg=bg)
        style=ttk.Style(self.root);style.theme_use("clam")
        style.configure("TFrame",background=bg)
        style.configure("TLabel",background=bg,foreground=text,font=("Segoe UI",10))
        style.configure("TButton",background="#243944",foreground=text,borderwidth=0,
                        font=("Segoe UI",10),padding=(12,8))
        style.map("TButton",background=[("active","#314d58")])
        style.configure("Accent.TButton",background=gold,foreground=bg,font=("Segoe UI",10,"bold"))
        style.map("Accent.TButton",background=[("active","#e4d1a1")])
        style.configure("Row.TCheckbutton",background=card,foreground=text,font=("Segoe UI",10),padding=4)
        style.map("Row.TCheckbutton",background=[("active","#213943")],foreground=[("disabled",muted)])
        style.configure("TNotebook",background=bg,borderwidth=0,bordercolor=bg,lightcolor=bg,darkcolor=bg)
        style.configure("TNotebook.Tab",background=bg,foreground=muted,padding=(18,8),font=("Segoe UI",10),borderwidth=0)
        style.map("TNotebook.Tab",background=[("selected",card)],foreground=[("selected",gold)])
        style.configure("TCombobox",fieldbackground="#233944",foreground=text,arrowcolor=gold,
                        background="#233944",bordercolor="#344d56",padding=5)
        style.map("TCombobox",fieldbackground=[("readonly","#233944")],foreground=[("readonly",text)])
        style.configure("TEntry",fieldbackground="#233944",foreground=text,insertcolor=text,padding=5)
        style.configure("Exploration.Horizontal.TProgressbar",background="#83cbb1",troughcolor="#243a43",
                        borderwidth=0,lightcolor="#83cbb1",darkcolor="#83cbb1")
        frame=ttk.Frame(self.root,padding=20);frame.pack(fill="both",expand=True)
        header=tk.Frame(frame,bg=bg);header.pack(fill="x",pady=(0,10))
        tk.Label(header,text="✦",font=("Segoe UI",29),bg=bg,fg=gold).pack(side="left",padx=(0,12))
        heading=tk.Frame(header,bg=bg);heading.pack(side="left")
        tk.Label(heading,text="GENSHIN GEM WISH",font=("Segoe UI",9,"bold"),bg=bg,fg=gold,anchor="w").pack(fill="x")
        tk.Label(heading,text="Sua próxima descoberta",font=("Segoe UI",19,"bold"),bg=bg,fg=text).pack(anchor="w")
        self.territory_path=tk.StringVar(value="Mondstadt · Superfície")
        tk.Label(heading,textvariable=self.territory_path,font=("Segoe UI",9),bg=bg,fg=muted,wraplength=410,justify="left").pack(anchor="w",pady=(3,0))
        connection=tk.Frame(frame,bg=card,highlightbackground="#30454d",highlightthickness=1,padx=12,pady=7)
        connection.pack(fill="x",pady=(0,8))
        tk.Label(connection,text="●  CONEXÃO COM O JOGO",bg=card,fg="#86cbb8",font=("Segoe UI",8,"bold")).pack(anchor="w")
        self.status=tk.StringVar(value="Procurando o Genshin…")
        tk.Label(connection,textvariable=self.status,bg=card,fg=text,font=("Segoe UI",9),wraplength=400,justify="left").pack(anchor="w",pady=(4,0))
        progress=tk.Frame(frame,bg=card,padx=12,pady=8);progress.pack(fill="x",pady=(0,10))
        tk.Label(progress,text="PROGRESSO DO RECORTE SELECIONADO",bg=card,fg=muted,font=("Segoe UI",8,"bold")).pack(anchor="w")
        self.progress_text=tk.StringVar(value="Carregando progresso…")
        tk.Label(progress,textvariable=self.progress_text,bg=card,fg=text,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(4,8))
        self.progress_value=tk.DoubleVar(value=0)
        ttk.Progressbar(progress,variable=self.progress_value,maximum=100,style="Exploration.Horizontal.TProgressbar").pack(fill="x")
        tabs=ttk.Notebook(frame);tabs.pack(fill="both",expand=True)
        explore=ttk.Frame(tabs,padding=(10,12));prefs=ttk.Frame(tabs,padding=(10,12))
        tabs.add(explore,text="Exploração");tabs.add(prefs,text="Preferências")
        filters=tk.Frame(explore,bg=bg);filters.pack(fill="x",pady=(0,8))
        tk.Label(filters,text="Mostrar no mapa",bg=bg,fg=text,font=("Segoe UI",11,"bold")).pack(side="left")
        ttk.Button(filters,text="Todos",command=lambda:self.set_categories(True)).pack(side="right",padx=(6,0))
        ttk.Button(filters,text="Limpar",command=lambda:self.set_categories(False)).pack(side="right")
        self.region_names={"Mondstadt · catálogo anterior":"legacy-mondstadt",**{r["name"]:r["id"] for r in self.catalogs.regions.values()}}
        self.region_var=tk.StringVar(value=next(k for k,v in self.region_names.items() if v==self.package_id))
        region_box=ttk.Combobox(explore,textvariable=self.region_var,values=list(self.region_names),state="readonly")
        region_box.pack(fill="x",pady=2);region_box.bind("<<ComboboxSelected>>",self.change_region)
        self.area_var=tk.StringVar(value="Todas as áreas")
        self.area_box=ttk.Combobox(explore,textvariable=self.area_var)
        self.area_box.pack(fill="x",pady=2)
        self.area_box.bind("<<ComboboxSelected>>",self.change_territory)
        self.area_box.bind("<Return>",self.change_territory)
        self.area_box.bind("<KeyRelease>",self.search_territories)
        self.layer_var=tk.StringVar(value="teyvat / surface")
        self.layer_box=ttk.Combobox(explore,textvariable=self.layer_var,state="readonly")
        self.layer_box.pack(fill="x",pady=2);self.layer_box.bind("<<ComboboxSelected>>",self.change_territory)
        self.category_query=tk.StringVar()
        search=ttk.Entry(explore,textvariable=self.category_query)
        search.pack(fill="x",pady=(4,2))
        self.category_query.trace_add("write",lambda *args:self.filter_categories())
        ttk.Label(explore,text="Buscar recurso ou categoria").pack(anchor="w")
        category_canvas=tk.Canvas(explore,bg=bg,highlightthickness=0,height=160)
        scrollbar=ttk.Scrollbar(explore,orient="vertical",command=category_canvas.yview)
        scrollbar.pack(side="right",fill="y");category_canvas.pack(fill="both",expand=True)
        category_canvas.configure(yscrollcommand=scrollbar.set)
        self.category_frame=tk.Frame(category_canvas,bg=bg)
        window=category_canvas.create_window((0,0),window=self.category_frame,anchor="nw")
        self.category_frame.bind("<Configure>",lambda e:category_canvas.configure(scrollregion=category_canvas.bbox("all")))
        category_canvas.bind("<Configure>",lambda e:category_canvas.itemconfigure(window,width=e.width))
        self.category_vars={};self.category_labels={};self.category_widgets=[]
        self.populate_region_controls()
        tk.Label(explore,text="Ctrl + clique em um ícone para alterar a coleta.\nSegure Ctrl para ver os itens já pegos.",
                 bg=bg,fg=muted,font=("Segoe UI",9),justify="left").pack(anchor="w",pady=(10,0))
        self.candidates=ttk.Combobox(explore,state="readonly")
        self.confirm_button=ttk.Button(explore,text="Confirmar item selecionado",command=self.confirm_candidate)
        ttk.Label(prefs,text="Atalhos durante o jogo",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(0,10))
        self.key_vars={}
        for action,label in (("visibility","Mostrar / ocultar"),("collect","Coletar item próximo"),("undo","Desfazer última coleta")):
            row=ttk.Frame(prefs);row.pack(fill="x",pady=5)
            ttk.Label(row,text=label).pack(side="left")
            var=tk.StringVar(value=self.settings["hotkeys"][action]);self.key_vars[action]=var
            ttk.Combobox(row,textvariable=var,values=HOTKEY_OPTIONS,state="readonly",width=16).pack(side="right")
        ttk.Button(prefs,text="Salvar atalhos",command=self.save_keys).pack(fill="x",pady=(12,18))
        ttk.Label(prefs,text="Reconhecimento",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(0,6))
        ttk.Label(prefs,text="Se o alinhamento ficar indisponível, os ícones\nsão ocultados até a localização ser recuperada.",foreground=muted).pack(anchor="w")
        ttk.Button(prefs,text="Verificar referências novamente",command=self.reload_reference).pack(fill="x",pady=(10,0))
        self.notice=tk.StringVar()
        notice_label=tk.Label(frame,textvariable=self.notice,bg=bg,fg=gold,font=("Segoe UI",9),wraplength=430,justify="left")
        footer=ttk.Frame(frame);footer.pack(side="bottom",fill="x",pady=(4,0),before=tabs)
        notice_label.pack(side="bottom",fill="x",pady=(4,2),before=tabs)
        self.visibility_button=ttk.Button(footer,text="Ocultar overlay",command=self.toggle_visibility)
        self.visibility_button.pack(side="left")
        ttk.Button(footer,text="Continuar jogando",style="Accent.TButton",command=self.root.iconify).pack(side="right")

    def populate_region_controls(self):
        region=self.session.region_id
        self.area_names={"Todas as áreas":None,"Área não confirmada":"unclassified"}
        if self.package_id!="legacy-mondstadt":
            self.area_names.update({self.catalogs.territories.path(n.id):n.id for n in self.catalogs.territories.search(region) if n.kind!="region"})
        self.area_box.configure(values=list(self.area_names))
        layers=sorted({f"{i.map_id} / {layer}" for i in self.session.items for layer in (i.layer_ids or (i.layer_id,))} |
                      {f"{i.map_id} / automática" for i in self.session.items})
        map_names={'teyvat':'Mapa principal','chasm':'Minas do Despenhadeiro','enkanomiya':'Enkanomiya',
                   'sea_of_bygone_eras':'Mar das Eras Passadas','sky_temple':'Templo do Céu',
                   'ancient_sacred_mountain':'Montanha Sagrada Antiga','frost_moon':'Lua Gélida',
                   'unclassified-map':'Mapa não confirmado'}
        self.layer_names={}
        if self.package_id!='legacy-mondstadt': self.layer_names['Todos os mapas · camada automática']='* / automática'
        for value in layers:
            mapid,layer=value.split(' / ')
            node=self.catalogs.territories.nodes.get(layer)
            name=node.name if node else {'surface':'Superfície','automática':'Camada automática',
                                        'underground-unclassified':'Subterrâneo · camada não confirmada'}.get(layer,layer)
            self.layer_names[f'{map_names.get(mapid,mapid)} · {name}']=value
        self.layer_box.configure(values=list(self.layer_names))
        pref=self.settings.get("regional",{}).get(self.package_id,{})
        choice=pref.get("layer",'* / automática' if self.package_id!='legacy-mondstadt' else 'teyvat / surface')
        choice=choice if choice in self.layer_names.values() else 'teyvat / surface' if 'teyvat / surface' in layers else layers[0]
        self.layer_var.set(next(k for k,v in self.layer_names.items() if v==choice))
        self.area_var.set(next((k for k,v in self.area_names.items() if v==pref.get("area")),"Todas as áreas"))
        if self.package_id in self.settings.get("regional",{}):
            self.session.selected=set(pref.get("categories",[]))
        for child in self.category_frame.winfo_children(): child.destroy()
        self.category_vars={};self.category_labels={};self.category_widgets=[]
        categories={c for i in self.session.items for c in (i.category_ids or (i.category,))}
        self.session.selected.intersection_update(categories)
        group=None
        for category in sorted(categories,key=lambda c:(CATEGORY_GROUPS.get(c,"Outros"),CATEGORIES[c][0])):
            label=CATEGORIES[category][0];new_group=CATEGORY_GROUPS.get(category,"Outros")
            if new_group!=group:
                title=ttk.Label(self.category_frame,text=new_group)
                title.pack(anchor="w",pady=(8,2));self.category_widgets.append((title,new_group.casefold()));group=new_group
            var=tk.BooleanVar(value=category in self.session.selected);self.category_vars[category]=var
            label_var=tk.StringVar(value=label);self.category_labels[category]=label_var
            button=ttk.Checkbutton(self.category_frame,textvariable=label_var,variable=var,command=self.select_categories,style="Row.TCheckbutton")
            button.pack(fill="x");self.category_widgets.append((button,(new_group+' '+label).casefold()))
        self.apply_territory()

    def filter_categories(self):
        query=self.category_query.get().casefold().strip()
        for widget,label in self.category_widgets:
            widget.pack_forget()
        for widget,label in self.category_widgets:
            if not query or query in label: widget.pack(fill="x")

    def search_territories(self,event=None):
        query=self.area_var.get().casefold()
        self.area_box.configure(values=[k for k in self.area_names if query in k.casefold()])

    def apply_territory(self):
        self.session.area_id=self.area_names.get(self.area_var.get())
        self.session.map_id,self.session.layer_id=self.layer_names[self.layer_var.get()].split(" / ")
        if self.session.map_id=='*': self.session.map_id=None
        if self.session.layer_id=="automática": self.session.layer_id=None
        path=self.catalogs.territories.path(self.session.area_id) if self.session.area_id else self.catalogs.regions[self.session.region_id]['name']
        self.territory_path.set(f"{path or 'Área não confirmada'} · {self.layer_var.get()}")
        self.counts_at=0

    def change_territory(self,event=None):
        if self.area_var.get() not in self.area_names:
            self.session.notice="Selecione uma área da lista de resultados.";return
        self.close_marker_menu(restore_focus=False)
        self.apply_territory()
        try: self.persist_settings()
        except OSError as exc: self.session.notice=f"Falha ao salvar preferências: {exc}"
        self.reload_reference()

    def change_region(self,event=None):
        identifier=self.region_names[self.region_var.get()]
        if identifier==self.package_id: return
        try:
            self.persist_settings()
            items,region,space=self.catalogs.load(identifier)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.region_var.set(next(k for k,v in self.region_names.items() if v==self.package_id))
            self.session.notice=f"Pacote regional indisponível: {exc}";return
        self.close_marker_menu(restore_focus=False);self.session.invalidate("Trocando região…")
        self.package_id=identifier;self.coordinate_system=space
        self.session.items=items;self.session.region_id=region;self.session.selected=set()
        self.populate_region_controls()
        try: self.persist_settings()
        except OSError as exc: self.session.notice=f"Falha ao salvar preferências: {exc}"
        self.reload_reference()

    def set_categories(self,selected):
        for var in self.category_vars.values():
            var.set(selected)
        self.select_categories()

    def persist_settings(self):
        self.settings["categories"]=sorted(self.session.selected)
        self.settings["package"]=self.package_id
        self.settings["server"]="America"
        self.settings.setdefault("regional",{})[self.package_id]={"categories":sorted(self.session.selected),"area":self.session.area_id,"layer":self.layer_names[self.layer_var.get()]}
        write_json(self.settings_path,self.settings)

    def select_categories(self):
        self.session.selected={c for c,v in self.category_vars.items() if v.get()}
        self.close_marker_menu(restore_focus=False)
        self.session.pending_ids.clear()
        try: self.persist_settings()
        except OSError as exc: self.session.notice=f"Falha ao salvar preferências: {exc}"

    def save_keys(self):
        keys={k:v.get() for k,v in self.key_vars.items()}
        if len(set(keys.values()))!=3:
            messagebox.showerror("Atalhos","Escolha uma tecla diferente para cada ação.",parent=self.root)
            return
        self.settings["hotkeys"]=keys
        try:
            self.persist_settings()
            self.configure_hotkeys()
        except OSError as exc: self.session.notice=f"Falha ao salvar atalhos: {exc}"

    def configure_hotkeys(self):
        # Registrations belong to the listener thread; recreate rather than rebind from Tk.
        if self.listener: self.listener.stop()
        self.listener=GlobalHotkeyListener()
        for index,(action,key) in enumerate(self.settings["hotkeys"].items(),1):
            code,modifiers=parse_hotkey(key)
            self.listener.register_hotkey(index,code,modifiers,
                                          lambda action=action:self.events.put(action))
        self.listener.start()

    def reload_reference(self):
        with self.reference_lock:
            self.selection_epoch+=1
            self.recognizer=None
            self.reference_error="Carregando referência do mapa selecionado…"
            self.reference_context=(self.session.region_id,self.session.map_id or 'auto',self.session.layer_id or 'auto')
        self.session.invalidate("Localizando…")
        self.visible_pins=[]
        if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
        if self.input_hwnd:
            self.native.interactive(self.input_hwnd,False)
            self.native.hide(self.input_hwnd)
        epoch=self.selection_epoch
        region,mapid,layer,space=self.session.region_id,self.session.map_id,self.session.layer_id,self.coordinate_system
        legacy=self.package_id=="legacy-mondstadt"
        directory=self.reference_override or (self.reference_root/'mondstadt' if legacy else self.reference_root/'kongying'/region)
        if not self.reference_override and not legacy and mapid: directory=directory/mapid
        if not self.reference_override and not legacy and layer: directory=directory/layer
        allowed_layers={(item.map_id,value) for item in self.session.scoped_items() for value in (item.layer_ids or (item.layer_id,))}
        def build():
            # Serialize construction and discard superseded selections before doing work.
            with self.reference_build_lock:
                if self.stop_event.is_set() or epoch!=self.selection_epoch: return
                try:
                    if self.reference_override and (directory/'manifest.json').is_file():
                        import json
                        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
                        recognizer=ScreenRecognizer(load_pack(directory,region_id=region,map_id=mapid or manifest.get('map_id','teyvat'),
                                                  layer_id=layer,coordinate_system=space))
                    elif layer is None and not legacy:
                        factories=[]
                        for candidate in sorted(directory.glob("*/manifest.json" if mapid else '*/*/manifest.json')):
                            candidate_map=mapid or candidate.parent.parent.name
                            if (candidate_map,candidate.parent.name) not in allowed_layers: continue
                            factories.append(lambda path=candidate.parent,mid=candidate_map:load_pack(path,region_id=region,map_id=mid,
                                             layer_id=path.name,coordinate_system=space))
                        recognizer=LayerRecognizer(factories)
                    else:
                        recognizer=ScreenRecognizer(load_pack(directory,region_id=region,map_id=mapid,layer_id=layer,coordinate_system=space))
                    error=""
                except Exception as exc:
                    logger.exception("Referência regional indisponível")
                    recognizer=None;error=str(exc)
                with self.reference_lock:
                    if epoch==self.selection_epoch and not self.stop_event.is_set():
                        self.recognizer=recognizer;self.reference_error=error
        threading.Thread(target=build,name="SelectedMapReference",daemon=True).start()

    def toggle_visibility(self):
        self.session.hidden=not self.session.hidden
        self.visibility_button.configure(text="Mostrar overlay" if self.session.hidden else "Ocultar overlay")

    def confirm_candidate(self):
        index=self.candidates.current()
        if 0<=index<len(self.pending_order):
            try: self.session.confirm(self.pending_order[index])
            except Exception as exc: self.session.notice=f"Falha ao salvar coleta: {exc}"

    def _poll_pointer(self):
        if self.stop_event.is_set():
            return
        try:
            control,x,y=self.native.pointer()
            control=control or self.control_listener.is_down
            changed=control!=self.control_down
            self.control_down=control
            if changed:
                logger.info("Overlay interaction Ctrl=%s",control)
            if self.menu_open:
                down=self.native.key_down(0x01)
                outside=(down and not self.menu_mouse_down and not self.marker_menu.contains(x,y))
                self.menu_mouse_down=down
                if outside or self.native.key_down(0x1b):
                    self.close_marker_menu()
            if not self.menu_open and self.input_hwnd:
                rect=self.native.game()
                if (not control or not self.native.foreground(rect)
                        or self.rect_key(rect)!=self.geometry_key
                        or not self.session.observation.fresh(time.monotonic()) or self.session.hidden):
                    self.native.interactive(self.input_hwnd,False)
                    self.native.hide(self.input_hwnd)
                elif changed:
                    self._sync_input(rect)
        except Exception:
            logger.exception("Falha na interação dos marcadores")
            if self.input_hwnd:
                self.native.interactive(self.input_hwnd,False)
                self.native.hide(self.input_hwnd)
        self.root.after(10,self._poll_pointer)

    def close_marker_menu(self, event=None, restore_focus=True):
        was_open=self.menu_open
        self.menu_open=False
        if self.marker_menu:
            menu=self.marker_menu
            self.marker_menu=None
            try:
                menu.destroy()
            except tk.TclError:
                pass
        if self.input_hwnd:
            self.native.interactive(self.input_hwnd,False)
            self.native.hide(self.input_hwnd)
        if was_open and restore_focus:
            rect=self.native.game()
            self.native.restore_game_focus(rect)

    def _sync_input(self,rect):
        if not self.input_hwnd:
            return
        if not self.control_down or not self.visible_pins or not self.session.observation.fresh(time.monotonic()):
            self.native.interactive(self.input_hwnd,False)
            self.native.hide(self.input_hwnd)
            return
        boxes=tuple((round(p.x)-ICON_MARGIN,round(p.y)-ICON_MARGIN,
                     round(p.x)+ICON_MARGIN+1,round(p.y)+ICON_MARGIN+1) for p in self.visible_pins)
        if boxes!=self.input_boxes:
            self.native.input_region(self.input_hwnd,list(boxes))
            self.input_boxes=boxes
        self.input_canvas.configure(width=rect.width,height=rect.height)
        self.native.interactive(self.input_hwnd,True)
        self.native.place(self.input_hwnd,rect)
        self.input_canvas.configure(cursor="hand2")

    def change_marker_state(self, identifier, collected):
        try:
            rect=self.native.game()
            if time.monotonic()>self.menu_deadline or self.rect_key(rect)!=self.menu_geometry:
                self.session.notice="Menu expirado. Use Ctrl + clique no item novamente."
            else:
                self.session.set_collected(identifier,collected)
                self.refresh_counts()
        except Exception as exc:
            self.session.notice=f"Falha ao salvar item: {exc}"
            logger.exception("Falha ao salvar pelo menu do marcador")
        finally:
            self.close_marker_menu()

    def refresh_counts(self):
        counts=self.session.collection_counts()
        items=self.session.scoped_items()
        permanent=[i for i in items if self.session.rules.get(i.rule_id,self.session.rules["unknown"]).kind=="permanent"]
        collected=sum(self.session.is_collected(i.id) for i in permanent)
        total=len(permanent)
        permanent_ids={i.id for i in permanent}
        unavailable=sum(self.session.is_collected(i.id) for i in items if i.id not in permanent_ids)
        for category in self.category_labels:
            label=CATEGORIES[category][0]
            count=counts.get(category,CollectionCount(0,0))
            state='indisponíveis' if CATEGORY_GROUPS.get(category)=='Recursos' else 'pegos'
            self.category_labels[category].set(f"{label} · {count.collected}/{count.total} {state}")
        self.progress_text.set(f"{collected}/{total} permanentes · {unavailable} recursos indisponíveis")
        self.progress_value.set(100*collected/total if total else 0)

    def open_marker_menu(self, event):
        rect=self.native.game()
        control,_,_=self.native.pointer()
        control=control or self.control_listener.is_down
        if not control or not self.native.menu_foreground(rect) or self.menu_open:
            logger.info("Marker click rejected: Ctrl=%s foreground=%s menu=%s",
                        control,self.native.menu_foreground(rect),self.menu_open)
            return "break"
        displayed={p.item.id for p in self.visible_pins}
        items=[i for i in self.session.hit_test(rect.width,rect.height,event.x,event.y)
               if i.id in displayed]
        if not items:
            logger.info("Marker click without current hit at %s,%s",event.x,event.y)
            return "break"
        logger.info("Marker menu opened: %s item(s)",len(items))
        self.menu_open=True
        self.menu_geometry=self.rect_key(rect)
        self.menu_deadline=time.monotonic()+30
        self.menu_mouse_down=True
        # Only the card receives input while open; outside clicks reach the game.
        self.native.interactive(self.input_hwnd,False)
        self.native.hide(self.input_hwnd)
        try:
            self.marker_menu=MarkerMenu(self.root,self.native,rect,items,self.session,
                                        self.change_marker_state,self.close_marker_menu,
                                        event.x_root,event.y_root)
        except Exception:
            self.close_marker_menu()
            logger.exception("Falha ao abrir cartão do item")
        return "break"

    @staticmethod
    def rect_key(rect):
        return rect.hwnd,rect.x,rect.y,rect.width,rect.height

    def _publish(self,value):
        try: self.latest.get_nowait()
        except queue.Empty: pass
        try: self.latest.put_nowait(value)
        except queue.Full: pass

    def _worker(self):
        motion=None
        active_recognizer=None
        previous_key=None
        try:
            with (self.user_dir/"live-session-v2.csv").open("a",newline="",encoding="utf-8") as log:
                writer=csv.writer(log)
                if log.tell()==0: writer.writerow(["monotonic_s","surface","latency_ms","confidence","p95_px","reason","region","map","layer","selection_epoch"])
                while not self.stop_event.is_set():
                    started=time.monotonic(); rect=self.native.game()
                    with self.reference_lock:
                        recognizer=self.recognizer; error=self.reference_error; epoch=self.selection_epoch
                        context=self.reference_context
                    if recognizer is not active_recognizer:
                        if motion: motion.close()
                        motion=MotionRecognizer(recognizer) if recognizer else None
                        active_recognizer=recognizer
                    key=self.rect_key(rect)
                    if key!=previous_key:
                        if motion: motion.reset()
                        previous_key=key
                    obs=Observation("hidden",started,reason="Aguardando o Genshin abrir…")
                    if rect.is_found and not self.native.foreground(rect):
                        if motion: motion.reset()
                        obs=Observation("hidden",started,reason="Volte ao Genshin para continuar")
                    elif rect.is_found and recognizer is None:
                        obs=Observation("hidden",started,reason=error)
                    elif rect.is_found:
                        try: obs=motion.observe(self.native.capture(rect),started)
                        except Exception:
                            logger.exception("Falha no reconhecimento")
                            obs=Observation("hidden",started,reason="Não foi possível reconhecer a tela")
                    elapsed=time.monotonic()-started
                    self._publish((self.rect_key(rect),obs,epoch))
                    current=epoch==self.selection_epoch
                    writer.writerow([round(started,3),obs.surface if current else 'hidden',round(elapsed*1000,1),round(obs.confidence,3),obs.error_px,
                                     obs.reason if current else 'Seleção substituída',context[0],obs.map_id or context[1],obs.layer_id or context[2],epoch]); log.flush()
                    self.stop_event.wait(max(.005,.05-elapsed))
        except Exception as exc:
            logger.exception("Falha no serviço ao vivo"); self.events.put(("error",str(exc)))
        finally:
            if motion: motion.close()

    def _tick(self):
        if self.stop_event.is_set(): return
        try:
            rect=self.native.game(); foreground=self.native.foreground(rect); key=self.rect_key(rect)
            if self.menu_open:
                # Keep the visibility shortcut responsive while a menu owns input.
                while True:
                    try: action=self.events.get_nowait()
                    except queue.Empty: break
                    if action=="visibility": self.toggle_visibility()
                    elif isinstance(action,tuple): self.session.notice=action[1]
                if (key!=self.menu_geometry or not rect.is_found or rect.is_minimized
                        or time.monotonic()>self.menu_deadline or self.session.hidden
                        or not self.native.menu_foreground(rect)):
                    self.close_marker_menu()
                else:
                    # Keep the explicit item selection, never old map coordinates.
                    if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
                    self.canvas.delete("all")
                    self.visible_pins=[]
                    self.root.after(50,self._tick)
                    return
            if key!=self.geometry_key:
                self.session.invalidate("Localizando após mudança de janela…"); self.geometry_key=key
            try:
                observation_key,obs,epoch=self.latest.get_nowait()
                if observation_key==key and epoch==self.selection_epoch: self.session.observation=obs
            except queue.Empty: pass
            if not foreground:
                self.session.invalidate("Volte ao Genshin para continuar" if rect.is_found else "Aguardando o Genshin abrir…",
                                        clear_pending=not rect.is_found)
            while True:
                try: action=self.events.get_nowait()
                except queue.Empty: break
                if action=="visibility": self.toggle_visibility()
                elif action=="collect" and foreground: self.session.collect()
                elif action=="undo" and foreground: self.session.undo()
                elif isinstance(action,tuple): self.session.notice=action[1]
            pins=self.session.pins(rect.width,rect.height,include_collected=self.control_down) if foreground and not self.overlay_error else []
            self.visible_pins=pins
            self.canvas.delete("all")
            if pins and self.overlay_hwnd:
                self.native.place(self.overlay_hwnd,rect)
                self.canvas.configure(width=rect.width,height=rect.height)
                for pin in pins:
                    draw_marker(self.canvas,pin.item.category,pin.x,pin.y,
                                collected=self.session.is_collected(pin.item.id))
            elif self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
            self._sync_input(rect)
            status=self.overlay_error or self.reference_error or self.session.observation.reason
            if self.session.hidden: status="Overlay oculto · use o atalho para mostrar"
            elif not self.session.selected and not self.reference_error: status+=" · selecione o que procurar"
            elif foreground and self.session.observation.surface!="hidden" and not self.session.observation.fresh(time.monotonic()):
                status="Localização atrasada · ícones ocultos"
            if self.package_id!='legacy-mondstadt': status+=" · cobertura em validação"
            self.status.set(status); self.notice.set(self.session.notice)
            if self.listener and self.listener.registration_errors:
                self.notice.set("Um atalho está em uso por outro programa. Escolha outra tecla e salve.")
            if time.monotonic()-self.counts_at>=1:
                self.refresh_counts();self.counts_at=time.monotonic()
            if self.session.pending_ids and time.monotonic()-self.session.pending_at>30: self.session.pending_ids.clear()
            order=[i for i in self.session.items if i.id in self.session.pending_ids]
            if [i.id for i in order]!=self.pending_order:
                self.pending_order=[i.id for i in order]
                self.candidates.configure(values=[f"{i.name} · {i.id[-8:]}" for i in order])
                if order:
                    self.candidates.set(""); self.candidates.pack(fill="x"); self.confirm_button.pack(fill="x")
                else:
                    self.candidates.pack_forget(); self.confirm_button.pack_forget()
        except Exception as exc:
            logger.exception("Falha na atualização do overlay")
            self.close_marker_menu()
            if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
            self.session.invalidate("Overlay pausado após uma falha"); self.session.notice=str(exc)
        self.root.after(50,self._tick)

    def close(self):
        self.stop_event.set()
        self.close_marker_menu(restore_focus=False)
        if self.listener: self.listener.stop()
        self.control_listener.stop()
        if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
        self.worker.join(timeout=2)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
