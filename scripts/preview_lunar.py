"""UI-only Lunar preview and geometry checks. Never captures the game or saves progress."""
from pathlib import Path
import argparse
import json
import sys
import time
import tkinter as tk
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.desktop import DesktopApp
from src.live.catalog import Item
from src.live.category_browser import CategoryModel
from src.live.storage import DEFAULT_KEYS

class PreviewApp(DesktopApp):
    def __init__(self,scale=1.,screen=(1366,768),visible=False):
        self.root=tk.Tk();self.root.withdraw();self.root.title('Hexen Map · Prévia Lunar (sem jogo)')
        self.root.maxsize(*screen)
        self.root.tk.call('tk','scaling',96/72*scale)
        noop=lambda *a,**k:None
        self.native=SimpleNamespace(dpi_scale=lambda *a:scale,desktop_bounds=lambda:(0,0,*screen),
            work_area=lambda *a:(0,0,screen[0],screen[1]-40),panel=noop,move_panel=noop,
            game=lambda:SimpleNamespace(is_found=False,is_minimized=False),restore_game_focus=noop,
            set_capture_visible=noop)
        if visible and sys.platform=='win32':
            from src.live.native import Windows
            chrome=Windows()
            self.native.panel=lambda child:chrome._caption_theme(chrome.u.GetAncestor(child,2) or child)
        self.settings={'hotkeys':dict(DEFAULT_KEYS),'categories':['common-chest','luxurious-chest'],'panel':{'detached':True},'performance_mode':'light'}
        self.chest_signals=SimpleNamespace(ready=True,reason='Referências visuais disponíveis.')
        self.catalogs=SimpleNamespace(appsample_available=True)
        self.session=SimpleNamespace(selected=set(self.settings['categories']),notice='',pending_ids=set(),undo=noop)
        self.automark=SimpleNamespace(reset=noop);self.automark_generation=0;self.region_loading=False
        self.persist_settings=noop;self.reload_reference=noop;self.confirm_candidate=noop
        self.install_browser_connector=lambda:self.notice.set('Prévia: não foi registrado nenhum conector.')
        self.import_appsample_progress=lambda:self.notice.set('Prévia: nenhum progresso foi importado.')
        self.close_marker_menu=noop
        self._panel()
        groups={'common-chest':('Baús comuns','Baús'),'exquisite-chest':('Baús sofisticados','Baús'),
                'precious-chest':('Baús preciosos','Baús'),'luxurious-chest':('Baús luxuosos','Baús'),
                'remarkable-chest':('Baús extraordinários','Baús')}
        for category in ('anemoculus','geoculus','electroculus','dendroculus','hydroculus','pyroculus','cryoculus','lunoculus'):
            groups[category]=(category,'Oculi')
        self.sample_items=[Item(str(i),name,category,0,0) for i,(category,(name,group)) in enumerate(groups.items())]
        metadata={k:{'name':name,'source_name':name,'group':group,'presentation_reviewed':True} for k,(name,group) in groups.items()}
        self.category_browser.set_model(CategoryModel(self.sample_items,metadata),self.session.selected)
        self.category_browser.counts={entry.key:(2,10) for entry in self.category_browser.model.entries}
        self.progress_text.set('Coletados: 12 de 60 · dados ilustrativos')
        self.status.set('Prévia visual · sem jogo conectado')
        self.root.update_idletasks()
        if visible:self.root.deiconify()
    def populate_region_controls(self):
        self.layer_names=['Teyvat / Superfície','Teyvat / Automática'];self.layer_var.set(self.layer_names[0]);self.territory_path.set('Teyvat · Superfície')
    def choose_categories(self,members,selected):
        if selected:self.session.selected.update(members)
        else:self.session.selected.difference_update(members)
        self.category_browser.selected=set(self.session.selected);self.category_browser.schedule_paint()
    def toggle_visibility(self):
        self.visibility_button.configure(text='Mostrar ícones' if self.visibility_button.cget('text')=='Ocultar ícones' else 'Ocultar ícones')
    def panel_undo(self):self.notice.set('Prévia: nenhuma coleta para desfazer.')
    def refresh_counts(self):pass
    def close(self):self.root.destroy()


def check(scale,screen):
    app=PreviewApp(scale,screen)
    root=app.root
    root.attributes('-alpha',0);root.deiconify()
    root.update();root.update_idletasks()
    width,height=app.panel_normal_size
    assert root.winfo_width()==width,(root.winfo_width(),width)
    assert root.winfo_height()==height,(root.winfo_height(),height)
    for button in (app.items_tab,app.settings_tab,app.visibility_button):
        assert button.winfo_width()>20,(button,button.winfo_width())
        assert button.winfo_rooty()+button.winfo_height()<=root.winfo_rooty()+height
    assert app.category_browser.winfo_height()>=45
    app.show_settings();root.update_idletasks()
    assert len(app.settings_sections)==6 and all(not s['open'] for s in app.settings_sections)
    for section in app.settings_sections:
        section['button'].invoke();root.update_idletasks()
        assert sum(s['open'] for s in app.settings_sections)==1
    app.tabs.select(app.explore);app.category_browser.collapsed.discard('Baús');app.category_browser.rebuild()
    root.update_idletasks();app.category_browser.paint()
    assert sum(r[0]=='tiles' for r in app.category_browser.rows)==2
    browser=app.category_browser
    tile=next(i for i,row in enumerate(browser.rows) if row[0]=='tiles')
    browser.activate(tile,browser.winfo_width()*.375)
    assert 'exquisite-chest' in app.session.selected
    browser.activate(tile,browser.winfo_width()*.375)
    assert 'exquisite-chest' not in app.session.selected
    browser.focused=tile+2;browser.tile_column=0;browser.activate_focused()
    assert 'remarkable-chest' in app.session.selected
    images=tuple(map(str,root._lunar_images));app.category_browser.paint()
    assert tuple(map(str,root._lunar_images))==images
    from src.live.theme import apply_theme,Tooltip
    apply_theme(root,scale);assert tuple(map(str,root._lunar_images))==images
    tip=Tooltip(app.items_tab,'Itens selecionados');before=root.focus_get();tip.show()
    assert tip.label is not None and root.focus_get()==before
    tip.hide();assert tip.label is None
    print(json.dumps({'scale':scale,'screen':screen,'panel':[width,height],'list_height':app.category_browser.winfo_height(),'theme_images':len(images)}))
    app.compact.stop();root.update_idletasks();root.destroy()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--scale',type=float,default=1.)
    parser.add_argument('--screen',default='1366x768');args=parser.parse_args();screen=tuple(map(int,args.screen.split('x')))
    if args.check:check(args.scale,screen)
    else:
        app=PreviewApp(args.scale,screen,visible=True)
        app.category_browser.collapsed.discard('Baús');app.category_browser.rebuild()
        app.root.mainloop()
