from unittest.mock import Mock,patch
import threading

import pytest

from src.live import alerts
from src.live.personal_state import AmbiguousProfilesRequired,OpeningCancelled,prepare_state_interactive
from src.live.desktop import DesktopApp


def test_error_is_modal_with_foreground_owner_and_restores_window():
    owner=Mock();owner.winfo_toplevel.return_value=owner
    owner.state.return_value='normal'
    owner.attributes.side_effect=lambda name,*args: 0 if name=='-topmost' else 1
    def show(*args,**kwargs):
        assert kwargs['parent'] is owner
        owner.attributes.assert_any_call('-topmost',True)
        owner.focus_force.assert_called_once()
    with patch.object(alerts.messagebox,'showerror',side_effect=show):
        alerts.showerror('Erro','Mensagem',parent=owner)
    owner.attributes.assert_any_call('-topmost',0)
    owner.destroy.assert_not_called()


def test_cancel_conflicting_save_picker_exits_without_creating_save():
    root=Mock()
    with patch('tkinter.Tk',return_value=root), \
         patch('src.live.personal_state.prepare_state',side_effect=AmbiguousProfilesRequired()) as prepare, \
         patch.object(alerts,'showinfo'), \
         patch.object(alerts,'select_progress',return_value=''):
        with pytest.raises(OpeningCancelled):prepare_state_interactive()
    prepare.assert_called_once()
    root.destroy.assert_called_once()


def test_fatal_error_stops_work_and_closes_only_after_acknowledgement():
    app=DesktopApp.__new__(DesktopApp)
    app.root=Mock();app.native=Mock();app.stop_event=threading.Event()
    app.input_hwnd=10;app.overlay_hwnd=20;app.close=Mock()
    def acknowledge(*args,**kwargs):
        assert app.stop_event.is_set()
        app.close.assert_not_called()
        app.native.hide.assert_any_call(10)
        app.native.hide.assert_any_call(20)
    with patch('src.live.desktop.messagebox.showerror',side_effect=acknowledge) as dialog:
        app.fatal_error(RuntimeError('Falha fatal'))
        app.fatal_error(RuntimeError('Não repetir'))
    dialog.assert_called_once();app.close.assert_called_once()
