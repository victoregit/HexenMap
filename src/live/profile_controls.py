"""UI-thread account switching; stale collection actions never cross profiles."""
from src.live.i18n import tr as _tr
import logging
import queue
import tkinter as tk
from tkinter import ttk,simpledialog
from src.live.alerts import showerror,foreground


class ProfileControls:
    def sync_profile_controls(self):
        store=self.profile_store
        self.profile_choices=store.profiles
        self.profile_box.configure(values=[row['name'] for row in self.profile_choices])
        self.profile_var.set(store.name())
        if hasattr(self,'profile_caption'):
            name=store.name();self.profile_caption.configure(text=_tr('Perfil: ')+(name if len(name)<=24 else name[:23]+'…'))

    def use_selected_profile(self):
        name=self.profile_var.get()
        identifier=next(row['id'] for row in self.profile_choices if row['name']==name)
        self.change_profile(identifier)

    def change_profile(self,identifier):
        if identifier==self.profile_store.active:return True
        if self.region_loading:
            self.profile_status.set(_tr('Aguarde o carregamento do catálogo.'));self.sync_profile_controls();return False
        try:
            progress=self.profile_store.open_progress(identifier)
            self.session.progress.save()
            self.close_layers();self.close_marker_menu(restore_focus=False)
            if getattr(self,'world_map',None):self.world_map.close()
            self.profile_store.activate(identifier)
        except Exception as exc:
            logging.getLogger(__name__).exception('Troca de perfil não aplicada')
            self.profile_status.set(_tr('Não foi possível trocar: {0}', exc))
            showerror(_tr('Não foi possível trocar de perfil'),_tr(str(exc))+_tr('\n\nO perfil anterior continua ativo.'),parent=self.root)
            self.sync_profile_controls();return False
        self.session.progress=progress
        self.session.undo_ids.clear();self.session.undo_records.clear()
        self.session.collection_epoch+=1
        self.session.invalidate('Localizando após troca de perfil…')
        self.selection_epoch+=1;self.automark_generation+=1
        if hasattr(self,'events'):
            retained=[]
            while True:
                try:action=self.events.get_nowait()
                except queue.Empty:break
                if action not in ('collect','undo'):retained.append(action)
            for action in retained:self.events.put(action)
        self.automark.reset();self.automark_snapshot=None
        self.display_motion.reset();self.displayed_observation=None
        self.counts_at=0
        self.sync_profile_controls();self.sync_pending_candidates();self.refresh_counts()
        self.profile_status.set(_tr('Ativo: ')+self.profile_store.name())
        self.session.notice=_tr('Perfil ativo: ')+self.profile_store.name()
        return True

    def create_profile(self):
        try:
            identifier=self.profile_store.create(self.new_profile_name.get())
        except Exception as exc:
            self.profile_status.set(_tr(str(exc)));showerror(_tr('Não foi possível criar o perfil'),_tr(str(exc)),parent=self.root);return
        self.new_profile_name.set('');self.sync_profile_controls()
        self.change_profile(identifier)

    def rename_profile(self):
        with foreground(self.root) as owner:
            name=simpledialog.askstring(_tr('Renomear perfil'),_tr('Nome do perfil ativo:'),
                                       initialvalue=self.profile_store.name(),parent=owner)
        if name is None:return
        try:self.profile_store.rename(self.profile_store.active,name)
        except Exception as exc:
            self.profile_status.set(_tr(str(exc)));showerror(_tr('Não foi possível renomear o perfil'),_tr(str(exc)),parent=self.root);return
        self.sync_profile_controls();self.profile_status.set(_tr('Perfil renomeado.'))


def build_profile_controls(app,parent,note):
    app.profile_var=tk.StringVar(value=app.profile_store.name())
    ttk.Label(parent,text=_tr('Perfil de progresso')).pack(anchor='w')
    row=ttk.Frame(parent);row.pack(fill='x',pady=4)
    app.profile_box=ttk.Combobox(row,textvariable=app.profile_var,state='readonly',width=16)
    app.profile_box.pack(side='left',fill='x',expand=True)
    ttk.Button(row,text=_tr('Usar perfil'),command=app.use_selected_profile).pack(side='right',padx=(6,0))
    ttk.Button(parent,text=_tr('Renomear perfil ativo…'),style='Quiet.TButton',command=app.rename_profile).pack(anchor='w',pady=(0,8))
    ttk.Label(parent,text=_tr('Novo perfil')).pack(anchor='w')
    app.new_profile_name=tk.StringVar()
    ttk.Entry(parent,textvariable=app.new_profile_name).pack(fill='x',pady=4)
    ttk.Button(parent,text=_tr('Criar e usar'),command=app.create_profile).pack(fill='x',pady=3)
    note(parent,_tr('Cada perfil tem suas coletas, importações e backups. Novos perfis começam sem coletas. Aparência, filtros e atalhos são compartilhados. A troca é manual; não acessamos sua conta do jogo.'))
    app.profile_status=tk.StringVar(value=_tr('Ativo: ')+app.profile_store.name())
    ttk.Label(parent,textvariable=app.profile_status,wraplength=280).pack(fill='x',pady=4)
    app.sync_profile_controls()
