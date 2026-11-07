"""Compact exploration controls. No game assets and no game input automation."""
import tkinter as tk
from tkinter import ttk

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS
from src.live.icons import draw_marker
from src.live.storage import HOTKEY_OPTIONS
from src.live.category_browser import CategoryBrowser, CategoryModel
from src.live.nation_selector import NationSelector

BG = '#141e2d'
ROW = '#1c2a3b'
TEXT = '#eee9df'
GOLD = '#cbb88a'
MUTED = '#a0adbd'


class CompactPanel:
    def _panel(self):
        self.panel_collapsed = False
        self.layer_popup = None
        self.panel_suspended = False
        pref = self.settings.get('panel', {})
        self.panel_detached=pref.get('detached') is not False
        self.root.overrideredirect(not self.panel_detached)
        self.root.attributes('-topmost', not self.panel_detached)
        self.root.resizable(False,False)
        self.root.configure(bg=BG, highlightbackground='#3c495b', highlightthickness=1)
        left,top,right,bottom=self.panel_desktop_bounds()
        x=max(left,min(pref.get('x',32),right-360))
        y=max(top,min(pref.get('y',80),bottom-580))
        self.last_panel_position=(x,y)
        self.root.geometry('360x540+32+80')
        self.root.minsize(40, 40)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 9))
        style.configure('TButton', background=ROW, foreground=TEXT, padding=(7, 4), borderwidth=0)
        style.map('TButton', background=[('active', '#2b3d54')])
        style.configure('TCheckbutton', background=ROW, foreground=TEXT, padding=2)
        style.map('TCheckbutton', background=[('active', '#2b3d54')])
        style.configure('TCombobox', fieldbackground=ROW, background=ROW, foreground=TEXT, arrowcolor=GOLD, padding=4)
        style.map('TCombobox', fieldbackground=[('readonly', ROW)], foreground=[('readonly', TEXT)])
        style.configure('TEntry', fieldbackground=ROW, foreground=TEXT, insertcolor=TEXT, padding=4)
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=ROW, foreground=TEXT, padding=(8, 3))
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill='both', expand=True)
        header = tk.Frame(self.shell, bg=BG)
        header.pack(fill='x', padx=10, pady=(7, 4))
        title = tk.Label(header, text='Exploração', bg=BG, fg=TEXT, font=('Segoe UI', 10, 'bold'))
        title.pack(side='left')
        for widget in (header, title):
            widget.bind('<Button-1>', self.start_panel_drag)
            widget.bind('<B1-Motion>', self.drag_panel)
            widget.bind('<ButtonRelease-1>', self.finish_panel_drag)
        ttk.Button(header, text='—', width=3, command=self.collapse_to_game).pack(side='right')
        ttk.Button(header, text='⚙', width=3, command=self.show_settings).pack(side='right', padx=3)
        self.panel_mode_button=ttk.Button(header,text='Fixar ao jogo' if self.panel_detached else 'Destacar',command=self.toggle_panel_mode)
        self.panel_mode_button.pack(side='right',padx=3)
        self.tabs = ttk.Notebook(self.shell)
        self.tabs.pack(fill='both', expand=True, padx=9)
        self.explore = ttk.Frame(self.tabs)
        self.prefs = ttk.Frame(self.tabs)
        self.tabs.add(self.explore, text='Itens')
        self.tabs.add(self.prefs, text='Ajustes')
        # Tabs are switched by the gear/back button to keep the main view quiet.
        style.layout('Compact.TNotebook.Tab', [])
        self.tabs.configure(style='Compact.TNotebook')
        scope = ttk.Frame(self.explore)
        if self.catalogs.appsample_available:
            source_row=ttk.Frame(self.explore);source_row.pack(fill='x',pady=(3,0))
            ttk.Label(source_row,text='Fonte').pack(side='left')
            self.source_var=tk.StringVar(value='AppSample' if self.package_id=='appsample' else 'Kongying')
            source_box=ttk.Combobox(source_row,textvariable=self.source_var,values=['Kongying','AppSample'],state='readonly',width=15)
            source_box.pack(side='right');source_box.bind('<<ComboboxSelected>>',self.change_source)
        scope.pack(fill='x', pady=(5, 3))
        self.region_names = {r['name']: r['id'] for r in self.catalogs.regions.values()}
        if self.package_id == 'legacy-mondstadt' or (self.package_id=='appsample' and self.settings.get('last_kongying_package')=='legacy-mondstadt'):
            self.region_names['Mondstadt · compatibilidade'] = 'legacy-mondstadt'
        active_region=self.settings.get('last_kongying_package','mondstadt') if self.package_id=='appsample' else self.package_id
        self.region_var = tk.StringVar(value=next((k for k,v in self.region_names.items() if v==active_region),next(iter(self.region_names))))
        box = NationSelector(scope,self.region_var,self.region_names,self.change_region,self.close_layers)
        self.region_box=box
        box.pack(side='left', fill='x', expand=True)
        self.source_caption=tk.Label(scope,text='AppSample · seleção por mapa',bg=BG,fg=GOLD,font=('Segoe UI',9),anchor='w')
        if hasattr(self,'source_var'):self.sync_source_controls()
        self.layer_var = tk.StringVar()
        button = tk.Canvas(scope, width=32, height=28, bg=ROW, highlightthickness=0, cursor='hand2')
        button.pack(side='right', padx=(5, 0))
        for cy in (19, 14, 9):
            button.create_polygon(7, cy, 16, cy-4, 25, cy, 16, cy+4, fill=ROW, outline=GOLD)
        button.bind('<Button-1>', self.open_layers)
        self.territory_path = tk.StringVar()
        tk.Label(self.explore, textvariable=self.territory_path, bg=BG, fg=MUTED,
                 font=('Segoe UI', 8), anchor='w', wraplength=330).pack(fill='x', pady=(0, 5))
        controls = ttk.Frame(self.explore)
        controls.pack(fill='x')
        self.category_query = tk.StringVar()
        ttk.Entry(controls, textvariable=self.category_query).pack(side='left', fill='x', expand=True)
        ttk.Button(controls, text='Todos', command=lambda: self.set_categories(True)).pack(side='left', padx=(4, 2))
        ttk.Button(controls, text='Limpar', command=lambda: self.set_categories(False)).pack(side='left')
        self.category_query.trace_add('write', lambda *a: self.filter_categories())
        tk.Label(self.explore, text='Buscar item ou categoria', bg=BG, fg=MUTED, font=('Segoe UI', 8)).pack(anchor='w')
        listing = ttk.Frame(self.explore)
        listing.pack(fill='both', expand=True, pady=4)
        canvas = CategoryBrowser(listing,self.choose_categories)
        scroll = ttk.Scrollbar(listing, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.connect_scrollbar(scroll)
        self.category_browser=canvas
        self.category_canvas = canvas
        self.category_vars = {}; self.category_labels = {}; self.category_widgets = []
        self.populate_region_controls()
        self.candidates = ttk.Combobox(self.explore, state='readonly')
        self.confirm_button = ttk.Button(self.explore, text='Confirmar selecionado', command=self.confirm_candidate)
        self.progress_text = tk.StringVar()
        self.progress_value = tk.DoubleVar()
        tk.Label(self.shell, textvariable=self.progress_text, bg=BG, fg=TEXT,
                 font=('Segoe UI', 8), wraplength=335, anchor='w').pack(fill='x', padx=10)
        self.status = tk.StringVar(value='Procurando o Genshin…')
        tk.Label(self.shell, textvariable=self.status, bg=BG, fg=MUTED,
                 font=('Segoe UI', 8), wraplength=335, anchor='w').pack(fill='x', padx=10, pady=(2, 0))
        self.notice = tk.StringVar()
        tk.Label(self.shell, textvariable=self.notice, bg=BG, fg=GOLD,
                 font=('Segoe UI', 8), wraplength=335, anchor='w').pack(fill='x', padx=10)
        footer = ttk.Frame(self.shell)
        footer.pack(fill='x', padx=9, pady=6)
        self.visibility_button = ttk.Button(footer, text='Ocultar ícones', command=self.toggle_visibility)
        self.visibility_button.pack(side='left')
        ttk.Button(footer, text='Desfazer', command=self.panel_undo).pack(side='left', padx=4)
        ttk.Button(footer, text='Jogar', command=self.collapse_to_game).pack(side='right')
        ttk.Button(self.prefs, text='‹ Voltar aos itens', command=lambda: self.tabs.select(self.explore)).pack(fill='x', pady=5)
        ttk.Label(self.prefs, text='Atalhos globais').pack(anchor='w', pady=5)
        self.key_vars = {}
        for action, label in (('panel', 'Abrir / recolher painel'), ('visibility', 'Mostrar / ocultar ícones'),
                              ('collect', 'Coletar próximo'), ('undo', 'Desfazer coleta')):
            row = ttk.Frame(self.prefs); row.pack(fill='x', pady=4)
            ttk.Label(row, text=label).pack(side='left')
            var = tk.StringVar(value=self.settings['hotkeys'][action]); self.key_vars[action] = var
            ttk.Combobox(row, textvariable=var, values=HOTKEY_OPTIONS, state='readonly', width=15).pack(side='right')
        ttk.Button(self.prefs, text='Salvar atalhos', command=self.save_keys).pack(fill='x', pady=7)
        ttk.Label(self.prefs, text='Ctrl + clique: marcar ou desmarcar.\nSegure Ctrl para revelar os itens pegos.\nServidor de reposição: América.').pack(anchor='w', pady=5)
        ttk.Button(self.prefs, text='Verificar referências', command=self.reload_reference).pack(fill='x', pady=5)
        ttk.Button(self.prefs, text='Encerrar overlay', command=self.close).pack(fill='x', pady=5)
        if self.catalogs.appsample_available:
            ttk.Button(self.prefs,text='Importar coletados do AppSample…',command=self.import_appsample_progress).pack(fill='x',pady=3)
        self.compact = tk.Canvas(self.root, width=38, height=38, bg=BG, highlightthickness=0, cursor='hand2')
        draw_marker(self.compact, 'anemoculus', 19, 19, scale=1.2)
        self.compact.bind('<Button-1>', self.start_panel_drag)
        self.compact.bind('<B1-Motion>', self.drag_panel)
        self.compact.bind('<ButtonRelease-1>', self.expand_or_drag)
        self.root.update_idletasks()
        self.native.panel(self.root.winfo_id())
        self.move_panel_to(x,y)
        if pref.get('collapsed') and not self.panel_detached:self.toggle_panel(save=False)

    def show_settings(self):
        self.tabs.select(self.prefs)

    def panel_undo(self):
        if getattr(self,'region_loading',False):return
        self.session.undo()
        self.refresh_counts()

    def start_panel_drag(self, event):
        x,y=self.panel_position()
        self.panel_drag = (event.x_root, event.y_root,x,y)
        self.panel_dragged = False

    def drag_panel(self, event):
        sx, sy, x, y = self.panel_drag
        dx, dy = event.x_root-sx, event.y_root-sy
        self.panel_dragged |= abs(dx)+abs(dy) > 4
        width, height = (40, 40) if self.panel_collapsed else (360, 540)
        rect = self.native.game()
        if not self.panel_detached and rect.is_found and not rect.is_minimized:
            left,top,right,bottom=rect.x,rect.y,rect.x+rect.width,rect.y+rect.height
        else:left,top,right,bottom=self.panel_desktop_bounds()
        x = max(left, min(x+dx, right-width)); y = max(top, min(y+dy, bottom-height))
        self.move_panel_to(x,y)

    def panel_desktop_bounds(self):
        if hasattr(self.native,'desktop_bounds'):return self.native.desktop_bounds()
        return 0,0,self.root.winfo_screenwidth(),self.root.winfo_screenheight()

    def panel_position(self):
        if hasattr(self.native,'control_bounds'):
            bounds=self.native.control_bounds(self.root.winfo_id())
            if bounds:self.last_panel_position=bounds[:2]
        elif self.root.state()!='iconic':self.last_panel_position=(self.root.winfo_x(),self.root.winfo_y())
        return self.last_panel_position

    def move_panel_to(self,x,y):
        if hasattr(self.native,'move_panel'):self.native.move_panel(self.root.winfo_id(),x,y)
        else:self.root.geometry(f'+{x}+{y}')
        self.last_panel_position=(x,y)

    def toggle_panel_mode(self):
        self.close_layers()
        if self.panel_collapsed:self.toggle_panel(save=False)
        self.panel_detached=not self.panel_detached
        self.root.overrideredirect(not self.panel_detached)
        self.root.attributes('-topmost',not self.panel_detached)
        self.root.update_idletasks();self.native.panel(self.root.winfo_id())
        self.panel_mode_button.configure(text='Fixar ao jogo' if self.panel_detached else 'Destacar')
        self.panel_suspended=False
        self.root.deiconify()
        self.finish_panel_drag()

    def finish_panel_drag(self, event=None):
        try: self.persist_settings()
        except OSError as exc: self.session.notice = str(exc)

    def expand_or_drag(self, event):
        if not self.panel_dragged:
            self.toggle_panel()
            self.root.focus_force()
        else: self.finish_panel_drag()

    def toggle_panel(self, save=True):
        if self.panel_detached:
            self.close_layers();self.panel_position()
            if self.root.state()=='iconic' or not self.root.winfo_viewable():
                self.root.deiconify();self.root.lift();self.root.focus_force()
            else:
                self.root.iconify();self.native.restore_game_focus(self.native.game())
            if save:self.finish_panel_drag()
            return
        self.panel_collapsed = not self.panel_collapsed
        if self.panel_collapsed:
            self.close_layers()
            self.shell.pack_forget(); self.compact.pack()
            self.root.geometry('40x40')
        else:
            self.compact.pack_forget(); self.shell.pack(fill='both', expand=True)
            self.root.geometry('360x540')
        if save: self.finish_panel_drag()

    def collapse_to_game(self):
        if self.panel_detached:
            self.panel_position();self.root.iconify()
            self.finish_panel_drag()
            self.native.restore_game_focus(self.native.game());return
        if not self.panel_collapsed: self.toggle_panel()
        self.native.restore_game_focus(self.native.game())

    def sync_panel_visibility(self, rect):
        if self.panel_detached:
            if self.panel_suspended:
                self.native.show_panel(self.root.winfo_id());self.panel_suspended=False
            return
        # Never float above unrelated applications. Keep controls available without a game.
        allowed = not rect.is_found or self.native.menu_foreground(rect)
        if not allowed and not self.panel_suspended:
            self.close_layers(); self.root.withdraw(); self.panel_suspended = True
        elif allowed and self.panel_suspended:
            self.native.show_panel(self.root.winfo_id()); self.panel_suspended = False

    def close_layers(self):
        if self.layer_popup:
            self.layer_popup.destroy(); self.layer_popup = None

    def control_rectangles(self, game):
        rectangles=[]
        for window in (self.root,self.layer_popup):
            if window is None:continue
            occluder=game.hwnd if window is self.root and self.panel_detached else None
            bounds=self.native.control_bounds(window.winfo_id(),occluder=occluder)
            if bounds:
                left,top,right,bottom=bounds
                rectangles.append((left-game.x-2,top-game.y-2,right-game.x+2,bottom-game.y+2))
        return rectangles

    def raise_attached_controls(self):
        if not self.panel_detached:self.native.above_icons(self.root.winfo_id())
        if self.layer_popup:self.native.above_icons(self.layer_popup.winfo_id())

    def panel_shortcut(self):
        self.toggle_panel()
        if self.panel_detached:return
        if self.panel_collapsed:self.native.restore_game_focus(self.native.game())
        else:self.root.deiconify();self.root.lift();self.root.focus_force()

    def open_layers(self, event=None):
        if getattr(self,'region_loading',False):return
        if self.layer_popup:
            self.close_layers(); return
        popup = self.layer_popup = tk.Toplevel(self.root)
        popup.overrideredirect(True); popup.attributes('-topmost', True)
        popup.configure(bg=BG, highlightbackground=GOLD, highlightthickness=1)
        popup.geometry(f'340x300+{self.root.winfo_x()+8}+{self.root.winfo_y()+70}')
        popup.update_idletasks()
        self.native.panel(popup.winfo_id())
        top = ttk.Frame(popup); top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text='Mapas e camadas').pack(side='left')
        ttk.Button(top, text='×', width=3, command=self.close_layers).pack(side='right')
        query = tk.StringVar()
        entry = ttk.Entry(popup, textvariable=query); entry.pack(fill='x', padx=8)
        container = ttk.Frame(popup); container.pack(fill='both', expand=True, padx=8, pady=6)
        listing = tk.Listbox(container, bg=ROW, fg=TEXT, selectbackground='#42516a', selectforeground=TEXT,
                             highlightthickness=0, borderwidth=0, font=('Segoe UI', 9), exportselection=False)
        scroll = ttk.Scrollbar(container, command=listing.yview)
        scroll.pack(side='right', fill='y'); listing.pack(fill='both', expand=True)
        listing.configure(yscrollcommand=scroll.set)
        choices = []
        def populate(*args):
            choices[:] = [name for name in self.layer_names if query.get().casefold() in name.casefold()]
            listing.delete(0, 'end')
            for index, name in enumerate(choices):
                listing.insert('end', ('● ' if name == self.layer_var.get() else '   ')+name)
                if name == self.layer_var.get(): listing.selection_set(index); listing.see(index)
        def choose(event=None):
            selected = listing.curselection()
            if selected:
                self.layer_var.set(choices[selected[0]])
                self.close_layers(); self.change_territory()
        listing.bind('<ButtonRelease-1>', choose); listing.bind('<Return>', choose)
        popup.bind('<Escape>', lambda e: self.close_layers())
        popup.bind('<FocusOut>', lambda e: popup.after(80, lambda: self.close_layers()
                   if self.layer_popup is popup and popup.focus_displayof() not in (entry, listing) else None))
        query.trace_add('write', populate); populate(); entry.focus_set()

    def build_category_rows(self, categories):
        metadata=getattr(self,'category_metadata',{})
        self.category_model=CategoryModel(self.session.items,metadata)
        self.category_browser.set_model(self.category_model,self.session.selected)
        self.filter_categories()

    def choose_categories(self, members, selected):
        if getattr(self,'region_loading',False):return
        if selected:self.session.selected.update(members)
        else:self.session.selected.difference_update(members)
        self.close_marker_menu(restore_focus=False)
        self.session.pending_ids.clear()
        self.category_browser.selected=set(self.session.selected)
        self.category_browser.schedule_paint()
        self.counts_at=0
        try:self.persist_settings()
        except OSError as exc:self.session.notice=f'Falha ao salvar preferências: {exc}'

    def filter_categories(self):
        self.category_browser.filter(self.category_query.get())
