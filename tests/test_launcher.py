import queue
from types import SimpleNamespace
from pathlib import Path

from src import launcher


class Widget:
    def __init__(self):self.options={}
    def configure(self,**kwargs):self.options.update(kwargs)
    def __setitem__(self,key,value):self.options[key]=value


def app(tmp_path):
    obj=launcher.Launcher.__new__(launcher.Launcher)
    obj.home=tmp_path;obj.events=queue.Queue();obj.busy=True
    obj.status=SimpleNamespace(set=lambda value:setattr(obj,'message',value))
    obj.progress=Widget();obj.retry_button=Widget()
    obj.closed=False;obj.scheduled=[]
    obj.root=SimpleNamespace(destroy=lambda:setattr(obj,'closed',True),after=lambda *args:obj.scheduled.append(args))
    return obj


def test_no_release_opens_installed_app(tmp_path,monkeypatch):
    obj=app(tmp_path);opened=[]
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append((args[0],kwargs)))
    obj.events.put(('current',None));obj.poll()
    assert opened[0][0]==str(tmp_path/'HexenMap.exe') and obj.closed
    assert opened[0][1]['env']['PYINSTALLER_RESET_ENVIRONMENT']=='1'


def test_app_gets_independent_bootloader_environment_without_mutating_launcher(tmp_path,monkeypatch):
    obj=app(tmp_path);opened=[]
    monkeypatch.setenv('_PYI_APPLICATION_HOME_DIR','old-extraction')
    monkeypatch.setenv('PYINSTALLER_RESET_ENVIRONMENT','0')
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append(kwargs))
    obj.open_app()
    assert opened[0]['env']['PYINSTALLER_RESET_ENVIRONMENT']=='1'
    assert launcher.os.environ['PYINSTALLER_RESET_ENVIRONMENT']=='0'


def test_installer_resets_inherited_bootloader_before_restarting_launcher():
    script=(Path(__file__).resolve().parents[1]/'installer/HexenMap.iss').read_text(encoding='utf-8')
    post=script.split('if CurStep = ssPostInstall then begin',1)[1]
    assert "SetChildEnvironment('PYINSTALLER_RESET_ENVIRONMENT', '1')" in post


def test_offline_opens_installed_app_without_clicks(tmp_path,monkeypatch):
    opened=[]
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append(args[0]))
    obj=app(tmp_path);obj.events.put(('error','offline'));obj.poll()
    assert obj.closed and not obj.busy and opened==[str(tmp_path/'HexenMap.exe')]


def test_verified_update_runs_installer_then_releases_launcher(tmp_path,monkeypatch):
    obj=app(tmp_path);opened=[]
    monkeypatch.setattr(launcher,'overlay_running',lambda:False)
    monkeypatch.setattr(launcher.os,'startfile',lambda path,**kwargs:opened.append((path,kwargs)))
    obj.events.put(('install',tmp_path/'updates/setup.exe'));obj.poll()
    assert obj.closed and len(opened)==1
    assert '/UPDATE=1' in opened[0][1]['arguments']
    assert '/VERYSILENT' in opened[0][1]['arguments']
    assert '/DIR=' in opened[0][1]['arguments']


def test_overlay_starting_during_download_blocks_installer(tmp_path,monkeypatch):
    obj=app(tmp_path)
    monkeypatch.setattr(launcher,'overlay_running',lambda:True)
    monkeypatch.setattr(launcher.os,'startfile',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('must not launch')))
    obj.events.put(('install',tmp_path/'setup.exe'));obj.poll()
    assert obj.closed and not obj.busy


def test_rollback_opens_previous_version_without_update_or_click(tmp_path,monkeypatch):
    opened=[]
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append(args[0]))
    obj=app(tmp_path);(tmp_path/'updates-paused').touch()
    obj.check=lambda: (_ for _ in ()).throw(AssertionError('must remain paused'))
    obj.startup()
    assert opened==[str(tmp_path/'HexenMap.exe')] and obj.closed


def test_installer_start_failure_falls_back_without_clicks(tmp_path,monkeypatch):
    obj=app(tmp_path);opened=[]
    monkeypatch.setattr(launcher,'overlay_running',lambda:False)
    def launch(path,**kwargs):
        if path.endswith('setup.exe'):raise OSError('installer unavailable')
        opened.append(path)
    monkeypatch.setattr(launcher.os,'startfile',launch)
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append(args[0]))
    obj.events.put(('install',tmp_path/'setup.exe'));obj.poll()
    assert obj.closed and opened==[str(tmp_path/'HexenMap.exe')]


def test_splash_is_animated_and_has_no_buttons(tmp_path,monkeypatch):
    from tkinter import ttk
    monkeypatch.setattr(launcher,'home_directory',lambda:tmp_path)
    obj=launcher.Launcher()
    try:
        obj.root.withdraw()
        def widgets(widget):
            for child in widget.winfo_children():
                yield child
                yield from widgets(child)
        assert not any(isinstance(widget,(launcher.tk.Button,ttk.Button)) for widget in widgets(obj.root))
        assert obj.root.overrideredirect()
        assert len(obj.loading_frames)==48
        old=obj.animation_index
        obj.animate()
        assert obj.animation_index==(old+1)%48
        assert obj.spinner.cget('image')==str(obj.loading_frames[old])
    finally:
        obj.root.destroy()


def test_other_admin_account_does_not_reassign_user_installation(tmp_path,monkeypatch):
    (tmp_path/'installed-user.txt').write_text('original-user',encoding='mbcs')
    assert launcher.installation_user_matches(tmp_path,'original-user')
    assert not launcher.installation_user_matches(tmp_path,'other-admin')
    obj=app(tmp_path);obj.busy=False;opened=[]
    monkeypatch.setattr(launcher,'current_username',lambda:'other-admin')
    monkeypatch.setattr(launcher,'overlay_running',lambda:False)
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda args,**kwargs:opened.append((args,kwargs)))
    obj.check()
    assert obj.closed and opened[0][0]==[str(tmp_path/'HexenMap.exe')]
    assert opened[0][1]['cwd']==str(tmp_path)
    assert obj.events.empty()


def test_uac_requested_before_launcher_code_starts():
    root=Path(__file__).resolve().parents[1]
    assert 'uac_admin=True' in (root/'HexenMapLauncher.spec').read_text()
    script=(root/'installer/HexenMap.iss').read_text(encoding='utf-8')
    update_entry=next(line for line in script.splitlines() if 'Check: IsUpdate' in line)
    assert 'runascurrentuser' in update_entry
