"""Elevated splash launcher: one UAC prompt before checking for updates."""
import os
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk

if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from src.live.i18n import tr as _tr
from src.live.identity import VERSION
from src.live.storage import bundle_dir
from src.live.updates import discover, download, overlay_running


def home_directory():
    return Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]


def current_username():
    import ctypes
    from ctypes import wintypes
    api=ctypes.WinDLL('advapi32',use_last_error=True)
    api.GetUserNameW.argtypes=[wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    api.GetUserNameW.restype=wintypes.BOOL
    buffer=ctypes.create_unicode_buffer(1024)
    size=wintypes.DWORD(len(buffer))
    if not api.GetUserNameW(buffer,ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def installation_user_matches(home,username=None):
    marker=home/'installed-user.txt'
    if not marker.exists():
        return True  # Older portable installations predate the ownership marker.
    try:
        owner=marker.read_text(encoding='mbcs').strip()
        return bool(owner) and owner.casefold()==(username or current_username()).casefold()
    except OSError:
        return False


class Launcher:
    def __init__(self):
        self.home = home_directory()
        self.events = queue.Queue()
        self.busy = False
        self.root = tk.Tk()
        self.root.title(_tr('Hexen Map'))
        assets=bundle_dir()/'data/assets/brand'
        self.root.iconbitmap(str(assets/'app.ico'))
        # A regular window remains reachable through the taskbar and Alt+Tab.
        self.root.overrideredirect(False)
        self.root.resizable(False,False)
        self.root.configure(bg='#142132')
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.bind('<Escape>',lambda event:self.close())
        frame = tk.Frame(self.root,bg='#142132',padx=28,pady=24)
        frame.pack()
        animation=json.loads((assets/'animations.json').read_text(encoding='utf-8'))
        self.frame_ms=animation['frame_ms']
        self.loading_durations=animation.get('loading_durations_ms',[self.frame_ms]*animation['loading_frames'])
        self.loading_frames=[tk.PhotoImage(master=self.root,file=str(assets/'loading'/f'{i:02}.png'))
                             for i in range(animation['loading_frames'])]
        self.spinner=tk.Label(frame,image=self.loading_frames[0],bg='#142132',borderwidth=0)
        self.spinner.pack(pady=(0,18))
        self.animation_index=0
        tk.Label(frame,text=_tr('HEXEN MAP'),bg='#142132',fg='#dfc48d',font=('Segoe UI',20,'bold')).pack()
        self.status = tk.StringVar(value=_tr('Verificando atualizações…'))
        tk.Label(frame,textvariable=self.status,bg='#142132',fg='#a0adbd',wraplength=280,
                 justify='center',height=2,width=34,font=('Segoe UI',10)).pack(pady=(12,0))
        self.root.update_idletasks()
        width,height=self.root.winfo_reqwidth(),self.root.winfo_reqheight()
        x=(self.root.winfo_screenwidth()-width)//2
        y=(self.root.winfo_screenheight()-height)//2
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.deiconify();self.root.lift();self.root.focus_force()
        self.animate()
        self.root.after(100,self.startup)
        self.root.after(80,self.poll)

    def close(self):
        # Downloads finish only in the worker; closing never starts an installer.
        self.root.destroy()

    def animate(self):
        index=self.animation_index
        self.spinner.configure(image=self.loading_frames[self.animation_index])
        self.animation_index=(self.animation_index+1)%len(self.loading_frames)
        self.root.after(self.loading_durations[index],self.animate)

    def log_error(self,error):
        try:
            (self.home/'launcher-update.log').write_text(str(error),encoding='utf-8')
        except OSError:
            pass

    def startup(self):
        if (self.home/'updates-paused').exists():
            self.open_app()
        else:
            self.check()

    def check(self):
        if self.busy:
            return
        if overlay_running():
            self.root.destroy()
            return
        if not installation_user_matches(self.home):
            # Alternate admin credentials must not move per-user registration to
            # that account. The overlay still uses the original installation's data.
            self.open_app()
            return
        self.busy = True
        self.status.set(_tr('Verificando atualizações no GitHub…'))
        threading.Thread(target=self.worker,name='ReleaseCheck',daemon=True).start()

    def worker(self):
        try:
            release = discover(VERSION)
            if release is None:
                self.events.put(('current',None))
                return
            self.events.put(('status',_tr('Baixando atualização {0}…',release.version)))
            path = download(release,self.home/'updates',lambda value:self.events.put(('progress',value)))
            self.events.put(('install',path))
        except Exception as exc:
            self.events.put(('error',str(exc)))

    def poll(self):
        try:
            while True:
                kind,value = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set(_tr('Atualizando… {0}%', int(value*100)))
                elif kind == 'status':
                    self.status.set(_tr(value))
                elif kind == 'current':
                    self.busy = False
                    self.status.set(_tr('Você está na versão mais recente disponível.'))
                    self.open_app()
                    return
                elif kind == 'error':
                    self.busy = False
                    self.log_error(value)
                    self.open_app()
                    return
                elif kind == 'install':
                    if overlay_running():
                        self.busy = False
                        self.root.destroy()
                        return
                    args = subprocess.list2cmdline(['/VERYSILENT','/NORESTART','/SUPPRESSMSGBOXES',
                                                    '/UPDATE=1',f'/DIR={self.home}'])
                    try:
                        os.startfile(str(value),arguments=args,cwd=str(self.home))
                    except OSError as exc:
                        self.busy = False
                        self.log_error(exc)
                        self.open_app()
                        return
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(80,self.poll)

    def open_app(self):
        path = self.home/'HexenMap.exe'
        try:
            # The app outlives this launcher and must unpack as a fresh instance.
            subprocess.Popen([str(path)],cwd=str(self.home),
                             env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
        except OSError as exc:
            self.log_error(exc)
            self.status.set(_tr('Não foi possível abrir o Hexen Map. Reinstale o aplicativo.'))
            self.root.after(4000,self.close)
            return
        self.root.destroy()


def main():
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,r'Local\HexenMap.Launcher')
    if not handle or ctypes.get_last_error()==183:
        if handle:
            kernel.CloseHandle(handle)
        return
    try:
        Launcher().root.mainloop()
    finally:
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    main()
