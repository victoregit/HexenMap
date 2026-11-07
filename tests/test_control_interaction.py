"""Regression for Ctrl-only observation and clicks received by our own window."""
from types import SimpleNamespace
import time

from src.overlay.control_key import ControlKeyListener
from src.live.desktop import DesktopApp


def test_both_control_keys_and_auto_repeat():
    listener=ControlKeyListener()
    listener.transition(0xa2,True)
    listener.transition(0xa2,True)
    assert listener.is_down
    listener.transition(0xa3,True)
    listener.transition(0xa2,False)
    assert listener.is_down
    listener.transition(0xa3,False)
    assert not listener.is_down


def test_observer_ignores_every_other_key_and_resets():
    listener=ControlKeyListener()
    listener.transition(65,True)
    assert not listener.is_down
    listener.transition(0xa2,True)
    listener.stop()
    assert not listener.is_down


def test_marker_menu_accepts_own_window_focus_and_control_event(monkeypatch):
    """A click can focus our input surface before its handler runs."""
    cards=[]
    class Card:
        def __init__(self,*args): self.args=args;cards.append(self)
    monkeypatch.setattr("src.live.desktop.MarkerMenu",Card)
    item=SimpleNamespace(id="real:chest",category="luxurious-chest")
    rect=SimpleNamespace(hwnd=1,x=0,y=0,width=600,height=400)
    app=DesktopApp.__new__(DesktopApp)
    app.native=SimpleNamespace(game=lambda:rect,pointer=lambda:(False,0,0),
                               foreground=lambda r:False,menu_foreground=lambda r:True,
                               interactive=lambda *args:None,hide=lambda *args:None)
    app.control_listener=ControlKeyListener()
    app.control_listener.transition(0xa2,True)
    app.menu_open=False
    app.visible_pins=[SimpleNamespace(item=item,x=100,y=100)]
    app.geometry_key=app.rect_key(rect)
    app.displayed_at=time.monotonic()
    app.displayed_observation=SimpleNamespace(fresh=lambda now:True)
    app.session=SimpleNamespace(hit_test=lambda *a:[item],progress=SimpleNamespace(is_collected=lambda i:False))
    app.root=object();app.input_hwnd=2
    result=app.open_marker_menu(SimpleNamespace(x=100,y=100,x_root=100,y_root=100))
    assert result=="break" and app.menu_open and len(cards)==1
    assert cards[0].args[3]==[item]
