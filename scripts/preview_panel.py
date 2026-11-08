"""Render the actual compact panel using isolated preferences and progress.

No capture, keyboard observer, recognizer or personal-save writes are started.
"""
from pathlib import Path
import sys
import tkinter as tk
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.desktop import DesktopApp
from src.live.regions import RegionalCatalog
from src.live.session import Session
from src.live.storage import DEFAULT_KEYS
from src.progress.progress_manager import ProgressManager


def preview(output=ROOT/'build/panel-preview.png'):
    app=DesktopApp.__new__(DesktopApp)
    app.settings={'categories':[], 'hotkeys':dict(DEFAULT_KEYS)}
    app.package_id='mondstadt'
    app.catalogs=RegionalCatalog(ROOT/'data/community')
    package=app.catalogs.load_package(app.package_id)
    app.category_metadata=package.categories
    from src.live.labels import register_presentation
    register_presentation(package.categories)
    items,region,space=package.items,package.region,package.coordinate_system
    app.region_loading=False
    app.session=Session(items,ProgressManager(str(ROOT/'build/preview-only/progress.json')))
    app.session.region_id=region
    app.session.rules=app.catalogs.rules
    app.session.territories=app.catalogs.territories
    app.session.selected={'common-chest','anemoculus','luxurious-chest'}
    app.native=SimpleNamespace(panel=lambda hwnd:None,
                              game=lambda:SimpleNamespace(is_found=False,is_minimized=False),restore_game_focus=lambda r:None)
    app.menu_open=False; app.marker_menu=None; app.input_hwnd=None
    app.persist_settings=lambda:None
    app.root=tk.Tk()
    app.root.title('Prévia isolada do painel')
    app.close=app.root.destroy
    app._panel();app.refresh_counts()
    app.status.set('Conectado · mapa M')
    app.root.update()
    # Render the real Tk widgets, not an independently drawn design mockup.
    app.root.after(250,lambda:None)
    import time
    time.sleep(.3)
    app.root.update()
    from PIL import ImageGrab
    output.parent.mkdir(parents=True,exist_ok=True)
    # Capture only this preview window, including when another app covers it.
    from src.live.native import Windows
    hwnd=Windows().u.GetAncestor(app.root.winfo_id(),2) or app.root.winfo_id()
    ImageGrab.grab(window=int(hwnd)).save(output)
    # Verify direct selection and keyboard navigation in the icon strip.
    app.region_box.changed=lambda:None
    assert len(app.region_box.images)==len(set(app.region_names.values()))
    app.region_box.move(1)
    expected=app.region_box.names[app.region_box.index]
    app.region_box.choose(app.region_box.index)
    assert app.region_var.get()==expected
    assert app.region_box.caption.cget('text')==expected+(' · '+app.region_box.detail if app.region_box.detail else '')
    print(f'Panel: {app.root.winfo_width()}x{app.root.winfo_height()}; preview: {output}')
    assert app.panel_detached and not app.root.overrideredirect()
    app.toggle_panel_mode()
    app.toggle_panel();app.root.update()
    assert app.root.winfo_width()==40
    app.toggle_panel();app.show_settings();app.root.update()
    assert app.tabs.select()==str(app.prefs)
    app.tabs.select(app.explore)
    app.category_query.set('baú');app.root.update()
    assert not hasattr(app,'area_box') and not hasattr(app,'layer_box')
    app.open_layers();app.root.update();app.close_layers()
    app.root.destroy()


if __name__=='__main__': preview()
