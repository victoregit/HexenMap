"""Windows integration check: real input hit target, no synthesized game input."""
from pathlib import Path
import ctypes as ct
from ctypes import wintypes as wt
import sys
import tkinter as tk

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.native import Windows
from src.overlay.window_tracker import GameWindowRect


def main():
    native=Windows()
    foreground=native.u.GetForegroundWindow()
    root=tk.Tk();root.withdraw()
    surface=tk.Toplevel(root);surface.withdraw();surface.overrideredirect(True)
    surface.configure(bg="black")
    canvas=tk.Canvas(surface,bg="black",highlightthickness=0)
    canvas.pack(fill="both",expand=True)
    surface.update_idletasks()
    hwnd=native.input_overlay(surface.winfo_id())
    try:
        native.input_region(hwnd,[(40,40,65,65)])
        native.interactive(hwnd,True)
        native.place(hwnd,GameWindowRect(40,60,200,200))
        root.update()
        hit=native.u.WindowFromPoint
        hit.argtypes=[wt.POINT];hit.restype=wt.HWND
        def top(x,y):
            target=hit(wt.POINT(x,y))
            return native.u.GetAncestor(target,2) or target
        assert top(90,110)==hwnd,"Clickable icon box did not receive mouse"
        assert top(150,170)!=hwnd,"Outside icon box blocked underlying app"
        native.interactive(hwnd,False)
        root.update()
        assert top(90,110)!=hwnd,"Disabled surface still captured mouse"
        assert native.u.GetForegroundWindow()==foreground,"Input surface stole focus"
        print("PASS: icon box captures; outside and disabled pass through; focus preserved")
    finally:
        native.hide(hwnd)
        root.destroy()


if __name__=="__main__":
    main()
