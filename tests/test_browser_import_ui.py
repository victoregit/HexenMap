"""Browser inbox must reach the existing confirmation flow, never apply silently."""
import json
from pathlib import Path
from types import SimpleNamespace
import threading
from src.live.desktop import DesktopApp
from src.live.browser_connector import queue_import


def test_inbox_claimed_once_and_archived_even_when_user_cancels(tmp_path):
    root=SimpleNamespace(deiconify=lambda:None,lift=lambda:None,after=lambda *a:None)
    seen=[]
    app=SimpleNamespace(user_dir=tmp_path/'userData',region_loading=False,package_id='appsample',root=root,stop_event=threading.Event())
    app.poll_browser_imports=lambda:None
    app.import_appsample_progress=lambda p:seen.append((p.suffix,json.loads(p.read_text())))
    p=queue_import(tmp_path,{'source':'appsample','version':1,'markerIds':['1']})
    DesktopApp.poll_browser_imports(app);DesktopApp.poll_browser_imports(app)
    assert len(seen)==1 and seen[0][0]=='.processing'
    assert (p.parent/'archive'/p.name).is_file()
    assert not (app.user_dir/'progress.json').exists()


def test_inbox_waits_for_catalog_without_discarding(tmp_path):
    app=SimpleNamespace(user_dir=tmp_path/'userData',region_loading=True,package_id='appsample',
        root=SimpleNamespace(after=lambda *a:None),stop_event=threading.Event(),poll_browser_imports=lambda:None)
    path=queue_import(tmp_path,{'source':'appsample','version':1,'markerIds':[]})
    DesktopApp.poll_browser_imports(app)
    assert path.exists()

import pytest

@pytest.mark.parametrize('confirm',[False,True])
def test_browser_file_requires_existing_preview_confirmation(tmp_path,monkeypatch,confirm):
    from src.live.catalog import Item
    from src.progress.progress_manager import ProgressManager
    import src.live.desktop as desktop
    manager=ProgressManager(str(tmp_path/'progress.json'));manager.mark_collected('existing');manager.save()
    before=Path(manager.filepath).read_bytes()
    path=tmp_path/'delivery.processing';path.write_text(json.dumps({'source':'appsample','version':1,'markerIds':['1']}))
    prompts=[]
    monkeypatch.setattr(desktop,'confirm_dialog',lambda title,text,**kw:prompts.append(text) or confirm)
    app=SimpleNamespace(region_loading=False,package_id='appsample',user_dir=tmp_path,root=object(),refresh_counts=lambda:None,
        session=SimpleNamespace(items=[Item('appsample:marker:1','Baú','common-chest',0,0,rule_id='permanent')],progress=manager,notice=''))
    DesktopApp.import_appsample_progress(app,path)
    assert len(prompts)==1 and '1 itens encontrados' in prompts[0]
    assert manager.is_collected('appsample:marker:1') is confirm
    if not confirm:assert Path(manager.filepath).read_bytes()==before
    else:assert any(p.read_bytes()==before for p in tmp_path.glob('*.bak'))
