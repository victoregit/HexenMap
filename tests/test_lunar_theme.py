"""Geometry and input checks run in isolated Tk processes, without game capture."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from src.live.theme import panel_size


@pytest.mark.parametrize('screen',['1366x768','1920x1080'])
@pytest.mark.parametrize('scale',[1.,1.25,1.5])
def test_lunar_layout_selection_and_cached_assets(screen,scale):
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'scripts/preview_lunar.py'),'--check','--scale',str(scale),'--screen',screen],
                          cwd=root,capture_output=True,text=True,timeout=30,check=True)
    data=json.loads(result.stdout)
    assert data['list_height']>=45 and data['theme_images']<=24


def test_panel_fits_negative_monitor_work_area_and_high_dpi():
    assert panel_size(1.,(-1920,0,0,1040))==(360,540)
    width,height=panel_size(1.5,(0,0,1366,728))
    assert width==540 and height<=728-72


def test_import_preview_requires_explicit_confirmation():
    code='''
import tkinter as tk
from tkinter import ttk
from src.live.theme import apply_theme,confirm_dialog,BG
root=tk.Tk();root.withdraw();apply_theme(root)
assert ttk.Style(root).lookup('Primary.TButton','background',('active',))==BG
def choose(label):
    def visit(widget):
        if isinstance(widget,ttk.Button) and widget.cget('text')==label:
            widget.invoke();return True
        return any(visit(child) for child in widget.winfo_children())
    assert visit(root)
for label,expected in [('Cancelar',False),('Mesclar coletas',True)]:
    root.after(100,lambda label=label:choose(label))
    assert confirm_dialog('Importar progresso','Prévia de teste',parent=root) is expected
root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                   capture_output=True,text=True,timeout=15,check=True)
