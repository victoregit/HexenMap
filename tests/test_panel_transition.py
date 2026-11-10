from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from PIL import Image

from src.live.native import Windows
from src.live.panel import CompactPanel
from src.live.panel_transition import HANDOFF_MS,handoff_frame,transition_frame


def test_transition_starts_with_panel_and_ends_on_exact_badge_handoff():
    source=Image.new('RGBA',(360,540),'#25304a')
    poster=handoff_frame()
    source_bytes=source.tobytes();poster_bytes=poster.tobytes()
    size=(384,564);origin=(12,12);target=(50,50)
    start=transition_frame(source,poster,0,size,origin,target,76)
    assert start.crop((12,12,372,552)).tobytes()==source_bytes
    expected=Image.new('RGBA',size)
    expected.alpha_composite(poster.resize((76,76),Image.Resampling.LANCZOS),(12,12))
    end=transition_frame(source,poster,1,size,origin,target,76)
    assert end.tobytes()==expected.tobytes()
    assert source.tobytes()==source_bytes and poster.tobytes()==poster_bytes
    assert HANDOFF_MS==3000


def test_live_panel_mask_transfers_region_ownership_and_clears_it():
    calls=[]
    native=Windows.__new__(Windows)
    native.u=SimpleNamespace(GetAncestor=lambda child,level:99,
        SetWindowRgn=lambda *args:calls.append(('apply',args)) or True)
    native.g=SimpleNamespace(CreateRectRgn=lambda *args:calls.append(('create',args)) or 42,
        DeleteObject=lambda handle:calls.append(('delete',handle)))
    native.panel_mask(10,(2.2,40.7,358.1,499.2))
    native.panel_mask(10,None)
    assert ('create',(2,41,358,499)) in calls
    assert ('apply',(99,42,True)) in calls
    assert ('apply',(99,None,True)) in calls
    assert not any(call[0]=='delete' for call in calls)


def test_play_and_f8_defer_game_focus_to_transition_completion():
    panel=CompactPanel();panel.panel_collapsed=False;panel.panel_detached=True
    calls=[]
    panel.native=SimpleNamespace(game=lambda:None,restore_game_focus=lambda game:calls.append('focus'))
    panel.toggle_panel=lambda **kwargs:calls.append(kwargs)
    panel.collapse_to_game()
    panel.panel_shortcut()
    assert calls==[{'return_to_game':True},{'return_to_game':True}]


def test_saved_collapsed_state_does_not_start_a_transition():
    panel=CompactPanel();panel.panel_detached=False;panel.panel_collapsed=False
    calls=[]
    panel._animate_panel_collapse=lambda *args:(_ for _ in ()).throw(AssertionError('startup animated'))
    panel._apply_panel_state=lambda collapsed,save:calls.append((collapsed,save))
    panel.toggle_panel(save=False)
    assert calls==[(True,False)]


def test_real_tk_win32_collapse_handoff_expand_and_repeat():
    if sys.platform!='win32':
        import pytest
        pytest.skip('Real Win32 window regions')
    code='''
import time
from scripts.preview_lunar import PreviewApp
from src.live.native import Windows
app=PreviewApp(1.,(1366,768),visible=True);root=app.root;root.update()
windows=Windows()
app.native.panel=windows.panel;app.native.panel_mask=windows.panel_mask
app.native.transition_panel=windows.transition_panel
app.native.control_bounds=windows.control_bounds;app.native.move_panel=windows.move_panel
focus=[];app.native.restore_game_focus=lambda game:focus.append(True)
from src.live.panel_transition import PanelCollapseTransition
for x,y in [(0,0),(0,200),(800,0),(-500,80)]:
 windows.move_panel(root.winfo_id(),x,y);root.update()
 bounds=windows.control_bounds(root.winfo_id())
 transition=PanelCollapseTransition(root,app.native,bounds,bounds[:2],app.compact_size,lambda:None)
 transition.start();root.update()
 actual=windows.control_bounds(transition.window.winfo_id())
 assert actual[:2]==(bounds[0]-12,bounds[1]-12),(bounds,actual)
 transition.cancel();root.update()
windows.move_panel(root.winfo_id(),80,80);root.update()
size=app.panel_normal_size
for action,location in [(app.collapse_to_game,(0,0)),(app.panel_shortcut,(0,180)),
                        (app.collapse_to_game,(800,0)),(app.panel_shortcut,(800,160))]:
 windows.move_panel(root.winfo_id(),*location);root.update()
 position=windows.control_bounds(root.winfo_id())[:2]
 before=len(focus);action();transition=app._panel_transition
 assert transition is not None and len(focus)==before
 assert windows.get_style(windows.u.GetAncestor(transition.window.winfo_id(),2),-20)&0x8000000
 deadline=time.monotonic()+2
 while app._panel_transition is not None and time.monotonic()<deadline:
  root.update();time.sleep(.008)
 root.update()
 assert app._panel_transition is None and app.panel_collapsed
 assert len(focus)==before+1
 assert (root.winfo_width(),root.winfo_height())==(app.compact_size,app.compact_size)
 assert windows.control_bounds(root.winfo_id())[:2]==position
 assert 3000<=(time.monotonic()-app.compact.epoch)*1000<3700
 app.toggle_panel(save=False);root.update()
 assert not app.panel_collapsed and app.panel_normal_size==size
app.collapse_to_game();transition=app._panel_transition;before=len(focus)
transition.finish();transition.finish();root.update()
assert app.panel_collapsed and len(focus)==before+1
app.compact.stop();root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=True,timeout=30)
