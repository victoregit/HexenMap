"""Non-modal, game-owned item card; no native menu grab or root focus transfer."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk

from src.live.icons import draw_marker
from src.live.category_art import draw_category_art
from src.live.catalog import CATEGORIES
from src.live.marker_hints import marker_url
from src.live.theme import BG, SURFACE, TEXT, MUTED, ACCENT, BORDER, apply_theme, Tooltip


LABELS={"common-chest":"Baú comum","exquisite-chest":"Baú sofisticado",
        "precious-chest":"Baú precioso","luxurious-chest":"Baú luxuoso",
        "remarkable-chest":"Baú extraordinário","anemoculus":"Anemoculus"}


class MarkerMenu:
    def __init__(self,parent,native,game,items,progress,on_change,on_close,x,y,hints=None):
        self.items=items
        self.native=native;self.game=game
        self.progress=progress
        self.on_change=on_change
        self.index=0
        self.hints=hints
        self.hint_job=None
        self.hint_generation=0
        self.photo_generation=0
        self.photos=[]
        self.photo_index=0
        self.photo_image=None
        self.photo_original=None;self.viewer=None;self.escape_consumed=False
        apply_theme(parent.winfo_toplevel(),getattr(parent.winfo_toplevel(),'_lunar_signature',1.))
        self.window=tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=BG)
        self.window.bind("<Escape>",lambda event:on_close())
        card=ttk.Frame(self.window,style='Card.TFrame',padding=(16,14))
        card.pack(fill="both",expand=True,padx=1,pady=1)
        header=tk.Frame(card,bg=SURFACE);header.pack(fill="x")
        self.icon=tk.Canvas(header,width=40,height=40,bg=SURFACE,highlightthickness=0)
        self.icon.pack(side="left",padx=(0,8))
        titles=tk.Frame(header,bg=SURFACE);titles.pack(side="left",fill="x",expand=True)
        self.title=tk.Label(titles,bg=SURFACE,fg=TEXT,font=("Segoe UI",12,"bold"),anchor="w")
        self.title.pack(fill="x")
        self.badge=tk.Label(titles,bg=SURFACE,fg=MUTED,font=("Segoe UI",9),anchor="w")
        self.badge.pack(fill="x")
        close=tk.Label(header,text="×",bg=SURFACE,fg=MUTED,font=("Segoe UI",16),cursor="hand2")
        close.pack(side="right",anchor="n")
        close.bind("<ButtonRelease-1>",lambda event:on_close())
        Tooltip(close,'Fechar cartão (Esc).')
        if len(items)>1:
            tk.Label(card,text="Há itens sobrepostos. Escolha qual alterar:",bg=SURFACE,fg=MUTED,
                     font=("Segoe UI",9)).pack(anchor="w",pady=(10,4))
            selector=ttk.Frame(card);selector.pack(fill='x')
            ttk.Button(selector,text='◀ Item anterior',takefocus=False,
                       command=lambda:self.select((self.index-1)%len(self.items))).pack(side='left')
            ttk.Button(selector,text='Próximo item ▶',takefocus=False,
                       command=lambda:self.select((self.index+1)%len(self.items))).pack(side='right')
        tk.Frame(card,bg=BORDER,height=1).pack(fill="x",pady=12)
        self.action=self._button(card)
        if hints is not None:
            tk.Label(card,text='Fotos do local · AppSample',bg=SURFACE,fg=ACCENT,
                     font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(10,4))
            self.hint_status=tk.Label(card,bg=SURFACE,fg=MUTED,font=('Segoe UI',8),anchor='w',wraplength=360)
            self.hint_status.pack(fill='x')
            self.photo_size=(min(480,max(240,game.width-90)),min(300,max(80,game.height-360)))
            self.photo_canvas=tk.Canvas(card,width=self.photo_size[0],height=self.photo_size[1],
                                        bg=BG,highlightthickness=0)
            self.photo_canvas.pack(pady=6)
            self.photo_canvas.bind('<Button-1>',lambda event:self.open_photo())
            Tooltip(self.photo_canvas,'Clique na foto para ampliar. Roda: zoom; arraste para navegar.')
            navigation=tk.Frame(card,bg=SURFACE);navigation.pack(fill='x',pady=(0,6))
            self.previous_photo=ttk.Button(navigation,text='◀ Anterior',style='Card.TButton',command=lambda:self._show_photo(-1),takefocus=False)
            self.previous_photo.pack(side='left')
            self.photo_counter=tk.Label(navigation,bg=SURFACE,fg=TEXT,font=('Segoe UI',9))
            self.photo_counter.pack(side='left',expand=True)
            self.next_photo=ttk.Button(navigation,text='Próxima ▶',style='Card.TButton',command=lambda:self._show_photo(1),takefocus=False)
            self.next_photo.pack(side='right')
            links=tk.Frame(card,bg=SURFACE);links.pack(fill='x')
            self.source_link=ttk.Button(links,text='Abrir ponto no AppSample',style='Card.TButton',command=self._open_source,takefocus=False)
            self.source_link.pack(side='left')
            self.refresh_link=ttk.Button(links,text='Atualizar',style='Card.TButton',command=lambda:self._load_hints(True),takefocus=False)
            self.refresh_link.pack(side='right')
        tk.Label(card,text="Clique fora para voltar ao jogo",bg=SURFACE,fg=MUTED,
                 font=("Segoe UI",8)).pack(pady=(10,0))
        self.select(0)
        self.window.update_idletasks()
        width=self.window.winfo_reqwidth();height=self.window.winfo_reqheight()
        if hints is not None and height>game.height:
            self.photo_size=(self.photo_size[0],max(1,self.photo_size[1]-(height-game.height)-8))
            self.photo_canvas.configure(height=self.photo_size[1])
            self.window.update_idletasks()
            width=self.window.winfo_reqwidth();height=self.window.winfo_reqheight()
        # Clamp to the game client, including monitors with negative origins.
        x=max(game.x,min(x,game.x+game.width-width))
        y=max(game.y,min(y,game.y+game.height-height))
        self.bounds=(x,y,x+width,y+height)
        self.window.geometry(f"{width}x{height}{x:+d}{y:+d}")
        self.window.update_idletasks()
        from src.live.noactivate import materialize_controls
        materialize_controls(self.window)
        self.hwnd=native.popup(self.window.winfo_id(),game)
        from src.overlay.window_tracker import GameWindowRect
        native.place(self.hwnd,GameWindowRect(x,y,width,height))

    def _button(self,parent):
        widget=ttk.Button(parent,style='Card.Primary.TButton',command=self._activate,takefocus=False)
        widget.pack(fill='x',pady=3)
        return widget

    def _activate(self):
        identifier=self.items[self.index].id
        self.on_change(identifier,not self.progress.is_collected(identifier))

    def _hover(self,hover):
        collected=self.progress.is_collected(self.items[self.index].id)
        self.action.configure(style='Card.Quiet.TButton' if collected else 'Card.Primary.TButton')

    def select(self,index):
        self.index=index
        item=self.items[index]
        collected=self.progress.is_collected(item.id)
        self.title.configure(text=LABELS.get(item.category,CATEGORIES.get(item.category,(item.name,))[0]))
        detail=self.progress.respawn_text(item) if hasattr(self.progress,"respawn_text") else ""
        self.badge.configure(text=detail or ("Já pego" if collected else "Ainda não pego"),wraplength=265,justify="left")
        self.icon.delete("all")
        if not draw_category_art(self.icon,item.category,20,21,size=34,collected=collected):
            draw_marker(self.icon,item.category,20,21,1.6,collected=collected)
        self.action.configure(text="↺  Desmarcar item" if collected else "✓  Marcar como pego")
        self._hover(False)
        if self.hints is not None:
            self._load_hints()

    def _open_source(self):
        url=marker_url(self.items[self.index])
        if url:
            webbrowser.open(url)

    def _photo_message(self,text):
        self.photo_original=None
        if self.viewer:self.viewer.close()
        self.photo_canvas.configure(cursor='')
        self.photo_image=None
        self.photo_canvas.delete('all')
        width,height=self.photo_size
        self.photo_canvas.create_text(width/2,height/2,text=text,fill=MUTED,
                                      width=width-24,font=('Segoe UI',10),justify='center')

    def _load_hints(self,refresh=False):
        self.hint_generation+=1
        self.photo_generation+=1
        generation=self.hint_generation
        if self.hint_job is not None:
            self.window.after_cancel(self.hint_job)
            self.hint_job=None
        available=marker_url(self.items[self.index]) is not None
        self.source_link.configure(state='normal' if available else 'disabled')
        self.refresh_link.configure(state='disabled')
        self.photos=[]
        self.photo_counter.configure(text='')
        self.previous_photo.configure(state='disabled');self.next_photo.configure(state='disabled')
        self.hint_status.configure(text='Buscando fotos…' if available else 'Fonte sem fotos integradas')
        self._photo_message('Buscando fotos deste ponto…' if available else 'Fotos disponíveis para marcadores do AppSample.')
        future=self.hints.request(self.items[self.index],refresh=refresh)
        self._poll_hints(future,generation)

    def _poll_hints(self,future,generation):
        if generation!=self.hint_generation:
            return
        self.hint_job=None
        if not future.done():
            self.hint_job=self.window.after(80,lambda:self._poll_hints(future,generation))
            return
        result=future.result()
        self.hint_status.configure(text=result.message)
        self.refresh_link.configure(state='normal' if marker_url(self.items[self.index]) else 'disabled')
        self.photos=list(dict.fromkeys(row['image'] for row in result.comments if row['image']))
        self.photo_index=0
        if self.photos:
            self._show_photo()
        else:
            self._photo_message('Nenhuma foto disponível nesta consulta.\nUse Atualizar ou consulte o ponto na fonte.')

    def _show_photo(self,step=0):
        if not self.photos:
            return
        if self.hint_job is not None:
            self.window.after_cancel(self.hint_job)
            self.hint_job=None
        self.photo_index=(self.photo_index+step)%len(self.photos)
        self.photo_generation+=1
        generation=self.photo_generation
        self.photo_counter.configure(text=f'{self.photo_index+1} / {len(self.photos)}')
        state='normal' if len(self.photos)>1 else 'disabled'
        self.previous_photo.configure(state=state);self.next_photo.configure(state=state)
        self._photo_message('Carregando foto…')
        self.hint_status.configure(text='Carregando foto do AppSample…')
        future=self.hints.request_image(self.photos[self.photo_index])
        self._poll_photo(future,generation)

    def _poll_photo(self,future,generation):
        if generation!=self.photo_generation:
            return
        self.hint_job=None
        if not future.done():
            self.hint_job=self.window.after(80,lambda:self._poll_photo(future,generation))
            return
        result=future.result()
        self.hint_status.configure(text=result.message)
        if result.image is None:
            self._photo_message(result.message)
            return
        image=result.image.copy()
        self.photo_original=result.image.copy();self.photo_canvas.configure(cursor='hand2')
        image.thumbnail(self.photo_size,Image.Resampling.LANCZOS)
        self.photo_image=ImageTk.PhotoImage(image,master=self.window)
        self.photo_canvas.delete('all')
        width,height=self.photo_size
        self.photo_canvas.create_image(width/2,height/2,image=self.photo_image)

    def contains(self,x,y):
        if self.viewer and self.viewer.contains(x,y):return True
        left,top,right,bottom=self.bounds
        return left<=x<right and top<=y<bottom

    def destroy(self):
        if self.viewer:self.viewer.close()
        self.hint_generation+=1
        self.photo_generation+=1
        if self.hint_job is not None:
            self.window.after_cancel(self.hint_job)
            self.hint_job=None
        self.window.destroy()

    def open_photo(self):
        if self.photo_original is None:return
        if self.viewer:self.viewer.window.lift();return
        from src.live.photo_viewer import PhotoViewer
        def closed():self.viewer=None;self.escape_consumed=True
        self.viewer=PhotoViewer(self.window,self.photo_original,closed,native=self.native,game=self.game)

    def escape_key(self,down):
        if not down:self.escape_consumed=False;return False
        if self.escape_consumed:return False
        if self.viewer:
            self.escape_consumed=True;self.viewer.close();return False
        return True
