from pathlib import Path
import subprocess,sys


def test_photo_viewport_zoom_drag_resize_and_close_are_bounded():
    code='''
import tkinter as tk
from types import SimpleNamespace
from PIL import Image
from src.live.theme import apply_theme
from src.live.photo_viewer import PhotoViewer
root=tk.Tk();root.withdraw();apply_theme(root);closed=[]
viewer=PhotoViewer(root,Image.new('RGB',(960,640),'blue'),lambda:closed.append(True))
viewer.window.attributes('-alpha',0);root.update();viewer.draw()
before=viewer.scale()
for _ in range(20):viewer.wheel(SimpleNamespace(delta=120,x=200,y=150))
viewer.draw();assert viewer.scale()>before and viewer.zoom<=8
assert viewer.photo.width()<=viewer.canvas.winfo_width()+20
assert viewer.photo.height()<=viewer.canvas.winfo_height()+20
viewer.start_drag(SimpleNamespace(x=100,y=100));viewer.drag(SimpleNamespace(x=180,y=140));viewer.draw()
viewer.fit();viewer.draw();assert viewer.zoom==1
viewer.close();assert closed==[True];root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=True,timeout=20)


def test_escape_closes_only_photo_until_key_is_released():
    from src.live.marker_menu import MarkerMenu
    from types import SimpleNamespace
    card=MarkerMenu.__new__(MarkerMenu);card.escape_consumed=False;closed=[]
    def close():closed.append(True);card.viewer=None
    card.viewer=SimpleNamespace(close=close)
    assert not card.escape_key(True) and closed==[True]
    assert not card.escape_key(True)
    assert not card.escape_key(False)
    assert card.escape_key(True)
