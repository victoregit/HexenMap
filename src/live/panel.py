"""Compact exploration controls with user-supplied branding."""
from src.live.i18n import tr as _tr
import tkinter as tk
import webbrowser
from tkinter import ttk

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS
from src.live.category_browser import CategoryBrowser, CategoryModel
from src.live.identity import DISPLAY_NAME, VERSION
from src.live.brand import AnimatedBadge, apply_app_icon, TRANSPARENT
from src.live.support import report_problem
from src.live.nation_map_button import NationMapButton
from src.live.control_icons import draw_elemental_sight

from src.live.theme import (BG, SURFACE as ROW, TEXT, ACCENT as GOLD, MUTED,
                            BORDER, ON_ACCENT, apply_theme, panel_size, place_dialog, Tooltip)
from src.live.panel_layout import PanelLayout,fitted_size


class CompactPanel(PanelLayout):
    def _panel(self):
        apply_app_icon(self.root)
        self.panel_collapsed = False
        self.layer_popup = None
        self.panel_suspended = False
        pref = self.settings.get('panel', {})
        self.panel_detached=pref.get('detached') is not False
        self.root.overrideredirect(not self.panel_detached)
        self.root.attributes('-topmost', not self.panel_detached)
        self.root.resizable(self.panel_detached,self.panel_detached)
        self.root.configure(bg=BG, highlightbackground=BORDER, highlightthickness=0)
        left,top,right,bottom=self.panel_desktop_bounds()
        if hasattr(self.native,'work_area'):
            left,top,right,bottom=self.native.work_area(pref.get('x',32),pref.get('y',80))
        self.panel_dpi=self.native.dpi_scale(self.root.winfo_id()) if hasattr(self.native,'dpi_scale') else 1.
        self.root._visual_scale=pref.get('scale',100)/100
        self.ui_scale=self.panel_dpi*self.root._visual_scale
        default_width,default_height=panel_size(self.ui_scale,(left,top,right,bottom))
        self.panel_normal_size=fitted_size(pref.get('width',default_width/self.ui_scale),pref.get('height',default_height/self.ui_scale),self.ui_scale,(left,top,right,bottom))
        width,height=self.panel_normal_size
        x=max(left,min(pref.get('x',32),right-width))
        y=max(top,min(pref.get('y',80),bottom-height-round(32*self.ui_scale)))
        self.last_panel_position=(x,y)
        self.root.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.root.minsize(40, 40)
        self.root._lunar_native=self.native
        apply_theme(self.root,self.ui_scale)
        self.shell=tk.Frame(self.root,bg=BG);self.shell.pack(fill='both',expand=True)
        header=tk.Frame(self.shell,bg=BG);header.pack(fill='x',padx=14,pady=(8,6))
        branding=tk.Frame(header,bg=BG);branding.pack(side='left')
        title=tk.Label(branding,text=_tr(DISPLAY_NAME),bg=BG,fg=TEXT,font=('Segoe UI',14,'bold'),anchor='w');title.pack(fill='x')
        subtitle=tk.Label(branding,text=_tr('Seu companheiro de exploração'),bg=BG,fg=MUTED,font=('Segoe UI',8),anchor='w');subtitle.pack(fill='x')
        self.profile_caption=subtitle
        if hasattr(self,'profile_store'):
            name=self.profile_store.name();subtitle.configure(text=_tr('Perfil: ')+(name if len(name)<=24 else name[:23]+'…'))
        for widget in (header,branding,title,subtitle):
            widget.bind('<Button-1>',self.start_panel_drag)
            widget.bind('<B1-Motion>',self.drag_panel)
            widget.bind('<ButtonRelease-1>',self.finish_panel_drag)
        collapse=ttk.Button(header,text='—',width=3,style='Quiet.TButton',command=self.collapse_to_game)
        collapse.pack(side='right');Tooltip(collapse,_tr('Recolher o painel e voltar ao jogo (F8).'))
        self.capture_eye=tk.Canvas(header,width=28,height=28,bg=BG,highlightthickness=0,cursor='hand2',takefocus=1)
        self.capture_eye.pack(side='right',padx=3)
        self.capture_eye.bind('<Button-1>',lambda e:self.toggle_capture_visibility())
        self.capture_eye.bind('<Return>',lambda e:self.toggle_capture_visibility())
        self.capture_eye.bind('<space>',lambda e:self.toggle_capture_visibility())
        self.paint_capture_eye()
        Tooltip(self.capture_eye,_tr('Mostrar ou ocultar o overlay no compartilhamento de tela.'))
        self.planet_button=NationMapButton(header,self.open_world_map,bg=BG)
        self.planet_button.pack(side='right',padx=2)
        Tooltip(self.planet_button,_tr('Abrir mapa geral de Teyvat: arraste, aproxime e confira seus coletados.'))
        self.tabs=ttk.Notebook(self.shell,style='Compact.TNotebook');self.tabs.pack(fill='both',expand=True,padx=14)
        self.explore=ttk.Frame(self.tabs);self.prefs=ttk.Frame(self.tabs)
        self.tabs.add(self.explore,text=_tr('Itens'));self.tabs.add(self.prefs,text=_tr('Ajustes'))
        navigation=ttk.Frame(self.shell,style='Card.TFrame',padding=4)
        navigation.pack(fill='x',padx=14,pady=(0,8),before=self.tabs)
        navigation.columnconfigure((0,1),weight=1)
        self.items_tab=ttk.Button(navigation,text=_tr('⌖  Itens'),command=lambda:self.tabs.select(self.explore))
        self.settings_tab=ttk.Button(navigation,text=_tr('☷  Ajustes'),command=self.show_settings)
        self.items_tab.grid(row=0,column=0,sticky='ew',padx=(0,3))
        self.settings_tab.grid(row=0,column=1,sticky='ew',padx=(3,0))
        def sync_navigation(event=None):
            exploring=self.tabs.select()==str(self.explore)
            self.items_tab.configure(style='Nav.Selected.TButton' if exploring else 'Nav.TButton')
            self.settings_tab.configure(style='Nav.TButton' if exploring else 'Nav.Selected.TButton')
        self.tabs.bind('<<NotebookTabChanged>>',sync_navigation);sync_navigation()
        self.region_names={'AppSample':'appsample'}
        self.region_var=tk.StringVar(value=_tr('AppSample'))
        self.layer_var=tk.StringVar();self.territory_path=tk.StringVar()
        search=ttk.Frame(self.explore);search.pack(fill='x')
        self.category_query=tk.StringVar()
        search_box=ttk.Frame(search,style='Input.TFrame',padding=(7,3));search_box.pack(fill='x',expand=True)
        search_entry=ttk.Entry(search_box,textvariable=self.category_query,style='Lunar.TEntry')
        magnifier=tk.Canvas(search_box,width=21,height=23,bg=ROW,highlightthickness=0)
        self.search_icon=magnifier
        magnifier.pack(side='left',padx=(2,3))
        magnifier.create_oval(3,4,13,14,outline=MUTED);magnifier.create_line(12,13,17,18,fill=MUTED)
        magnifier.bind('<Button-1>',lambda e:search_entry.focus_set())
        search_entry.pack(side='left',fill='x',expand=True)
        placeholder=tk.Label(search,text=_tr('O que você quer encontrar?'),bg=ROW,fg=MUTED,font=('Segoe UI',9),cursor='xterm')
        def search_hint(*args):
            if not self.category_query.get() and self.root.focus_get()!=search_entry:placeholder.place(in_=search_entry,x=7,y=5)
            else:placeholder.place_forget()
        placeholder.bind('<Button-1>',lambda e:search_entry.focus_set())
        search_entry.bind('<FocusIn>',search_hint);search_entry.bind('<FocusOut>',search_hint)
        search_entry.bind('<FocusIn>',lambda e:search_box.state(['focus']),add='+')
        search_entry.bind('<FocusOut>',lambda e:search_box.state(['!focus']),add='+')
        self.category_query.trace_add('write',search_hint);search_hint()
        self.category_query.trace_add('write',lambda *a:self.filter_categories())
        hints=ttk.Frame(self.explore);hints.pack(fill='x',pady=(5,3))
        ttk.Label(hints,text=_tr('Seleção'),foreground=MUTED,font=('Segoe UI',8)).pack(side='left')
        ttk.Button(hints,text=_tr('Limpar seleção'),style='Quiet.TButton',command=lambda:self.set_categories(False)).pack(side='right')
        ttk.Button(hints,text=_tr('Selecionar todos'),style='Quiet.TButton',command=lambda:self.set_categories(True)).pack(side='right')
        listing=ttk.Frame(self.explore);listing.pack(fill='both',expand=True,pady=(1,0))
        canvas=CategoryBrowser(listing,self.choose_categories,height=150)
        scroll=ttk.Scrollbar(listing,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True);canvas.connect_scrollbar(scroll)
        self.category_browser=canvas;self.category_canvas=canvas
        self.category_vars={};self.category_labels={};self.category_widgets=[]
        self.populate_region_controls()
        self.candidates=ttk.Combobox(self.explore,state='readonly')
        self.confirm_button=ttk.Button(self.explore,text=_tr('Confirmar selecionado'),command=self.confirm_candidate)
        self.progress_text=tk.StringVar();self.progress_value=tk.DoubleVar()
        information=tk.Frame(self.shell,bg=BG);information.pack(side='bottom',fill='x',before=self.tabs,padx=16,pady=(5,5))
        self.build_automark_controls(information)
        tk.Frame(information,bg=BORDER,height=1).pack(fill='x',pady=(0,5))
        tk.Label(information,textvariable=self.progress_text,bg=BG,fg=MUTED,font=('Segoe UI',8),wraplength=325,anchor='w').pack(fill='x')
        self.status=tk.StringVar(value=_tr('Procurando o Genshin…'));summary=tk.StringVar()
        def summarize_status(*args):summary.set(_tr(self.status.get().split(' · ')[0]))
        self.status.trace_add('write',summarize_status);summarize_status()
        tk.Label(information,textvariable=summary,bg=BG,fg=MUTED,font=('Segoe UI',8),wraplength=325,anchor='w').pack(fill='x',pady=(2,0))
        self.notice=tk.StringVar()
        notice_label=tk.Label(information,textvariable=self.notice,bg=BG,fg=GOLD,font=('Segoe UI',8),wraplength=325,anchor='w')
        footer=ttk.Frame(information);footer.pack(fill='x',pady=(7,0))
        play=ttk.Button(footer,text=_tr('Jogar'),style='Primary.TButton',width=7,command=self.collapse_to_game)
        play.pack(side='right');Tooltip(play,_tr('Recolher o painel e devolver o foco ao Genshin.'))
        bottom=tk.Frame(footer,bg=BG);bottom.pack(side='left',fill='x',expand=True)
        self.report_button=ttk.Button(bottom,text=_tr('Report'),style='Quiet.TButton',command=lambda:report_problem(self.root))
        self.report_button.pack(side='left')
        self.support_button=ttk.Button(bottom,text=_tr('Apoiar'),style='Quiet.TButton',
                                      command=lambda:webbrowser.open('https://buymeacoffee.com/victorsilva'))
        self.support_button.pack(side='left',padx=(2,0))
        Tooltip(self.support_button,_tr('Apoiar o Hexen Map no Buy Me a Coffee.'))
        self.version_label=tk.Label(information,text=_tr('v{0}', VERSION),bg=BG,fg=MUTED,
                                    font=('Segoe UI',8),anchor='e')
        self.version_label.pack(fill='x',pady=(2,0))
        def show_notice(*args):
            if self.notice.get():notice_label.pack(fill='x',before=footer)
            else:notice_label.pack_forget()
        self.notice.trace_add('write',show_notice)
        from src.live.settings_panel import build_settings
        self.settings_canvas=build_settings(self,self.prefs,bg=BG,muted=MUTED)
        scale=self.native.dpi_scale(self.root.winfo_id()) if hasattr(self.native,'dpi_scale') else 1.
        self.compact_size=max(76,round(76*scale))
        self.compact=AnimatedBadge(self.root,self.compact_size)
        self.compact.bind('<Return>',lambda event:self.toggle_panel())
        self.compact.bind('<space>',lambda event:self.toggle_panel())
        self.compact.bind('<Button-1>', self.start_panel_drag)
        self.compact.bind('<B1-Motion>', self.drag_panel)
        self.compact.bind('<ButtonRelease-1>', self.expand_or_drag)
        self.root.update_idletasks()
        self.native.panel(self.root.winfo_id())
        self.move_panel_to(x,y)
        self.setup_panel_resize()
        if pref.get('collapsed'):self.toggle_panel(save=False)

    def build_scope_controls(self,parent):
        scope=ttk.Frame(parent);scope.pack(fill='x',pady=(0,2))
        self.source_caption=tk.Label(scope,text=_tr('◎  Mapa  ⌄'),bg=BG,fg=TEXT,font=('Segoe UI',9),anchor='w',pady=7,cursor='hand2',takefocus=1)
        self.source_caption.pack(side='left',fill='x',expand=True)
        self.source_caption.bind('<Button-1>',self.open_layers)
        self.source_caption.bind('<Return>',self.open_layers)
        Tooltip(self.source_caption,_tr('Selecionar mapa do AppSample. A seleção permanece fixa ao viajar.'))
        layer_caption=tk.Label(scope,text=_tr('Superfície'),bg=BG,fg=TEXT,font=('Segoe UI',8),cursor='hand2')
        layer_caption.pack(side='right')
        layer_caption.bind('<Button-1>',self.open_layers)
        button=tk.Canvas(scope,width=30,height=30,bg=BG,highlightthickness=0,cursor='hand2');button.pack(side='right',padx=(8,0))
        self.layer_button=button
        for cy in (20,15,10):button.create_polygon(7,cy,15,cy-4,23,cy,15,cy+4,fill=BG,outline=GOLD)
        button.bind('<Button-1>',self.open_layers)
        button.configure(takefocus=1);button.bind('<Return>',self.open_layers);button.bind('<space>',self.open_layers)
        Tooltip(button,_tr('Escolher mapa e camada. A seleção permanece fixa ao viajar.'))
        def show_territory(*args):
            path=self.territory_path.get().split(' · ',1)
            name=path[0]
            self.source_caption.configure(text='◎  '+(name if len(name)<=24 else name[:23]+'…')+'  ⌄')
            layer=path[1] if len(path)>1 else 'Camada'
            layer_caption.configure(text=_tr(layer) if len(layer)<=18 else _tr(layer[:17])+'…')
        self.territory_path.trace_add('write',show_territory);show_territory()

    def build_automark_controls(self,parent):
        from PIL import Image,ImageDraw,ImageTk
        scale=self.ui_scale;style=ttk.Style(self.root)
        element='AutoMarkSwitch'+str(round(scale*100))
        images=[]
        for active,disabled in ((False,False),(True,False),(False,True)):
            w=max(28,round(34*scale));h=max(16,round(18*scale));ss=3
            image=Image.new('RGBA',(w*ss,h*ss));draw=ImageDraw.Draw(image)
            draw.rounded_rectangle((0,0,w*ss-1,h*ss-1),radius=h*ss/2,
                                   fill=BORDER if disabled else GOLD if active else '#3C4054')
            r=h*ss/2-3*ss;cx=w*ss-h*ss/2 if active else h*ss/2;cy=h*ss/2
            draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=MUTED if disabled else '#F3EEFC')
            images.append(ImageTk.PhotoImage(image.resize((w,h),Image.Resampling.LANCZOS),master=self.root))
        self.root._automark_switch_images=images
        if element not in style.element_names():
            style.element_create(element,'image',images[0],('disabled',images[2]),('selected',images[1]),sticky='e')
        style.layout('AutoMark.TCheckbutton',[('Checkbutton.padding',{'sticky':'nswe','children':[
            (element,{'side':'right','sticky':'e'}),('Checkbutton.label',{'side':'left','sticky':'w'})]})])
        style.configure('AutoMark.TCheckbutton',background=ROW,foreground=TEXT,
                        font=('Segoe UI',round(9*self.root._visual_scale),'bold'),padding=(0,3))
        style.map('AutoMark.TCheckbutton',background=[('active',ROW)],foreground=[('disabled',MUTED),('focus',GOLD)])
        self.automark_card=ttk.Frame(parent,style='Card.TFrame',padding=(11,8))
        self.automark_card.pack(fill='x',pady=(0,8))
        row=tk.Frame(self.automark_card,bg=ROW);row.pack(fill='x')
        self.automark_var=tk.BooleanVar(value=self.settings.get('automark',False))
        self.automark_toggle=ttk.Checkbutton(row,text=_tr('AutoMark de baús · Beta'),style='AutoMark.TCheckbutton',
            variable=self.automark_var,command=self.change_automark)
        self.automark_toggle.pack(side='left',fill='x',expand=True)
        self.automark_resync_button=ttk.Button(row,text='↻',width=3,style='Card.Quiet.TButton',command=self.resync_automark)
        self.automark_resync_button.pack(side='right',padx=(4,0))
        Tooltip(self.automark_resync_button,_tr('Sincronizar novamente a tela e a posição do AutoMark.'))
        Tooltip(self.automark_toggle,_tr('Reconhece a abertura e as recompensas para marcar um baú próximo sem ambiguidade. Use Desfazer para corrigir uma coleta.'))
        self.automark_sync_text=tk.StringVar(value=_tr('Volte ao Genshin para sincronizar a tela e a posição.')
            if self.settings.get('automark') else _tr('AutoMark desligado.'))
        self.automark_sync_label=tk.Label(self.automark_card,textvariable=self.automark_sync_text,
            bg=ROW,fg=MUTED,anchor='w',justify='left',wraplength=260,font=('Segoe UI',8))
        self.automark_sync_label.bind('<Configure>',lambda event:self.automark_sync_label.configure(wraplength=max(100,event.width))
            if int(self.automark_sync_label.cget('wraplength'))!=max(100,event.width) else None)
        def refresh(*args):
            ready=self.chest_signals.ready;enabled=self.automark_var.get() and ready
            self.automark_resync_button.state(['!disabled'] if enabled else ['disabled'])
            if enabled or not ready:self.automark_sync_label.pack(fill='x',pady=(3,0))
            else:self.automark_sync_label.pack_forget()
            if not ready:
                self.automark_toggle.state(['disabled'])
                self.automark_sync_text.set(_tr('Indisponível: confira as referências em Ajustes → Diagnóstico.'))
        self.automark_var.trace_add('write',refresh);refresh()

    def change_automark(self):
        self.settings['automark']=self.automark_var.get() and self.chest_signals.ready
        self.resync_automark()
        self.persist_settings()

    def resync_automark(self):
        self.automark.reset();self.automark_generation+=1
        if hasattr(self,'automark_sync_text'):
            self.automark_sync_text.set(_tr('Volte ao Genshin para sincronizar a tela e a posição.')
                                       if self.settings.get('automark') else _tr('AutoMark desligado.'))

    def update_automark_sync(self):
        from src.live.automark_service import synchronization_message
        if not self.chest_signals.ready:text=_tr('Indisponível: confira as referências em Ajustes → Diagnóstico.')
        elif not self.settings.get('automark'):text=_tr('AutoMark desligado.')
        elif self.session.hidden:text=_tr('Mostre o overlay para sincronizar o AutoMark.')
        elif self.region_loading:text=_tr('Carregando referências…')
        elif self.automark_service.sync_context!=(self.automark_generation,self.selection_epoch):
            text=_tr('Sincronizando tela e posição…')
        else:text=_tr(synchronization_message(self.automark_service.sync_state))
        if self.automark_sync_text.get()!=text:self.automark_sync_text.set(_tr(text))

    def show_settings(self):
        self.tabs.select(self.prefs)

    def capture_label(self):
        return _tr('Compartilhamento: ícones visíveis') if self.settings.get('capture_visible',False) else _tr('Compartilhamento: ícones ocultos')

    def paint_capture_eye(self):
        c=self.capture_eye;c.delete('all');visible=self.settings.get('capture_visible',False)
        color=GOLD if visible else MUTED
        draw_elemental_sight(c,color,BG,visible,getattr(c,'_icon_scale',1.))

    def toggle_capture_visibility(self):
        value=not self.settings.get('capture_visible',False)
        try:self.native.set_capture_visible(value)
        except OSError as exc:
            self.session.notice=_tr(str(exc));return
        self.settings['capture_visible']=value
        self.paint_capture_eye();self.capture_button.configure(text=_tr(self.capture_label()))
        self.session.notice=_tr('Overlay visível no compartilhamento de tela.') if value else _tr('Overlay oculto no compartilhamento de tela.')
        try:self.persist_settings()
        except OSError as exc:self.session.notice=_tr('Visibilidade alterada; preferência não salva: {0}', exc)

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
        width, height = (self.compact_size, self.compact_size) if self.panel_collapsed else getattr(self,'panel_normal_size',(360,540))
        rect = self.native.game()
        if (self.panel_collapsed or not self.panel_detached) and rect.is_found and not rect.is_minimized:
            left,top,right,bottom=rect.x,rect.y,rect.x+rect.width,rect.y+rect.height
        else:left,top,right,bottom=self.panel_desktop_bounds()
        x = max(left, min(x+dx, right-width)); y = max(top, min(y+dy, bottom-height))
        self.move_panel_to(x,y)
        if self.panel_collapsed and rect.is_found:
            self._compact_offset=(x-rect.x,y-rect.y)

    def compact_position(self,game,follow=False):
        """Keep the collapsed eye inside the client, including offset monitors."""
        x,y=self.last_panel_position
        if game.is_found and not game.is_minimized and min(game.width,game.height)>0:
            left,top,right,bottom=game.x,game.y,game.x+game.width,game.y+game.height
            if follow and hasattr(self,'_compact_offset'):
                x,y=left+self._compact_offset[0],top+self._compact_offset[1]
            margin=min(12,max(0,(min(game.width,game.height)-self.compact_size)//2))
            x=max(left+margin,min(x,right-self.compact_size-margin))
            y=max(top+margin,min(y,bottom-self.compact_size-margin))
            self._compact_offset=(x-left,y-top)
        else:
            left,top,right,bottom=self.panel_desktop_bounds()
            x=max(left,min(x,right-self.compact_size));y=max(top,min(y,bottom-self.compact_size))
        return round(x),round(y)

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

    def panel_mode_label(self):
        return _tr('Fixar ao Genshin') if self.panel_detached else _tr('Desprender do Genshin')

    def toggle_panel_mode(self):
        self.close_layers()
        if self.panel_collapsed:self.toggle_panel(save=False)
        self.panel_detached=not self.panel_detached
        self.root.overrideredirect(not self.panel_detached)
        self.root.attributes('-topmost',not self.panel_detached)
        self.update_panel_constraints()
        self.root.update_idletasks();self.native.panel(self.root.winfo_id())
        self.panel_mode_button.configure(text=_tr(self.panel_mode_label()))
        self.panel_suspended=False
        self.root.deiconify()
        self.finish_panel_drag()

    def finish_panel_drag(self, event=None):
        try: self.persist_settings()
        except OSError as exc: self.session.notice = _tr(str(exc))

    def expand_or_drag(self, event):
        if not self.panel_dragged:
            self.toggle_panel()
            self.root.focus_force()
        else: self.finish_panel_drag()

    def _animate_panel_collapse(self,save,return_to_game):
        from src.live.panel_transition import PanelCollapseTransition,HANDOFF_MS
        if not hasattr(self.native,'panel_mask') or not hasattr(self.native,'control_bounds') or not self.root.winfo_viewable():return False
        if getattr(self,'_layout_busy',False):return False
        self.panel_position();self.close_layers();self.root.update_idletasks()
        try:bounds=self.native.control_bounds(self.root.winfo_id())
        except (OSError,tk.TclError):return False
        if bounds is None:return False
        target=self.compact_position(self.native.game())
        def complete():
            self._panel_transition=None
            game=self.native.game()
            allowed=not game.is_found or self.native.menu_foreground(game)
            if not allowed:self.root.withdraw()
            self.compact.play_from(HANDOFF_MS)
            self._apply_panel_state(True,save)
            if allowed:
                self.root.deiconify()
                self.move_panel_to(*target)
            self.panel_suspended=not allowed
            if return_to_game and allowed:self.native.restore_game_focus(game)
        try:
            transition=PanelCollapseTransition(self.root,self.native,bounds,
                                               target,self.compact_size,complete)
        except (OSError,tk.TclError):return False
        self._panel_transition=transition;self._layout_busy=True
        try:transition.start()
        except (OSError,tk.TclError):transition.finish()
        return True

    def toggle_panel(self, save=True, animate=True, return_to_game=False):
        transition=getattr(self,'_panel_transition',None)
        if transition is not None:
            transition.finish();return
        if self.panel_detached and not self.panel_collapsed and self.root.state()=='iconic':
            self.root.deiconify();self.root.lift();self.root.focus_force()
            return
        # Saved-state restoration stays immediate; only user actions animate.
        if not self.panel_collapsed and animate and save:
            if self._animate_panel_collapse(save,return_to_game):return
        self._apply_panel_state(not self.panel_collapsed,save)
        if return_to_game and self.panel_collapsed:self.native.restore_game_focus(self.native.game())

    def _apply_panel_state(self,collapsed,save=True):
        self.panel_position();self.close_layers()
        self.panel_collapsed=collapsed
        self._layout_busy=True
        self.update_panel_constraints()
        if self.panel_collapsed:
            self.root.overrideredirect(True)
            self.root.attributes('-topmost',True)
            self.root.attributes('-transparentcolor',TRANSPARENT)
            self.root.configure(bg=TRANSPARENT,highlightthickness=0)
            self.shell.pack_forget();self.compact.pack()
            self.root.geometry(f'{self.compact_size}x{self.compact_size}')
        else:
            self.compact.pack_forget();self.shell.pack(fill='both',expand=True)
            self.root.attributes('-transparentcolor','')
            self.root.configure(bg=BG,highlightthickness=0)
            self.root.overrideredirect(not self.panel_detached)
            self.root.attributes('-topmost',not self.panel_detached)
            self.root.geometry('%dx%d'%getattr(self,'panel_normal_size',(360,540)))
            self.root.deiconify();self.root.lift()
            if self.panel_detached:self.root.focus_force()
        self.root.update_idletasks();self.native.panel(self.root.winfo_id())
        if collapsed:self.move_panel_to(*self.compact_position(self.native.game()))
        self._layout_busy=False
        self.panel_suspended=False
        if save:self.finish_panel_drag()

    def collapse_to_game(self):
        if not self.panel_collapsed:self.toggle_panel(return_to_game=True)
        else:self.native.restore_game_focus(self.native.game())

    def sync_panel_visibility(self, rect):
        transition=getattr(self,'_panel_transition',None)
        if transition is not None:
            if rect.is_found and not self.native.menu_foreground(rect):transition.finish()
            else:return
        if self.panel_detached and not self.panel_collapsed:
            if self.panel_suspended:
                self.native.show_panel(self.root.winfo_id());self.panel_suspended=False
            return
        if self.panel_collapsed and rect.is_found and not rect.is_minimized:
            position=self.compact_position(rect,follow=True)
            if position!=self.last_panel_position:self.move_panel_to(*position)
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
        transition=getattr(self,'_panel_transition',None)
        for window in (self.root,self.layer_popup,getattr(transition,'window',None)):
            if window is None:continue
            occluder=game.hwnd if window is self.root and self.panel_detached and not self.panel_collapsed else None
            bounds=self.native.control_bounds(window.winfo_id(),occluder=occluder)
            if bounds:
                left,top,right,bottom=bounds
                rectangles.append((left-game.x-2,top-game.y-2,right-game.x+2,bottom-game.y+2))
        return rectangles

    def raise_attached_controls(self):
        if not self.panel_detached or self.panel_collapsed:self.native.above_icons(self.root.winfo_id())
        if self.layer_popup:self.native.above_icons(self.layer_popup.winfo_id())
        transition=getattr(self,'_panel_transition',None)
        if transition is not None and transition.window is not None:
            self.native.above_icons(transition.window.winfo_id())

    def panel_shortcut(self):
        self.toggle_panel(return_to_game=not self.panel_collapsed)
        if not self.panel_collapsed and not getattr(self,'_panel_transition',None) and not self.panel_detached:
            self.root.deiconify();self.root.lift();self.root.focus_force()

    def open_layers(self, event=None):
        if getattr(self,'region_loading',False):return
        if self.layer_popup:
            self.close_layers(); return
        popup = self.layer_popup = tk.Toplevel(self.root)
        popup.overrideredirect(True); popup.attributes('-topmost', True)
        popup.configure(bg=BG, highlightbackground=GOLD, highlightthickness=1)
        place_dialog(popup,self.root,(340,300))
        top = ttk.Frame(popup); top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text=_tr('Mapas e camadas')).pack(side='left')
        ttk.Button(top, text='×', width=3, command=self.close_layers).pack(side='right')
        query = tk.StringVar()
        entry = ttk.Entry(popup, textvariable=query); entry.pack(fill='x', padx=8)
        container = ttk.Frame(popup); container.pack(fill='both', expand=True, padx=8, pady=6)
        listing = tk.Listbox(container, bg=ROW, fg=TEXT, selectbackground=GOLD, selectforeground=ON_ACCENT,
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
        # Counts cover the territory, independently of the visible categories.
        try:self.persist_settings()
        except OSError as exc:self.session.notice=_tr('Falha ao salvar preferências: {0}', exc)

    def filter_categories(self):
        job=getattr(self,'category_filter_job',None)
        if job is not None:self.root.after_cancel(job)
        def apply():
            self.category_filter_job=None
            self.category_browser.filter(self.category_query.get())
        self.category_filter_job=self.root.after(65,apply)
