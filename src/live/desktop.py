"""Configuration panel and separate click-through icon surface, all Tk calls on UI thread."""
from __future__ import annotations

import csv
import math
from collections import Counter
import logging
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS, load_catalog
from src.live.regions import RegionalCatalog
from src.live.loading import CatalogLoader, ProcessCatalogSource
from src.live.labels import register_presentation
from src.live.category_browser import CountIndices
from src.live.marker_art import draw_pin, LEGACY
from src.live.marker_menu import MarkerMenu
from src.live.panel import CompactPanel
from src.live.presentation import DisplayMotion, MarkerCanvas, DisplayTelemetry, outside_controls
from src.live.native import Windows, OverlayAlreadyRunning
from src.live.motion import MotionRecognizer
from src.live.reference import load_pack, ReferenceUnavailable, ReferenceCancelled
from src.live.session import Session, CollectionCount
from src.live.storage import bundle_dir, install_dir, read_settings, write_json, HOTKEY_OPTIONS, parse_hotkey, PreferenceWriter
from src.live.vision import Observation, ScreenRecognizer, LayerRecognizer, template_visible
from src.live.reference_store import read_spec
from src.live.budget_vision import BudgetRecognizer
from src.live.performance import PerformanceTelemetry
from src.live.identity import WINDOW_TITLE
from src.live.automark import AutoMark,ChestSignals
from src.live.automark_service import AutoMarkService
from src.live.opening_recovery import minimap_frame
from src.overlay.global_hotkeys import GlobalHotkeyListener, MOD_NOREPEAT
from src.overlay.control_key import ControlKeyListener
from src.progress.progress_manager import ProgressManager

logger=logging.getLogger(__name__)


class DesktopApp(CompactPanel):
    def __init__(self, reference_dir: Path | None = None):
        self.native=Windows()
        self.native.enable_dpi()
        if not self.native.acquire_instance():raise OverlayAlreadyRunning()
        self.user_dir=install_dir()/"userData"
        self.user_dir.mkdir(exist_ok=True)
        self.settings_path=self.user_dir/"settings.json"
        self.settings=read_settings(self.settings_path)
        self.native.set_capture_visible(self.settings.get('capture_visible',False))
        self.preference_writer=PreferenceWriter(self.settings_path)
        self.catalogs=RegionalCatalog(bundle_dir()/"data/community",self.user_dir/'catalogs')
        self.package_id=self.settings.get("package",self.catalogs.default_package(self.user_dir/'references'))
        if not self.catalogs.accepts(self.package_id): self.package_id="appsample"
        package=self.catalogs.load_package(self.package_id)
        self.category_metadata=package.categories
        self.map_names=getattr(package,'map_names',{}) or {}
        register_presentation(package.categories)
        items,region,coordinate_system=package.items,package.region,package.coordinate_system
        self.region_loading=False
        self.catalog_generation=0
        self.requested_package=self.package_id
        self.catalog_source=ProcessCatalogSource(self.catalogs.community,self.user_dir/'catalogs')
        self.catalog_loader=CatalogLoader(self.catalog_source)
        self.count_indices=CountIndices()
        self.coordinate_system=coordinate_system
        self.selection_epoch=0
        self.counts_at=0.0
        self.session=Session(items,
                             ProgressManager(str(self.user_dir/"progress.json")))
        self.automark=AutoMark()
        self.chest_signals=ChestSignals(self.user_dir/'automark')
        self.automark_generation=0;self.automark_snapshot=None
        self.session.selected=set(self.settings["categories"]) & CATEGORIES.keys()
        self.session.region_id=region
        self.session.map_id="as-map-2"
        self.session.layer_id="surface"
        self.session.territories=self.catalogs.territories
        self.session.rules=self.catalogs.rules
        self.reference_override=reference_dir
        self.reference_root=self.user_dir/'references'
        self.reference_dir=reference_dir or self.user_dir/"references/appsample/as-map-2/surface"
        self.recognizer=None
        self.reference_error=""
        self.reference_lock=threading.Lock()
        self.reference_build_lock=threading.Lock()
        self.reference_released=threading.Event();self.reference_released.set()
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
        self.overlay_exclusions=None
        self.pending_order=[]
        self.control_down=False
        self.visible_pins=[]
        self.marker_menu=None
        self.menu_open=False
        self.menu_deadline=0.0
        self.menu_geometry=None
        self.menu_mouse_down=False
        self.root=tk.Tk()
        self.root.title(WINDOW_TITLE)
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
        self.renderer=MarkerCanvas(self.canvas,draw_pin)
        self.display_motion=DisplayMotion()
        self.displayed_at=0.0
        self.displayed_observation=None
        self.telemetry=None
        try: self.telemetry=DisplayTelemetry(self.user_dir/'display-session.csv')
        except OSError: logger.exception("Métricas de desenho indisponíveis")
        self.reload_reference()
        self.configure_hotkeys()
        self.control_listener.start()
        self.worker=threading.Thread(target=self._worker,name="LiveRecognition",daemon=True)
        self.worker.start()
        self.automark_service=AutoMarkService(self.chest_signals,Windows,self.automark_context,self.events.put,self.stop_event)
        self.automark_worker=threading.Thread(target=self.automark_service.run,name='ChestHUD',daemon=True)
        self.automark_worker.start()
        self.root.after(16,self._tick)
        self.root.after(10,self._poll_pointer)

    def populate_region_controls(self):
        region=self.session.region_id
        layers=sorted({f"{i.map_id} / {layer}" for i in self.session.items for layer in (i.layer_ids or (i.layer_id,))} |
                      {f"{i.map_id} / automática" for i in self.session.items})
        if self.package_id=='appsample':
            available={f'{p.parent.parent.name} / {p.parent.name}' for p in (self.user_dir/'references/appsample').glob('*/*/manifest.json')}
            layers=[value for value in layers if value in available] or ['as-map-2 / surface']
        map_names={'teyvat':'Mapa principal','chasm':'Minas do Despenhadeiro','enkanomiya':'Enkanomiya',
                   'sea_of_bygone_eras':'Mar das Eras Passadas','sky_temple':'Templo do Céu',
                   'ancient_sacred_mountain':'Montanha Sagrada Antiga','frost_moon':'Lua Gélida',
                   'unclassified-map':'Mapa não confirmado'}
        map_names.update(getattr(self,'map_names',{}))
        self.layer_names={}
        for value in layers:
            mapid,layer=value.split(' / ')
            node=self.catalogs.territories.nodes.get(layer)
            name=node.name if node else {'surface':'Superfície','automática':'Camada automática',
                                        'underground-unclassified':'Subterrâneo · camada não confirmada'}.get(layer,layer)
            if layer.startswith('as-layer-'):name='Camada '+layer.removeprefix('as-layer-').replace('-', '/')+' · sem referência'
            if mapid.startswith('as-map-') and mapid not in map_names:map_names[mapid]='Mapa '+mapid.removeprefix('as-map-')+' · sem referência'
            self.layer_names[f'{map_names.get(mapid,mapid)} · {name}']=value
        pref=self.settings.get("regional",{}).get(self.package_id,{})
        default='as-map-2 / surface'
        choice=pref.get("layer",default)
        choice=choice if choice in self.layer_names.values() else 'teyvat / surface' if 'teyvat / surface' in layers else layers[0]
        self.layer_var.set(next(k for k,v in self.layer_names.items() if v==choice))
        if self.package_id in self.settings.get("regional",{}):
            self.session.selected=set(pref.get("categories",[]))
        categories={c for i in self.session.items for c in (i.category_ids or (i.category,))}
        self.session.selected.intersection_update(categories)
        self.build_category_rows(categories)
        self.apply_territory()

    def apply_territory(self):
        self.session.area_id=None
        self.session.map_id,self.session.layer_id=self.layer_names[self.layer_var.get()].split(" / ")
        if self.session.map_id=='*': self.session.map_id=None
        if self.session.layer_id=="automática": self.session.layer_id=None
        self.territory_path.set(self.layer_var.get())
        self.counts_at=0

    def change_territory(self,event=None):
        self.close_marker_menu(restore_focus=False)
        self.apply_territory()
        try: self.persist_settings()
        except OSError as exc: self.session.notice=f"Falha ao salvar preferências: {exc}"
        self.reload_reference()

    def show_appsample_export(self):
        from src.live.appsample_export import GUIDE, script_text
        from tkinter import filedialog
        import webbrowser
        popup=tk.Toplevel(self.root);popup.title('Exportação local — AppSample');popup.geometry('540x580')
        popup.transient(self.root)
        body=tk.Text(popup,wrap='word',font=('Segoe UI',10),padx=14,pady=12)
        scroll=ttk.Scrollbar(popup,command=body.yview);scroll.pack(side='right',fill='y')
        body.configure(yscrollcommand=scroll.set);body.pack(fill='both',expand=True)
        body.insert('1.0',GUIDE);body.configure(state='disabled')
        actions=ttk.Frame(popup);actions.pack(fill='x',padx=10,pady=8)
        def save_script():
            name=filedialog.asksaveasfilename(parent=popup,title='Salvar código para conferir',
                initialfile='hexen-appsample-export.js',defaultextension='.js',filetypes=[('JavaScript','*.js')])
            if name:
                try:
                    Path(name).write_text(script_text(),encoding='utf-8')
                    messagebox.showinfo('Script salvo','Abra o arquivo em um editor para conferir o código. Execute somente no DevTools do AppSample, seguindo as instruções.',parent=popup)
                except OSError as exc:messagebox.showerror('Falha ao salvar',str(exc),parent=popup)
        ttk.Button(actions,text='Salvar script…',command=save_script).pack(side='left')
        ttk.Button(actions,text='Abrir AppSample',command=lambda:webbrowser.open('https://genshin-impact-map.appsample.com/pt/')).pack(side='left',padx=6)
        ttk.Button(actions,text='Importar arquivo…',command=lambda:(popup.destroy(),self.import_appsample_progress())).pack(side='right')

    def import_appsample_progress(self):
        if self.region_loading:return
        if self.package_id!='appsample':
            self.session.notice='Selecione a fonte AppSample antes de importar.';return
        from tkinter import filedialog
        from src.live.appsample_import import parse_marker_ids
        from src.live.appsample_runtime import import_records
        import json
        filename=filedialog.askopenfilename(parent=self.root,title='Coletados do AppSample',
            initialdir=self.user_dir/'imports/appsample',filetypes=[('Progresso JSON','*.json *.txt')])
        if not filename:return
        try:
            path=Path(filename)
            if path.stat().st_size>16*1024*1024:raise ValueError('Arquivo maior que 16 MiB')
            ids,_=parse_marker_ids(json.loads(path.read_text(encoding='utf-8-sig')))
            records,missing,key=import_records(ids,self.session.items)
            if not messagebox.askyesno('Importar coletados',f'{len(records)} itens encontrados no catálogo.\n{len(missing)} IDs ausentes serão preservados no arquivo original.\n\nMesclar com o progresso atual, criando backup?',parent=self.root):return
            result=self.session.progress.merge_imported_records(records,key,'appsample')
            self.refresh_counts();self.session.notice=f"AppSample: {result['added']} novos coletados; {len(missing)} IDs sem posição nesta versão."
        except Exception as exc:
            logger.exception('Importação AppSample não aplicada');self.session.notice=f'Falha na importação: {exc}'

    def sync_source_controls(self):
        self.source_caption.configure(text='APPSAMPLE')

    def request_package(self,identifier):
        if identifier==self.package_id and not self.region_loading:return
        try:self.persist_settings()
        except OSError as exc:
            self.session.notice=f"Falha ao salvar preferências: {exc}";return
        self.close_layers();self.close_marker_menu(restore_focus=False)
        self.requested_package=identifier
        self.region_loading=True
        self.session.invalidate("Trocando nação…")
        with self.reference_lock:
            self.selection_epoch+=1
            if self.recognizer is not None:self.reference_released.clear()
            self.recognizer=None
            self.reference_error="Carregando catálogo…"
        self.display_motion.reset();self.displayed_observation=None
        self.visible_pins=[];self.renderer.clear()
        if self.overlay_hwnd:self.native.hide(self.overlay_hwnd)
        if self.input_hwnd:
            self.native.interactive(self.input_hwnd,False);self.native.hide(self.input_hwnd)
        self.category_browser.set_model(None,set())
        self.territory_path.set('Carregando '+('AppSample' if identifier=='appsample' else self.region_var.get())+'…')
        self.progress_text.set('Carregando catálogo…')
        self.catalog_generation=self.catalog_loader.request(identifier)

    def poll_catalog(self):
        while True:
            try:generation,error=self.preference_writer.errors.get_nowait()
            except queue.Empty:break
            if generation==self.preference_writer.generation:
                self.session.notice=f'Preferências não salvas: {error}'
        while True:
            try:generation,identifier,package,error=self.catalog_loader.results.get_nowait()
            except queue.Empty:return
            if generation!=self.catalog_generation or identifier!=self.requested_package:continue
            self.region_loading=False
            if error:
                if hasattr(self,'source_var'):self.sync_source_controls()
                else:self.region_var.set(next(k for k,v in self.region_names.items() if v==self.package_id))
                self.session.notice=f"Pacote regional indisponível: {error}"
                self.populate_region_controls();self.reload_reference()
                continue
            self.package_id=package.id;self.coordinate_system=package.coordinate_system
            self.category_metadata=package.categories
            self.map_names=getattr(package,'map_names',{}) or {}
            register_presentation(package.categories)
            self.session.items=package.items;self.session.region_id=package.region
            self.session.selected=set()
            self.category_query.set('')
            self.sync_source_controls()
            self.populate_region_controls()
            try:self.persist_settings()
            except OSError as exc:self.session.notice=f"Falha ao salvar preferências: {exc}"
            self.reload_reference()

    def set_categories(self,selected):
        if self.region_loading:return
        if not selected:
            self.choose_categories(set(self.session.selected),False);return
        browser=self.category_browser
        entries=[e for e in self.category_model.entries if
                 (not browser.query or browser.query in e.search) and
                 (e.group not in {'Etiquetas da fonte','Identificação pendente'} or browser.query or
                  e.group not in browser.collapsed)]
        self.choose_categories(set().union(*(e.members for e in entries)),True)

    def persist_settings(self):
        self.settings["categories"]=sorted(self.session.selected)
        self.settings["package"]=self.package_id
        self.settings["server"]="America"
        self.settings.setdefault("regional",{})[self.package_id]={"categories":sorted(self.session.selected),"layer":self.layer_names[self.layer_var.get()]}
        x,y=self.panel_position()
        self.settings["panel"]={"collapsed":self.panel_collapsed,"detached":self.panel_detached,"x":x,"y":y}
        self.preference_writer.request(self.settings)

    def select_categories(self):
        self.session.selected={c for c,v in self.category_vars.items() if v.get()}
        self.close_marker_menu(restore_focus=False)
        self.session.pending_ids.clear()
        try: self.persist_settings()
        except OSError as exc: self.session.notice=f"Falha ao salvar preferências: {exc}"

    def save_keys(self):
        keys={k:v.get() for k,v in self.key_vars.items()}
        if len(set(keys.values()))!=len(self.key_vars):
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
            if self.recognizer is not None:self.reference_released.clear()
            self.recognizer=None
            self.reference_error="Carregando referência do mapa selecionado…"
            self.reference_context=(self.session.region_id,self.session.map_id or 'auto',self.session.layer_id or 'auto')
        self.session.invalidate("Localizando…")
        self.display_motion.reset()
        self.displayed_observation=None
        self.renderer.clear()
        if hasattr(self.root,'_hexen_photos'):self.root._hexen_photos.prune(force=True)
        self.visible_pins=[]
        if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
        if self.input_hwnd:
            self.native.interactive(self.input_hwnd,False)
            self.native.hide(self.input_hwnd)
        epoch=self.selection_epoch
        region,mapid,layer,space=self.session.region_id,self.session.map_id,self.session.layer_id,self.coordinate_system
        directory=self.reference_override or self.reference_root/'appsample'
        if not self.reference_override and mapid:directory=directory/mapid
        if not self.reference_override and layer:directory=directory/layer
        allowed_layers={(item.map_id,value) for item in self.session.scoped_items() for value in (item.layer_ids or (item.layer_id,))}
        cancelled=lambda:self.stop_event.is_set() or epoch!=self.selection_epoch
        def build():
            # Serialize construction and discard superseded selections before doing work.
            with self.reference_build_lock:
                while not self.reference_released.wait(.05):
                    if cancelled():return
                if self.stop_event.is_set() or epoch!=self.selection_epoch: return
                # Do not overlap a retired JSON worker with cold SIFT workspace peaks.
                self.catalog_source.retire_idle()
                if cancelled():return
                try:
                    candidates=[]
                    if (directory/'manifest.json').is_file():candidates=[directory/'manifest.json']
                    elif layer is None:
                        candidates=[candidate for candidate in sorted(directory.glob('*/manifest.json' if mapid else '*/*/manifest.json'))
                                    if (mapid or candidate.parent.parent.name,candidate.parent.name) in allowed_layers]
                    specs=[]
                    for candidate in candidates:
                        if cancelled():raise ReferenceCancelled('Seleção substituída')
                        import json
                        metadata=json.loads(candidate.read_text(encoding='utf-8'))
                        specs.append(read_spec(candidate.parent,region,mapid or metadata.get('map_id','teyvat'),
                                               layer,space,len(specs)))
                    mode=self.settings.get('performance_mode','light')
                    try:
                        recognizer=BudgetRecognizer(specs,self.user_dir/'cache/references',mode,cancelled)
                    except (MemoryError, __import__('cv2').error) as exc:
                        if mode!='global' or not isinstance(exc,MemoryError) and 'memory' not in str(exc).lower():raise
                        logger.warning('Cobertura global indisponível; retornando ao modo Leve: %s',exc)
                        recognizer=BudgetRecognizer(specs,self.user_dir/'cache/references','light',cancelled)
                        self.events.put(('performance_fallback',epoch))
                    error=""
                except ReferenceCancelled:
                    return
                except Exception as exc:
                    if cancelled():return
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
        pointer_active=False
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
                rect=self.native.game();pointer_active=rect.is_found and self.native.foreground(rect)
                if (not control or not pointer_active
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
        self.root.after(10 if self.control_down or self.menu_open or pointer_active else 80,self._poll_pointer)

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
        boxes=tuple(box for p in self.visible_pins
                    for box in getattr(p,'geometry',LEGACY).rectangles(p.x,p.y))
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

    def collect_shortcut(self,rect):
        choices=self.automark.choices(self.session,time.monotonic())
        if not choices:
            self.session.collect();return
        self.automark.reset()
        self.close_marker_menu(restore_focus=False)
        self.menu_open=True;self.menu_geometry=self.rect_key(rect)
        self.menu_deadline=time.monotonic()+30;self.menu_mouse_down=False
        self.native.interactive(self.input_hwnd,False);self.native.hide(self.input_hwnd)
        self.marker_menu=MarkerMenu(self.root,self.native,rect,choices,self.session,
                                    self.change_marker_state,self.close_marker_menu,
                                    rect.x+rect.width//2,rect.y+rect.height//2)

    def refresh_counts(self):
        if hasattr(self,'category_browser'):
            if self.region_loading:return
            if hasattr(self,'count_indices'):
                index=self.count_indices.get(self.session,self.category_model)
                if index is None:
                    self.progress_text.set('Contando itens…')
                    return False
                totals,memberships,permanent_ids,other_ids=index
                collected_counts=Counter();collected=unavailable=0
                for identifier in self.session.progress.get_collected_ids():
                    if identifier in memberships and self.session.is_collected(identifier):
                        collected_counts.update(memberships[identifier])
                        if identifier in permanent_ids:collected+=1
                        else:unavailable+=1
                counts={entry.key:(collected_counts[entry.key],totals[entry.key]) for entry in self.category_model.entries}
                total=len(permanent_ids)
            else:
                counts=self.category_model.counts(self.session)
                collected,total,unavailable=self.session.progress_summary()
            browser=self.category_browser
            if counts!=browser.counts or browser.selected!=self.session.selected:
                browser.counts=counts;browser.selected=set(self.session.selected);browser.schedule_paint()
            self.progress_text.set(f"{collected}/{total} permanentes · {unavailable} recursos indisponíveis")
            self.progress_value.set(100*collected/total if total else 0)
            return
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
        now=time.monotonic()
        if (self.rect_key(rect)!=self.geometry_key or now-self.displayed_at>.12
                or self.displayed_observation is None or not self.displayed_observation.fresh(now)):
            return "break"
        hits=[p for p in self.visible_pins
              if getattr(p,'geometry',LEGACY).contains(p.x,p.y,event.x,event.y)]
        hits.sort(key=lambda p:(math.hypot(p.x-event.x,p.y-event.y),p.item.id))
        items=[p.item for p in hits]
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

    def _publish(self,value,frame=None):
        obs=value[1]
        evidence=minimap_frame(frame,obs.circle,obs.captured_at) if self.settings.get('automark') and obs.surface=='minimap' else None
        self.automark_snapshot=(*value,evidence)
        try: self.latest.get_nowait()
        except queue.Empty: pass
        try: self.latest.put_nowait(value)
        except queue.Full: pass

    def acknowledge_reference_release(self,active_recognizer):
        with self.reference_lock:
            if active_recognizer is None and self.recognizer is None:self.reference_released.set()

    def automark_context(self):
        with self.reference_lock:
            pack=self.recognizer.pack if self.recognizer is not None else None
            epoch=self.selection_epoch
        enabled=self.settings.get('automark',False) and not self.session.hidden and not self.region_loading and not self.menu_open
        return enabled,self.automark_generation,epoch,pack,self.automark_snapshot

    def _worker(self):
        motion=None
        try:performance=PerformanceTelemetry(self.user_dir/'performance.jsonl')
        except OSError:performance=None;logger.warning('Diagnóstico de desempenho indisponível')
        active_recognizer=None
        previous_key=None
        try:
            with (self.user_dir/"live-session-v2.csv").open("a",newline="",encoding="utf-8") as log:
                writer=csv.writer(log)
                if log.tell()==0: writer.writerow(["monotonic_s","surface","latency_ms","confidence","p95_px","reason","region","map","layer","selection_epoch"])
                last_log=-math.inf;last_log_state=None
                while not self.stop_event.is_set():
                    frame=None
                    started=time.monotonic(); rect=self.native.game()
                    with self.reference_lock:
                        recognizer=self.recognizer; error=self.reference_error; epoch=self.selection_epoch
                        context=self.reference_context
                    if recognizer is not active_recognizer:
                        if motion: motion.close(wait=True)
                        if active_recognizer is not None and hasattr(active_recognizer,'close'):active_recognizer.close()
                        motion=MotionRecognizer(recognizer) if recognizer else None
                        active_recognizer=recognizer
                    self.acknowledge_reference_release(active_recognizer)
                    key=(self.rect_key(rect),getattr(self.native,'capture_visible',False))
                    if key!=previous_key:
                        if motion: motion.reset()
                        previous_key=key
                    obs=Observation("hidden",started,reason="Aguardando o Genshin abrir…")
                    if rect.is_found and not self.native.foreground(rect):
                        if motion: motion.reset()
                        obs=Observation("hidden",started,reason="Volte ao Genshin para continuar")
                    elif rect.is_found and recognizer is None:
                        obs=Observation("hidden",started,reason=error)
                    elif rect.is_found and ((not self.session.selected and not (self.settings.get('automark')
                            and getattr(self,'chest_signals',None) is not None and self.chest_signals.ready)) or self.session.hidden):
                        if motion:motion.reset()
                        obs=Observation('hidden',started,reason='Overlay oculto' if self.session.hidden else 'Selecione o que procurar')
                    elif rect.is_found:
                        try:
                            p=recognizer.pack
                            fraction=min(1.,max(.35,p.map_ui_roi[1]+p.map_ui_roi[3],p.gameplay_ui_roi[1]+p.gameplay_ui_roi[3])+.01)
                            if motion.previous_surface=='map':frame=self.native.capture(rect)
                            else:
                                frame=self.native.capture(rect,fraction)
                                if frame is not None and template_visible(frame,p.map_ui,p.map_ui_roi):frame=self.native.capture(rect)
                            obs=motion.observe(frame,started)
                        except MemoryError:
                            if self.settings.get('performance_mode')=='global':self.events.put(('performance_fallback',epoch,True))
                            obs=Observation('hidden',started,reason='Memória insuficiente para a referência atual')
                        except ReferenceCancelled:
                            obs=Observation('hidden',started,reason='Seleção substituída')
                        except Exception:
                            logger.exception("Falha no reconhecimento")
                            obs=Observation("hidden",started,reason="Não foi possível reconhecer a tela")
                    elapsed=time.monotonic()-started
                    self._publish((self.rect_key(rect),obs,epoch),frame)
                    current=epoch==self.selection_epoch
                    state=(obs.surface,obs.reason,epoch)
                    if state!=last_log_state or started-last_log>=1:
                        writer.writerow([round(started,3),obs.surface if current else 'hidden',round(elapsed*1000,1),round(obs.confidence,3),obs.error_px,
                                         obs.reason if current else 'Seleção substituída',context[0],obs.map_id or context[1],obs.layer_id or context[2],epoch])
                        log.flush();last_log=started;last_log_state=state
                    if performance is not None:
                        try:performance.record(recognizer,self.settings.get('performance_mode','light'),obs.surface,rect.is_found and self.native.foreground(rect))
                        except OSError:
                            try:performance.close()
                            except OSError:pass
                            performance=None;logger.warning('Diagnóstico de desempenho interrompido')
                    interval=.05 if rect.is_found and self.native.foreground(rect) and recognizer is not None and self.session.selected and not self.session.hidden else .25
                    self.stop_event.wait(max(.005,interval-elapsed))

        except Exception as exc:
            logger.exception("Falha no serviço ao vivo"); self.events.put(("error",str(exc)))
        finally:
            if motion: motion.close(wait=True)
            if active_recognizer is not None and hasattr(active_recognizer,'close'):active_recognizer.close()
            self.native.close_capture()
            if performance is not None:performance.close()
            self.reference_released.set()

    def _tick(self):
        if self.stop_event.is_set(): return
        foreground=False
        try:
            self.poll_catalog()
            rect=self.native.game(); foreground=self.native.foreground(rect); key=self.rect_key(rect)
            self.sync_panel_visibility(rect)
            if self.menu_open:
                # Keep the visibility shortcut responsive while a menu owns input.
                while True:
                    try: action=self.events.get_nowait()
                    except queue.Empty: break
                    if action=="visibility": self.toggle_visibility()
                    elif action=="panel":
                        self.close_marker_menu(restore_focus=False);self.panel_shortcut()
                    elif isinstance(action,tuple) and action[0]=='automark_event':
                        logger.info('AutoMark result=ignored reason=marker_card_open event=%s',action[2].token)
                    elif isinstance(action,tuple): self.session.notice=action[1]
                if (key!=self.menu_geometry or not rect.is_found or rect.is_minimized
                        or time.monotonic()>self.menu_deadline or self.session.hidden
                        or not self.native.menu_foreground(rect)):
                    self.close_marker_menu()
                else:
                    # Keep the explicit item selection, never old map coordinates.
                    if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
                    self.canvas.delete("all")
                    if hasattr(self,"renderer"): self.renderer.clear()
                    if hasattr(self,"display_motion"): self.display_motion.reset()
                    self.visible_pins=[]
                    self.root.after(16,self._tick)
                    return
            if key!=self.geometry_key:
                self.session.invalidate("Localizando após mudança de janela…"); self.geometry_key=key
            try:
                observation_key,obs,epoch=self.latest.get_nowait()
                if observation_key==key and epoch==self.selection_epoch: self.session.observation=obs
            except queue.Empty: pass
            if not foreground:
                if hasattr(self,'automark'):self.automark.reset()
                self.session.invalidate("Volte ao Genshin para continuar" if rect.is_found else "Aguardando o Genshin abrir…",
                                        clear_pending=not rect.is_found)
            while True:
                try: action=self.events.get_nowait()
                except queue.Empty: break
                if action=="panel" and (self.panel_detached or foreground or self.native.menu_foreground(rect) or not rect.is_found):
                    self.panel_shortcut()
                elif isinstance(action,tuple) and action[0]=='performance_fallback':
                    if action[1]==self.selection_epoch:
                        self.settings['performance_mode']='light';self.performance_var.set('Leve')
                        self.session.notice='Cobertura global indisponível por memória. Modo Leve ativado.'
                        if len(action)>2 and action[2]:self.reload_reference()
                        self.persist_settings()
                elif action=="visibility": self.toggle_visibility()
                elif isinstance(action,tuple) and action[0]=='automark_event':
                    if (foreground and action[1]==self.selection_epoch and self.settings.get('automark')
                            and self.chest_signals.ready and not self.region_loading):
                        outcome=self.automark.apply(action[2],self.session,time.monotonic())
                        logger.info('AutoMark result=%s reason=%s event=%s candidates=%s',outcome,
                                    self.automark.last_reason,action[2].token,self.automark.last_candidates)
                        if outcome=='marked':self.refresh_counts()
                elif isinstance(action,tuple) and action[0]=='automark_unresolved':
                    if foreground and action[1]==self.selection_epoch:
                        self.session.notice='AutoMark: abertura sem posição comprovada. Use o atalho de coleta para escolher.'
                elif action=="collect" and foreground and not self.region_loading: self.collect_shortcut(rect)
                elif action=="undo" and foreground and not self.region_loading: self.session.undo()
                elif isinstance(action,tuple): self.session.notice=action[1]
            now=time.monotonic()
            display=self.display_motion.present(self.session.observation,now)
            self.session.marker_dpi=self.native.dpi_scale(rect.hwnd) if rect.hwnd else 1.
            pins=self.session.pins(rect.width,rect.height,now,include_collected=self.control_down,
                                   observation=display) if foreground and not self.overlay_error and not self.region_loading else []
            controls=self.control_rectangles(rect)
            pins=outside_controls(pins,controls)
            exclusion_key=(rect.width,rect.height,tuple(controls))
            if self.overlay_hwnd and rect.width>0 and rect.height>0 and exclusion_key!=self.overlay_exclusions:
                self.native.exclude_controls(self.overlay_hwnd,rect.width,rect.height,controls)
                self.overlay_exclusions=exclusion_key
            self.visible_pins=pins
            self.displayed_at=now
            self.displayed_observation=display
            if pins and self.overlay_hwnd:
                self.native.place(self.overlay_hwnd,rect)
                if getattr(self,'canvas_size',None)!=(rect.width,rect.height):
                    self.canvas.configure(width=rect.width,height=rect.height);self.canvas_size=(rect.width,rect.height)
                self.renderer.render(pins,self.session.is_collected)
            elif self.overlay_hwnd:
                self.native.hide(self.overlay_hwnd)
                self.renderer.clear()
            if not foreground: self.display_motion.reset()
            if self.telemetry:
                try: self.telemetry.record(self.session.region_id,self.session.observation,display,pins,now)
                except OSError:
                    logger.exception("Métricas de desenho interrompidas")
                    self.telemetry.close();self.telemetry=None
            self._sync_input(rect)
            self.raise_attached_controls()
            status=self.overlay_error or self.reference_error or self.session.observation.reason
            if self.session.hidden: status="Overlay oculto · use o atalho para mostrar"
            elif not self.session.selected and not self.reference_error: status+=" · selecione o que procurar"
            elif foreground and self.session.observation.surface!="hidden" and not self.session.observation.fresh(time.monotonic()):
                status="Localização atrasada · ícones ocultos"
            status+=" · cobertura em validação"
            status+=' · '+('Global' if self.settings.get('performance_mode')=='global' else 'Leve')
            if self.status.get()!=status:self.status.set(status)
            if self.notice.get()!=self.session.notice:self.notice.set(self.session.notice)
            if self.listener and self.listener.registration_errors:
                self.notice.set("Um atalho está em uso por outro programa. Escolha outra tecla e salve.")
            if time.monotonic()-self.counts_at>=1:
                if self.refresh_counts() is not False:self.counts_at=time.monotonic()
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
            self.visible_pins=[];self.displayed_observation=None
            if self.input_hwnd:
                self.native.interactive(self.input_hwnd,False);self.native.hide(self.input_hwnd)
            if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
            self.session.invalidate("Overlay pausado após uma falha"); self.session.notice=str(exc)
        self.root.after(16 if foreground else 100,self._tick)

    def close(self):
        try: self.persist_settings()
        except OSError: logger.exception("Falha ao salvar painel")
        self.stop_event.set()
        self.catalog_loader.close()
        self.catalog_source.close()
        self.count_indices.close()
        if not self.preference_writer.close():logger.error('Preferências pendentes não puderam ser salvas ao encerrar')
        self.close_layers()
        self.close_marker_menu(restore_focus=False)
        if self.listener: self.listener.stop()
        self.control_listener.stop()
        if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
        self.worker.join(timeout=2)
        self.automark_worker.join(timeout=2)
        if self.telemetry: self.telemetry.close()
        self.root.destroy()
        self.native.release_instance()

    def run(self):
        self.root.mainloop()
