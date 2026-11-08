"""Compact exploration controls. No game assets and no game input automation."""
import tkinter as tk
from tkinter import ttk

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS
from src.live.icons import draw_marker
from src.live.storage import HOTKEY_OPTIONS
from src.live.category_browser import CategoryBrowser, CategoryModel
from src.live.nation_selector import NationSelector
from src.live.identity import DISPLAY_NAME

BG = '#111923'
ROW = '#1b2734'
TEXT = '#edf1f5'
GOLD = '#dfc48d'
MUTED = '#91a0b2'


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
        style.configure('TFrame',background=BG)
        style.configure('TLabel',background=BG,foreground=TEXT,font=('Segoe UI',9))
        style.configure('TButton',background=ROW,foreground=TEXT,padding=(10,7),borderwidth=0,font=('Segoe UI',9))
        style.map('TButton',background=[('active','#283747')],foreground=[('disabled','#586474')])
        style.configure('Quiet.TButton',background=BG,padding=(6,5),foreground=MUTED)
        style.map('Quiet.TButton',background=[('active',ROW)],foreground=[('active',TEXT)])
        style.configure('Primary.TButton',background=GOLD,foreground='#17202a',font=('Segoe UI',9,'bold'))
        style.map('Primary.TButton',background=[('active','#f0dca9')],foreground=[('active','#17202a')])
        style.configure('TCombobox',fieldbackground=ROW,background=ROW,foreground=TEXT,arrowcolor=MUTED,padding=6,borderwidth=0)
        style.map('TCombobox',fieldbackground=[('readonly',ROW)],foreground=[('readonly',TEXT)])
        style.configure('TEntry',fieldbackground=ROW,foreground=TEXT,insertcolor=TEXT,padding=7,borderwidth=0,bordercolor=ROW,lightcolor=ROW,darkcolor=ROW)
        style.configure('Compact.TNotebook',borderwidth=0,bordercolor=BG,lightcolor=BG,darkcolor=BG)
        style.configure('TScrollbar',background='#344152',troughcolor=BG,borderwidth=0,arrowsize=10)
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.layout('Compact.TNotebook.Tab',[])
        style.layout('Compact.TNotebook',[('Notebook.client',{'sticky':'nswe'})])
        self.shell=tk.Frame(self.root,bg=BG);self.shell.pack(fill='both',expand=True)
        header=tk.Frame(self.shell,bg=BG);header.pack(fill='x',padx=16,pady=(10,6))
        title=tk.Label(header,text=DISPLAY_NAME,bg=BG,fg=TEXT,font=('Segoe UI',15,'bold'));title.pack(side='left')
        for widget in (header,title):
            widget.bind('<Button-1>',self.start_panel_drag)
            widget.bind('<B1-Motion>',self.drag_panel)
            widget.bind('<ButtonRelease-1>',self.finish_panel_drag)
        ttk.Button(header,text='—',width=3,style='Quiet.TButton',command=self.collapse_to_game).pack(side='right')
        ttk.Button(header,text='⚙',width=3,style='Quiet.TButton',command=self.show_settings).pack(side='right',padx=3)
        self.capture_eye=tk.Canvas(header,width=28,height=28,bg=BG,highlightthickness=0,cursor='hand2',takefocus=1)
        self.capture_eye.pack(side='right',padx=3)
        self.capture_eye.bind('<Button-1>',lambda e:self.toggle_capture_visibility())
        self.capture_eye.bind('<Return>',lambda e:self.toggle_capture_visibility())
        self.capture_eye.bind('<space>',lambda e:self.toggle_capture_visibility())
        self.paint_capture_eye()
        self.tabs=ttk.Notebook(self.shell,style='Compact.TNotebook');self.tabs.pack(fill='both',expand=True,padx=16)
        self.explore=ttk.Frame(self.tabs);self.prefs=ttk.Frame(self.tabs)
        self.tabs.add(self.explore,text='Itens');self.tabs.add(self.prefs,text='Ajustes')
        if self.catalogs.appsample_available:
            self.source_var=tk.StringVar(value='AppSample' if self.package_id=='appsample' else 'Kongying')
        scope=ttk.Frame(self.explore);scope.pack(fill='x',pady=(0,2))
        self.region_names={r['name']:r['id'] for r in self.catalogs.regions.values()}
        if self.package_id=='legacy-mondstadt' or (self.package_id=='appsample' and self.settings.get('last_kongying_package')=='legacy-mondstadt'):
            self.region_names['Mondstadt · compatibilidade']='legacy-mondstadt'
        active_region=self.settings.get('last_kongying_package','mondstadt') if self.package_id=='appsample' else self.package_id
        self.region_var=tk.StringVar(value=next((k for k,v in self.region_names.items() if v==active_region),next(iter(self.region_names))))
        self.region_box=NationSelector(scope,self.region_var,self.region_names,self.change_region,self.close_layers)
        self.region_box.pack(side='left',fill='x',expand=True)
        self.source_caption=tk.Label(scope,text='APPSAMPLE',bg=BG,fg=MUTED,font=('Segoe UI',8,'bold'),anchor='w',pady=7)
        if hasattr(self,'source_var'):self.sync_source_controls()
        self.layer_var=tk.StringVar()
        button=tk.Canvas(scope,width=30,height=30,bg=BG,highlightthickness=0,cursor='hand2');button.pack(side='right',padx=(8,0))
        for cy in (20,15,10):button.create_polygon(7,cy,15,cy-4,23,cy,15,cy+4,fill=BG,outline=GOLD)
        button.bind('<Button-1>',self.open_layers)
        self.territory_path=tk.StringVar()
        territory_label=tk.Label(self.explore,textvariable=self.territory_path,bg=BG,fg=MUTED,font=('Segoe UI',8),anchor='w',wraplength=320)
        def show_territory(*args):
            if self.package_id=='appsample':
                if not territory_label.winfo_manager():territory_label.pack(fill='x',pady=(0,5),after=scope)
            else:
                territory_label.pack_forget()
                layer=self.territory_path.get().split(' · ')[-1].replace('Todos os mapas','Automático')
                self.region_box.detail=layer
                self.region_box.draw()
        self.territory_path.trace_add('write',show_territory)
        search=ttk.Frame(self.explore);search.pack(fill='x')
        self.category_query=tk.StringVar()
        search_entry=ttk.Entry(search,textvariable=self.category_query)
        search_entry.pack(side='left',fill='x',expand=True)
        placeholder=tk.Label(search,text='Buscar itens…',bg=ROW,fg=MUTED,font=('Segoe UI',9),cursor='xterm')
        def search_hint(*args):
            if not self.category_query.get() and self.root.focus_get()!=search_entry:placeholder.place(in_=search_entry,x=7,y=5)
            else:placeholder.place_forget()
        placeholder.bind('<Button-1>',lambda e:search_entry.focus_set())
        search_entry.bind('<FocusIn>',search_hint);search_entry.bind('<FocusOut>',search_hint)
        self.category_query.trace_add('write',search_hint);search_hint()
        ttk.Button(search,text='Limpar',style='Quiet.TButton',command=lambda:self.set_categories(False)).pack(side='right',padx=(5,0))
        self.category_query.trace_add('write',lambda *a:self.filter_categories())
        hints=ttk.Frame(self.explore);hints.pack(fill='x',pady=(5,3))
        ttk.Label(hints,text='ITENS',foreground=MUTED,font=('Segoe UI',8)).pack(side='left')
        ttk.Button(hints,text='Selecionar todos',style='Quiet.TButton',command=lambda:self.set_categories(True)).pack(side='right')
        farm=tk.Frame(self.explore,bg=ROW,padx=6,pady=6)
        farm.pack(side='bottom',fill='x',pady=(8,0))
        farm_actions=tk.Frame(farm,bg=ROW);farm_actions.pack(fill='x')
        self.farm_button=ttk.Button(farm_actions,text='Farmar baús',style='Primary.TButton',command=self.toggle_farm)
        self.farm_button.pack(side='left',fill='x',expand=True)
        self.farm_next=ttk.Button(farm_actions,text='Próximo',command=self.next_farm_target,state='disabled');self.farm_next.pack(side='right',padx=(6,0))
        self.farm_hint=tk.StringVar()
        farm_hint_label=tk.Label(farm,textvariable=self.farm_hint,bg=ROW,fg=MUTED,font=('Segoe UI',8),wraplength=300,anchor='w')
        def show_farm_hint(*args):
            if self.farm_hint.get():farm_hint_label.pack(fill='x',pady=(5,0))
            else:farm_hint_label.pack_forget()
        self.farm_hint.trace_add('write',show_farm_hint)
        listing=ttk.Frame(self.explore);listing.pack(fill='both',expand=True,pady=(1,0))
        canvas=CategoryBrowser(listing,self.choose_categories,height=150)
        scroll=ttk.Scrollbar(listing,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True);canvas.connect_scrollbar(scroll)
        self.category_browser=canvas;self.category_canvas=canvas
        self.category_vars={};self.category_labels={};self.category_widgets=[]
        self.populate_region_controls()
        self.candidates=ttk.Combobox(self.explore,state='readonly')
        self.confirm_button=ttk.Button(self.explore,text='Confirmar selecionado',command=self.confirm_candidate)
        self.progress_text=tk.StringVar();self.progress_value=tk.DoubleVar()
        information=tk.Frame(self.shell,bg=BG);information.pack(side='bottom',fill='x',before=self.tabs,padx=16,pady=(7,10))
        tk.Frame(information,bg='#2a3543',height=1).pack(fill='x',pady=(0,5))
        tk.Label(information,textvariable=self.progress_text,bg=BG,fg=MUTED,font=('Segoe UI',8),wraplength=325,anchor='w').pack(fill='x')
        self.status=tk.StringVar(value='Procurando o Genshin…');summary=tk.StringVar()
        def summarize_status(*args):summary.set(self.status.get().split(' · ')[0])
        self.status.trace_add('write',summarize_status);summarize_status()
        tk.Label(information,textvariable=summary,bg=BG,fg=MUTED,font=('Segoe UI',8),wraplength=325,anchor='w').pack(fill='x',pady=(2,0))
        self.notice=tk.StringVar()
        notice_label=tk.Label(information,textvariable=self.notice,bg=BG,fg=GOLD,font=('Segoe UI',8),wraplength=325,anchor='w')
        footer=ttk.Frame(information);footer.pack(fill='x',pady=(7,0))
        self.visibility_button=ttk.Button(footer,text='Ocultar ícones',style='Quiet.TButton',command=self.toggle_visibility);self.visibility_button.pack(side='left')
        ttk.Button(footer,text='Desfazer',style='Quiet.TButton',command=self.panel_undo).pack(side='left')
        ttk.Button(footer,text='Jogar',style='Primary.TButton',width=9,command=self.collapse_to_game).pack(side='right')
        def show_notice(*args):
            if self.notice.get():notice_label.pack(fill='x',before=footer)
            else:notice_label.pack_forget()
        self.notice.trace_add('write',show_notice)
        prefs_canvas=tk.Canvas(self.prefs,bg=BG,highlightthickness=0)
        prefs_scroll=ttk.Scrollbar(self.prefs,orient='vertical',command=prefs_canvas.yview)
        prefs_scroll.pack(side='right',fill='y');prefs_canvas.pack(side='left',fill='both',expand=True)
        prefs_canvas.configure(yscrollcommand=prefs_scroll.set)
        prefs_body=ttk.Frame(prefs_canvas)
        prefs_window=prefs_canvas.create_window(0,0,window=prefs_body,anchor='nw')
        prefs_body.bind('<Configure>',lambda e:prefs_canvas.configure(scrollregion=prefs_canvas.bbox('all')))
        prefs_canvas.bind('<Configure>',lambda e:prefs_canvas.itemconfigure(prefs_window,width=e.width))
        ttk.Button(prefs_body, text='‹ Voltar aos itens', command=lambda: self.tabs.select(self.explore)).pack(fill='x', pady=5)
        self.panel_mode_button=ttk.Button(prefs_body,text='Fixar ao jogo' if self.panel_detached else 'Destacar',command=self.toggle_panel_mode)
        self.panel_mode_button.pack(fill='x',pady=5)
        self.capture_button=ttk.Button(prefs_body,text=self.capture_label(),command=self.toggle_capture_visibility)
        self.capture_button.pack(fill='x',pady=5)
        ttk.Label(prefs_body,text='Para transmitir os pins, compartilhe a tela inteira. Capturar só a janela do jogo pode não incluir o overlay.',wraplength=295,foreground=MUTED).pack(fill='x',pady=(0,6))
        if self.catalogs.appsample_available:
            source_row=ttk.Frame(prefs_body);source_row.pack(fill='x',pady=6)
            ttk.Label(source_row,text='Fonte de dados').pack(side='left')
            source_box=ttk.Combobox(source_row,textvariable=self.source_var,values=['Kongying','AppSample'],state='readonly',width=13)
            source_box.pack(side='right');source_box.bind('<<ComboboxSelected>>',self.change_source)
        ttk.Label(prefs_body, text='Atalhos globais').pack(anchor='w', pady=5)
        self.key_vars = {}
        for action, label in (('panel', 'Abrir / recolher painel'), ('visibility', 'Mostrar / ocultar ícones'),
                              ('collect', 'Coletar próximo'), ('undo', 'Desfazer coleta'),
                              ('farm','Iniciar / parar farm'),('farm_next','Pular baú-alvo')):
            row = ttk.Frame(prefs_body); row.pack(fill='x', pady=4)
            ttk.Label(row, text=label).pack(side='left')
            var = tk.StringVar(value=self.settings['hotkeys'][action]); self.key_vars[action] = var
            ttk.Combobox(row, textvariable=var, values=HOTKEY_OPTIONS, state='readonly', width=15).pack(side='right')
        ttk.Button(prefs_body, text='Salvar atalhos', command=self.save_keys).pack(fill='x', pady=7)
        ttk.Label(prefs_body, text='Ctrl + clique: marcar ou desmarcar.\nSegure Ctrl para revelar os itens pegos.\nServidor de reposição: América.').pack(anchor='w', pady=5)
        ttk.Button(prefs_body, text='Verificar referências', command=self.reload_reference).pack(fill='x', pady=5)
        ttk.Button(prefs_body, text='Encerrar overlay', command=self.close).pack(fill='x', pady=5)
        if self.catalogs.appsample_available:
            ttk.Button(prefs_body,text='Importar coletados do AppSample…',command=self.import_appsample_progress).pack(fill='x',pady=3)
        ttk.Label(prefs_body,textvariable=self.status,wraplength=300,foreground=MUTED).pack(fill='x',pady=8)
        def scroll_preferences(event):
            prefs_canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
        def bind_preferences(widget):
            widget.bind('<MouseWheel>',scroll_preferences)
            for child in widget.winfo_children():bind_preferences(child)
        bind_preferences(prefs_canvas)
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

    def capture_label(self):
        return 'Captura: visível' if self.settings.get('capture_visible',False) else 'Captura: oculta'

    def paint_capture_eye(self):
        c=self.capture_eye;c.delete('all');visible=self.settings.get('capture_visible',False)
        color=GOLD if visible else MUTED
        c.create_line(3,14,8,9,14,7,20,9,25,14,20,19,14,21,8,19,3,14,fill=color,smooth=True,width=1.5)
        c.create_oval(11,11,17,17,fill=color,outline='')
        if not visible:c.create_line(5,24,24,5,fill=color,width=2)

    def toggle_capture_visibility(self):
        value=not self.settings.get('capture_visible',False)
        try:self.native.set_capture_visible(value)
        except OSError as exc:
            self.session.notice=str(exc);return
        self.settings['capture_visible']=value
        self.paint_capture_eye();self.capture_button.configure(text=self.capture_label())
        self.session.notice='Overlay visível no compartilhamento de tela.' if value else 'Overlay oculto no compartilhamento de tela.'
        try:self.persist_settings()
        except OSError as exc:self.session.notice=f'Visibilidade alterada; preferência não salva: {exc}'

    def toggle_farm(self):
        if getattr(self,'region_loading',False):return
        farm=self.session.farm
        if farm.enabled:farm.stop()
        else:farm.start(self.session)
        self.farm_button.configure(text='Parar farm' if farm.enabled else 'Farmar baús')
        self.farm_next.configure(state='normal' if farm.enabled else 'disabled')
        self.session.notice='' if farm.enabled else 'Farm encerrado.'

    def next_farm_target(self):
        if self.session.farm.enabled:self.session.farm.skip()

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
