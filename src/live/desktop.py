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

from src.live.catalog import CATEGORIES, load_catalog
from src.live.icons import draw_marker, ICON_MARGIN
from src.live.native import Windows
from src.live.motion import MotionRecognizer
from src.live.reference import load_pack, ReferenceUnavailable
from src.live.session import Session
from src.live.storage import bundle_dir, install_dir, read_settings, write_json, HOTKEY_OPTIONS, parse_hotkey
from src.live.vision import Observation, ScreenRecognizer
from src.overlay.global_hotkeys import GlobalHotkeyListener, MOD_NOREPEAT
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
        self.session=Session(load_catalog(bundle_dir()/"data/community/mondstadt"),
                             ProgressManager(str(self.user_dir/"progress.json")))
        self.session.selected=set(self.settings["categories"]) & CATEGORIES.keys()
        self.reference_dir=reference_dir or self.user_dir/"references/mondstadt"
        self.recognizer=None
        self.reference_error=""
        self.reference_lock=threading.Lock()
        self.events=queue.Queue()
        self.latest=queue.Queue(maxsize=1)
        self.stop_event=threading.Event()
        self.listener=None
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
        self.worker=threading.Thread(target=self._worker,name="LiveRecognition",daemon=True)
        self.worker.start()
        self.root.after(50,self._tick)
        self.root.after(10,self._poll_pointer)

    def _panel(self):
        style=ttk.Style(self.root)
        style.theme_use("clam")
        self.root.configure(bg="#111b23")
        style.configure("TFrame",background="#111b23")
        style.configure("TLabel",background="#111b23",foreground="#e7f0ee",font=("Segoe UI",10))
        style.configure("TCheckbutton",background="#111b23",foreground="#e7f0ee",font=("Segoe UI",11))
        style.map("TCheckbutton",background=[("active","#203039")])
        style.configure("TButton",font=("Segoe UI",10),padding=7)
        frame=ttk.Frame(self.root,padding=24)
        frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="Explore sem sair do jogo",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(frame,text="Mondstadt · superfície",foreground="#81d8bd").pack(anchor="w",pady=(4,16))
        self.status=tk.StringVar(value="Procurando o Genshin…")
        ttk.Label(frame,textvariable=self.status,wraplength=410).pack(anchor="w",pady=(0,16))
        ttk.Label(frame,text="O que você quer encontrar?",font=("Segoe UI",11,"bold")).pack(anchor="w")
        self.category_vars={}
        self.category_labels={}
        for category,(label,_) in CATEGORIES.items():
            var=tk.BooleanVar(value=category in self.session.selected)
            self.category_vars[category]=var
            row=ttk.Frame(frame); row.pack(fill="x",pady=2)
            icon=tk.Canvas(row,width=32,height=29,bg="#111b23",highlightthickness=0)
            icon.pack(side="left",padx=(0,5))
            draw_marker(icon,category,16,15,1.3)
            text=tk.StringVar(value=label)
            self.category_labels[category]=text
            ttk.Checkbutton(row,textvariable=text,variable=var,command=self.select_categories).pack(side="left")
        ttk.Label(frame,text="Sem seleção, nenhum ícone aparece.",foreground="#9cadaa").pack(anchor="w",pady=(4,14))
        ttk.Label(frame,text="Ctrl + clique no ícone: marcar ou desmarcar.\nSegure Ctrl para revelar os itens já pegos.",
                  foreground="#9cadaa",font=("Segoe UI",9)).pack(anchor="w",pady=(0,8))
        self.visibility_button=ttk.Button(frame,text="Ocultar overlay",command=self.toggle_visibility)
        self.visibility_button.pack(fill="x")
        keys=ttk.Frame(frame); keys.pack(fill="x",pady=12)
        self.key_vars={}
        for col,(action,label) in enumerate((("visibility","Mostrar/ocultar"),("collect","Coletar próximo"),("undo","Desfazer"))):
            ttk.Label(keys,text=label).grid(row=0,column=col,padx=(0,8),sticky="w")
            var=tk.StringVar(value=self.settings["hotkeys"][action]); self.key_vars[action]=var
            ttk.Combobox(keys,textvariable=var,values=HOTKEY_OPTIONS,state="readonly",width=13).grid(row=1,column=col,padx=(0,8),pady=5)
        ttk.Button(frame,text="Salvar atalhos",command=self.save_keys).pack(anchor="w")
        self.notice=tk.StringVar()
        ttk.Label(frame,textvariable=self.notice,wraplength=410,foreground="#ffd587").pack(anchor="w",pady=(10,4))
        self.candidates=ttk.Combobox(frame,state="readonly")
        self.confirm_button=ttk.Button(frame,text="Confirmar item selecionado",command=self.confirm_candidate)
        self.progress_text=tk.StringVar()
        ttk.Label(frame,textvariable=self.progress_text,foreground="#9cadaa").pack(anchor="w",pady=(10,4))
        ttk.Button(frame,text="Verificar referências novamente",command=self.reload_reference).pack(anchor="w",pady=4)
        ttk.Button(frame,text="Minimizar e continuar jogando",command=self.root.iconify).pack(fill="x",pady=(12,0))

    def persist_settings(self):
        self.settings["categories"]=sorted(self.session.selected)
        write_json(self.settings_path,self.settings)

    def select_categories(self):
        self.session.selected={c for c,v in self.category_vars.items() if v.get()}
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
        try:
            recognizer=ScreenRecognizer(load_pack(self.reference_dir)); error=""
        except (ReferenceUnavailable,ValueError,OSError) as exc:
            recognizer=None; error=str(exc)
        with self.reference_lock:
            self.recognizer=recognizer; self.reference_error=error
        self.session.invalidate("Localizando…")

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
            changed=control!=self.control_down
            self.control_down=control
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

    def close_marker_menu(self, event=None):
        self.menu_open=False
        if self.marker_menu:
            menu=self.marker_menu
            self.marker_menu=None
            try:
                menu.grab_release()
                menu.destroy()
            except tk.TclError:
                pass
        if self.input_hwnd:
            self.native.interactive(self.input_hwnd,False)
            self.native.hide(self.input_hwnd)

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

    def _dismiss_unmapped_menu(self,menu):
        if self.marker_menu==menu and not menu.winfo_ismapped():
            self.close_marker_menu()

    def change_marker_state(self, identifier, collected):
        try:
            rect=self.native.game()
            if time.monotonic()>self.menu_deadline or self.rect_key(rect)!=self.menu_geometry:
                self.session.notice="Menu expirado. Use Ctrl + clique no item novamente."
            else:
                self.session.set_collected(identifier,collected)
        except Exception as exc:
            self.session.notice=f"Falha ao salvar item: {exc}"
            logger.exception("Falha ao salvar pelo menu do marcador")
        finally:
            self.close_marker_menu()

    def open_marker_menu(self, event):
        rect=self.native.game()
        control,_,_=self.native.pointer()
        if not control or not self.native.foreground(rect) or self.menu_open:
            return "break"
        displayed={p.item.id for p in self.visible_pins}
        items=[i for i in self.session.hit_test(rect.width,rect.height,event.x,event.y)
               if i.id in displayed]
        if not items:
            return "break"
        self.menu_open=True
        self.menu_geometry=self.rect_key(rect)
        self.menu_deadline=time.monotonic()+30
        menu=tk.Menu(self.input_surface,tearoff=False)
        self.marker_menu=menu
        def add_actions(target,item):
            collected=self.session.progress.is_collected(item.id)
            target.add_command(label="Marcar como pego",state="disabled" if collected else "normal",
                               command=lambda:self.change_marker_state(item.id,True))
            target.add_command(label="Desmarcar",state="normal" if collected else "disabled",
                               command=lambda:self.change_marker_state(item.id,False))
        if len(items)==1:
            menu.add_command(label=f"{CATEGORIES[items[0].category][0]} · {items[0].id[-8:]}",state="disabled")
            menu.add_separator()
            add_actions(menu,items[0])
        else:
            menu.add_command(label="Escolha o item sobreposto",state="disabled")
            for item in items:
                child=tk.Menu(menu,tearoff=False)
                add_actions(child,item)
                state=" · pego" if self.session.progress.is_collected(item.id) else ""
                menu.add_cascade(label=f"{CATEGORIES[item.category][0]} · {item.id[-8:]}{state}",menu=child)
        menu.add_separator()
        menu.add_command(label="Cancelar",command=self.close_marker_menu)
        # Tk unposts a menu before invoking its command. Destroy it after the
        # command has run, rather than deleting the pending Tcl callback.
        menu.bind("<Unmap>",lambda e:self.root.after_idle(self._dismiss_unmapped_menu,menu) if e.widget==menu else None)
        menu.bind("<Escape>",lambda e:self.close_marker_menu())
        try:
            menu.tk_popup(event.x_root,event.y_root)
        except tk.TclError:
            self.close_marker_menu()
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
            with (self.user_dir/"live-session.csv").open("a",newline="",encoding="utf-8") as log:
                writer=csv.writer(log)
                if log.tell()==0: writer.writerow(["monotonic_s","surface","latency_ms","confidence","p95_px","reason"])
                while not self.stop_event.is_set():
                    started=time.monotonic(); rect=self.native.game()
                    with self.reference_lock:
                        recognizer=self.recognizer; error=self.reference_error
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
                    self._publish((self.rect_key(rect),obs))
                    writer.writerow([round(started,3),obs.surface,round(elapsed*1000,1),round(obs.confidence,3),obs.error_px,obs.reason]); log.flush()
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
                    # Freeze the clicked snapshot while the explicit menu owns input.
                    self.root.after(50,self._tick)
                    return
            if key!=self.geometry_key:
                self.session.invalidate("Localizando após mudança de janela…"); self.geometry_key=key
            try:
                observation_key,obs=self.latest.get_nowait()
                if observation_key==key: self.session.observation=obs
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
                    if self.control_down:
                        self.canvas.create_rectangle(pin.x-ICON_MARGIN,pin.y-ICON_MARGIN,
                                                     pin.x+ICON_MARGIN,pin.y+ICON_MARGIN,
                                                     outline="#b8efd9",width=1)
                    draw_marker(self.canvas,pin.item.category,pin.x,pin.y,
                                collected=self.session.progress.is_collected(pin.item.id))
            elif self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
            self._sync_input(rect)
            status=self.overlay_error or self.reference_error or self.session.observation.reason
            if self.session.hidden: status="Overlay oculto · use o atalho para mostrar"
            elif not self.session.selected and not self.reference_error: status+=" · selecione o que procurar"
            elif foreground and self.session.observation.surface!="hidden" and not self.session.observation.fresh(time.monotonic()):
                status="Localização atrasada · ícones ocultos"
            self.status.set(status); self.notice.set(self.session.notice)
            if self.listener and self.listener.registration_errors:
                self.notice.set("Um atalho está em uso por outro programa. Escolha outra tecla e salve.")
            known=sum(self.session.progress.is_collected(i.id) for i in self.session.items)
            for category,(label,_) in CATEGORIES.items():
                items=[i for i in self.session.items if i.category==category]
                remaining=sum(not self.session.progress.is_collected(i.id) for i in items)
                self.category_labels[category].set(f"{label} · {remaining}/{len(items)}")
            self.progress_text.set(f"{known} de {len(self.session.items)} itens marcados nesta região")
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
        self.close_marker_menu()
        if self.listener: self.listener.stop()
        if self.overlay_hwnd: self.native.hide(self.overlay_hwnd)
        self.worker.join(timeout=2)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
