"""Save and dismiss callbacks must return to the game, not the settings panel."""
from types import SimpleNamespace
import time

import pytest

from src.live.catalog import Item
from src.live.catalog import CATEGORIES
from src.live.desktop import DesktopApp
from src.live.marker_menu import MarkerMenu
from src.live.native import Windows
from src.live.session import Session
from src.progress.progress_manager import ProgressManager


@pytest.fixture
def app(tmp_path):
    obj=DesktopApp.__new__(DesktopApp)
    obj.session=Session([Item("real:chest","Chest","luxurious-chest",200,100)],
                        ProgressManager(str(tmp_path/"progress.json")))
    obj.calls=[]
    obj.category_labels={key:SimpleNamespace(set=lambda value:None) for key in CATEGORIES}
    obj.progress_text=SimpleNamespace(set=lambda value:obj.calls.append(value))
    obj.progress_value=SimpleNamespace(set=lambda value:None)
    rect=SimpleNamespace(hwnd=1,x=0,y=0,width=600,height=400,is_minimized=False)
    obj.native=SimpleNamespace(game=lambda:rect,interactive=lambda *a:obj.calls.append("disable-input"),
                                hide=lambda *a:obj.calls.append("hide-input"),
                                restore_game_focus=lambda *a:obj.calls.append("focus-game"))
    obj.menu_open=True
    obj.menu_geometry=obj.rect_key(rect)
    obj.menu_deadline=time.monotonic()+30
    obj.marker_menu=SimpleNamespace(destroy=lambda:obj.calls.append("destroy-card"))
    obj.input_hwnd=2
    return obj


def test_mark_saves_before_card_closes_and_restores_game_focus(app):
    app.change_marker_state("real:chest",True)
    assert ProgressManager(app.session.progress.filepath).is_collected("real:chest")
    assert not app.menu_open and app.marker_menu is None
    assert app.calls[-1]=="focus-game"
    assert app.calls.count("destroy-card")==1
    assert "1/1 permanentes · 0 recursos indisponíveis" in app.calls
    assert app.session.active()==[]


def test_dismiss_outside_restores_focus_without_collecting(app):
    app.close_marker_menu()
    assert app.session.progress.collected_count==0
    assert app.calls[-1]=="focus-game"


def test_unmark_saves_and_returns_to_game(app):
    app.session.set_collected("real:chest",True)
    app.change_marker_state("real:chest",False)
    assert not ProgressManager(app.session.progress.filepath).is_collected("real:chest")
    assert app.calls[-1]=="focus-game"


def test_shutdown_does_not_activate_game(app):
    app.close_marker_menu(restore_focus=False)
    assert "focus-game" not in app.calls


def test_open_card_does_not_keep_old_map_coordinates_visible(app):
    import queue
    import threading
    app.stop_event=threading.Event();app.events=queue.Queue()
    app.overlay_hwnd=3
    app.root=SimpleNamespace(after=lambda *args:None)
    app.sync_panel_visibility=lambda rect:None
    app.poll_catalog=lambda:None
    app.canvas=SimpleNamespace(delete=lambda *args:app.calls.append('clear-pins'))
    app.visible_pins=[object()]
    app.native.foreground=lambda rect:True
    app.native.menu_foreground=lambda rect:True
    app.native.game().is_found=True
    app._tick()
    assert 'clear-pins' in app.calls
    assert app.visible_pins==[]
    assert app.menu_open


def test_category_change_closes_card_without_stealing_panel_focus(app):
    app.category_vars={'luxurious-chest':SimpleNamespace(get=lambda:False)}
    app.persist_settings=lambda:None
    app.select_categories()
    assert not app.menu_open and app.session.selected==set()
    assert 'focus-game' not in app.calls


def test_focus_restoration_never_steals_from_another_application():
    native=Windows.__new__(Windows)
    calls=[]
    native.u=SimpleNamespace(IsWindow=lambda h:True,SetForegroundWindow=lambda h:calls.append(h))
    native.menu_foreground=lambda r:False
    assert not native.restore_game_focus(SimpleNamespace(hwnd=1,is_minimized=False))
    assert calls==[]


def test_single_card_action_toggles_both_directions():
    card=MarkerMenu.__new__(MarkerMenu)
    card.items=[SimpleNamespace(id="real:chest")];card.index=0
    state={"collected":False}
    card.progress=SimpleNamespace(is_collected=lambda i:state["collected"])
    calls=[]
    def change(identifier,collected):
        calls.append((identifier,collected))
        state["collected"]=collected
    card.on_change=change
    card._activate()
    card._activate()
    assert calls==[("real:chest",True),("real:chest",False)]
