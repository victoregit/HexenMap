"""Windows notification-area controls; tray callbacks never call Tk directly."""
import logging
import queue

from PIL import Image

from src.live.identity import DISPLAY_NAME,VERSION
from src.live.storage import bundle_dir


class AppTray:
    def __init__(self,app):
        import pystray
        self.app=app;self.pending=queue.Queue();self.job=None;self.closed=False
        with Image.open(bundle_dir()/'data/assets/brand/app.ico') as source:
            image=source.convert('RGBA')
        self.icon=pystray.Icon('HexenMap',image,f'{DISPLAY_NAME} {VERSION}',
            pystray.Menu(
                pystray.MenuItem('Abrir painel',lambda icon,item:self.pending.put('open'),default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Encerrar Hexen Map',lambda icon,item:self.pending.put('exit'))))
        self.icon.run_detached()
        self.job=app.root.after(100,self.poll)

    def poll(self):
        self.job=None
        if self.closed:return
        while not self.pending.empty():
            action=self.pending.get_nowait()
            if action=='exit':
                self.app.close();return
            if action=='open':
                transition=getattr(self.app,'_panel_transition',None)
                if transition:transition.cancel();self.app._panel_transition=None
                if self.app.panel_collapsed:self.app.toggle_panel(animate=False)
                self.app.root.deiconify();self.app.root.lift();self.app.root.focus_force()
        self.job=self.app.root.after(100,self.poll)

    def close(self):
        if self.closed:return
        self.closed=True
        if self.job is not None:
            self.app.root.after_cancel(self.job);self.job=None
        try:
            self.icon.visible=False
            self.icon.stop()
        except Exception:logging.getLogger(__name__).exception('Falha ao remover ícone da bandeja')
