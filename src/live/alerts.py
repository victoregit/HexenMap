"""Modal foreground alerts: errors must not disappear behind the game."""
from contextlib import contextmanager
import tkinter as tk
from tkinter import messagebox, filedialog


@contextmanager
def foreground(parent=None):
    owned=parent is None
    owner=tk.Tk() if owned else parent.winfo_toplevel()
    hidden=owner.state()=='withdrawn'
    topmost=owner.attributes('-topmost')
    alpha=owner.attributes('-alpha')
    try:
        if owned or hidden:
            owner.attributes('-alpha',0)
            if owned:owner.geometry('1x1+0+0')
            owner.deiconify()
        owner.attributes('-topmost',True)
        owner.lift();owner.update_idletasks();owner.focus_force()
        yield owner
    finally:
        if owner.winfo_exists():
            if owned:owner.destroy()
            else:
                if hidden:owner.withdraw()
                owner.attributes('-alpha',alpha)
                owner.attributes('-topmost',topmost)


def showerror(title,message,*,parent=None):
    with foreground(parent) as owner:
        return messagebox.showerror(title,message,parent=owner)


def showinfo(title,message,*,parent=None):
    with foreground(parent) as owner:
        return messagebox.showinfo(title,message,parent=owner)


def askyesnocancel(title,message,*,parent=None):
    with foreground(parent) as owner:
        return messagebox.askyesnocancel(title,message,parent=owner)


def select_progress(parent):
    with foreground(parent) as owner:
        return filedialog.askopenfilename(parent=owner,
            title='Selecione seu progress.json antigo ou um backup — Cancelar encerra o app',
            filetypes=[('Progresso e backups','*.json *.bak'),('Todos','*.*')])
