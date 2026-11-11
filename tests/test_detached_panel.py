from types import SimpleNamespace

from src.live.panel import CompactPanel
from src.live.native import Windows
from src.live.storage import read_settings,write_json,DEFAULT_KEYS


def test_control_bounds_use_windows_physical_frame_including_titlebar():
    panel=CompactPanel()
    panel.panel_detached=True;panel.panel_collapsed=False
    panel.root=SimpleNamespace(winfo_id=lambda:1)
    panel.layer_popup=SimpleNamespace(winfo_id=lambda:2)
    calls=[]
    def bounds(hwnd,occluder=None):
        calls.append((hwnd,occluder))
        return (400,220,760,800) if hwnd==1 else (500,300,840,600)
    panel.native=SimpleNamespace(control_bounds=bounds)
    result=panel.control_rectangles(SimpleNamespace(x=300,y=200,hwnd=10))
    assert result==[(98,18,462,602),(198,98,542,402)]
    assert calls==[(1,10),(2,None)]


def test_detached_panel_does_not_follow_game_focus_or_hide_on_alt_tab():
    panel=CompactPanel();panel.panel_detached=True;panel.panel_collapsed=False;panel.panel_suspended=False
    panel.sync_panel_visibility(SimpleNamespace())  # No game-focus queries needed.
    assert panel.panel_suspended is False


def test_drag_can_leave_game_and_use_negative_monitor_coordinates():
    panel=CompactPanel();panel.panel_detached=True;panel.panel_collapsed=False
    panel.panel_drag=(500,200,300,100);panel.panel_dragged=False
    panel.native=SimpleNamespace(game=lambda:SimpleNamespace(is_found=True,is_minimized=False,
        x=0,y=0,width=1366,height=768))
    panel.panel_desktop_bounds=lambda:(-1920,0,1366,1080)
    positions=[];panel.move_panel_to=lambda x,y:positions.append((x,y))
    panel.drag_panel(SimpleNamespace(x_root=-500,y_root=300))
    assert positions==[(-700,200)] and panel.panel_dragged


def test_detached_preference_and_negative_position_survive_restart(tmp_path):
    path=tmp_path/'settings.json'
    write_json(path,{'categories':[],'hotkeys':dict(DEFAULT_KEYS),
                    'panel':{'detached':True,'collapsed':False,'x':-800,'y':100}})
    assert read_settings(path)['panel']=={'detached':True,'collapsed':False,'x':-800,'y':100}


def test_clip_region_subtracts_controls_without_deleting_windows_owned_handle():
    native=Windows.__new__(Windows);calls=[];handles=iter([1,2])
    native.g=SimpleNamespace(CreateRectRgn=lambda *a:next(handles),
        CombineRgn=lambda *a:calls.append(('subtract',a)) or 1,
        DeleteObject=lambda handle:calls.append(('delete',handle)))
    native.u=SimpleNamespace(SetWindowRgn=lambda *a:calls.append(('apply',a)) or True)
    native.exclude_controls(99,1366,768,[(100,100,460,680)])
    assert ('subtract',(1,1,2,4)) in calls
    assert ('delete',2) in calls and ('delete',1) not in calls
    assert ('apply',(99,1,True)) in calls


def test_collapsed_animated_button_hides_over_other_apps_and_returns_without_focus():
    panel=CompactPanel();panel.panel_detached=True;panel.panel_collapsed=True;panel.panel_suspended=False
    calls=[]
    panel.root=SimpleNamespace(winfo_id=lambda:10,withdraw=lambda:calls.append('hide'))
    panel.close_layers=lambda:calls.append('close')
    panel.last_panel_position=(10,10)
    panel.compact_position=lambda rect,follow=False:(10,10)
    panel.native=SimpleNamespace(menu_foreground=lambda rect:rect.foreground,show_panel=lambda hwnd:calls.append('show'))
    panel.sync_panel_visibility(SimpleNamespace(is_found=True,is_minimized=False,foreground=False))
    assert panel.panel_suspended and calls==['close','hide']
    panel.sync_panel_visibility(SimpleNamespace(is_found=True,is_minimized=False,foreground=True))
    assert not panel.panel_suspended and calls==['close','hide','show']


def test_collapsed_button_is_excluded_from_markers_without_game_occlusion():
    panel=CompactPanel();panel.panel_detached=True;panel.panel_collapsed=True;panel.layer_popup=None
    panel.root=SimpleNamespace(winfo_id=lambda:10)
    calls=[]
    def bounds(hwnd,occluder=None):calls.append(occluder);return (10,20,74,84)
    panel.native=SimpleNamespace(control_bounds=bounds)
    assert panel.control_rectangles(SimpleNamespace(hwnd=99,x=0,y=0))==[(8,18,76,86)]
    assert calls==[None]
