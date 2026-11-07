"""Non-modal, game-owned item card; no native menu grab or root focus transfer."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.live.icons import draw_marker
from src.live.catalog import CATEGORIES


LABELS={"common-chest":"Baú comum","exquisite-chest":"Baú sofisticado",
        "precious-chest":"Baú precioso","luxurious-chest":"Baú luxuoso",
        "remarkable-chest":"Baú extraordinário","anemoculus":"Anemoculus"}


class MarkerMenu:
    def __init__(self,parent,native,game,items,progress,on_change,on_close,x,y):
        self.items=items
        self.progress=progress
        self.on_change=on_change
        self.index=0
        self.window=tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg="#cbb88a")
        self.window.bind("<Escape>",lambda event:on_close())
        card=tk.Frame(self.window,bg="#1c2a3b",padx=16,pady=14)
        card.pack(fill="both",expand=True,padx=1,pady=1)
        header=tk.Frame(card,bg="#1c2a3b");header.pack(fill="x")
        self.icon=tk.Canvas(header,width=40,height=40,bg="#1c2a3b",highlightthickness=0)
        self.icon.pack(side="left",padx=(0,8))
        titles=tk.Frame(header,bg="#1c2a3b");titles.pack(side="left",fill="x",expand=True)
        self.title=tk.Label(titles,bg="#1c2a3b",fg="#eee9df",font=("Segoe UI",12,"bold"),anchor="w")
        self.title.pack(fill="x")
        self.badge=tk.Label(titles,bg="#1c2a3b",fg="#a0adbd",font=("Segoe UI",9),anchor="w")
        self.badge.pack(fill="x")
        close=tk.Label(header,text="×",bg="#1c2a3b",fg="#a0adbd",font=("Segoe UI",16),cursor="hand2")
        close.pack(side="right",anchor="n")
        close.bind("<ButtonRelease-1>",lambda event:on_close())
        if len(items)>1:
            tk.Label(card,text="Há itens sobrepostos. Escolha qual alterar:",bg="#1c2a3b",fg="#a0adbd",
                     font=("Segoe UI",9)).pack(anchor="w",pady=(10,4))
            selector=ttk.Combobox(card,state="readonly",width=34,
                                 values=[f"{i+1}. {LABELS.get(item.category,CATEGORIES.get(item.category,(item.name,))[0])}" for i,item in enumerate(items)])
            selector.pack(fill="x")
            selector.current(0)
            selector.bind("<<ComboboxSelected>>",lambda event:self.select(selector.current()))
        tk.Frame(card,bg="#3c495b",height=1).pack(fill="x",pady=12)
        self.action=self._button(card)
        tk.Label(card,text="Clique fora para voltar ao jogo",bg="#1c2a3b",fg="#a0adbd",
                 font=("Segoe UI",8)).pack(pady=(10,0))
        self.select(0)
        self.window.update_idletasks()
        width=self.window.winfo_reqwidth();height=self.window.winfo_reqheight()
        # Clamp to the game client, including monitors with negative origins.
        x=max(game.x,min(x,game.x+game.width-width))
        y=max(game.y,min(y,game.y+game.height-height))
        self.bounds=(x,y,x+width,y+height)
        self.window.geometry(f"{width}x{height}{x:+d}{y:+d}")
        self.window.update_idletasks()
        self.hwnd=native.popup(self.window.winfo_id(),game)
        from src.overlay.window_tracker import GameWindowRect
        native.place(self.hwnd,GameWindowRect(x,y,width,height))

    def _button(self,parent):
        widget=tk.Label(parent,font=("Segoe UI",10,"bold"),padx=12,pady=9,anchor="w",cursor="hand2")
        widget.pack(fill="x",pady=3)
        widget.bind("<ButtonRelease-1>",lambda event:self._activate())
        widget.bind("<Enter>",lambda event:self._hover(True))
        widget.bind("<Leave>",lambda event:self._hover(False))
        return widget

    def _activate(self):
        identifier=self.items[self.index].id
        self.on_change(identifier,not self.progress.is_collected(identifier))

    def _hover(self,hover):
        collected=self.progress.is_collected(self.items[self.index].id)
        bg=("#354860" if hover else "#293b51") if collected else ("#e8d5a7" if hover else "#cbb88a")
        self.action.configure(bg=bg,fg="#eee9df" if collected else "#1c2a3b")

    def select(self,index):
        self.index=index
        item=self.items[index]
        collected=self.progress.is_collected(item.id)
        self.title.configure(text=LABELS.get(item.category,CATEGORIES.get(item.category,(item.name,))[0]))
        detail=self.progress.respawn_text(item) if hasattr(self.progress,"respawn_text") else ""
        self.badge.configure(text=detail or ("Já pego" if collected else "Ainda não pego"),wraplength=265,justify="left")
        self.icon.delete("all")
        draw_marker(self.icon,item.category,20,21,1.6,collected=collected)
        self.action.configure(text="↺  Desmarcar item" if collected else "✓  Marcar como pego")
        self._hover(False)

    def contains(self,x,y):
        left,top,right,bottom=self.bounds
        return left<=x<right and top<=y<bottom

    def destroy(self):
        self.window.destroy()
