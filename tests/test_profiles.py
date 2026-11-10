import queue
from types import SimpleNamespace

import pytest

from src.live.personal_state import prepare_state,StateRecoveryRequired
from src.live.profile_controls import ProfileControls
from src.live.profiles import ProfileStore
from src.live.session import Session
from src.live.storage import write_json


def store_at(tmp_path):
    prepare_state(destination=tmp_path,legacy_roots=[],allow_new=True)
    return ProfileStore(tmp_path)


def test_original_save_stays_in_place_and_new_profile_is_empty(tmp_path):
    store=store_at(tmp_path);manager=store.open_progress()
    manager.mark_collected('original');manager.save()
    before=(tmp_path/'progress.json').read_bytes()
    store=ProfileStore(tmp_path)
    assert store.active=='default' and store.name()=='Principal'
    second=store.create('Conta 2')
    assert (tmp_path/'progress.json').read_bytes()==before
    assert not store.open_progress(second).get_collected_ids()
    store.activate(second)
    assert ProfileStore(tmp_path).active==second
    assert store.open_progress('default').is_collected('original')


def test_import_ledger_and_backups_are_independent(tmp_path):
    store=store_at(tmp_path);second=store.create('Alternativa')
    key='a'*64;records={'appsample:marker:1':{'collected_at':'2026-11-10','notes':'import'}}
    first=store.open_progress('default')
    assert first.merge_imported_records(records,key,'appsample')['added']==1
    other=store.open_progress(second)
    assert other.merge_imported_records(records,key,'appsample')['added']==1
    assert other.backup_filepath!=first.backup_filepath
    assert first.merge_imported_records(records,key,'appsample')['repeated']


@pytest.mark.parametrize('name',['','  ','x'*41,'bad\nname'])
def test_invalid_profile_names_do_not_create_saves(tmp_path,name):
    store=store_at(tmp_path)
    with pytest.raises(ValueError):store.create(name)
    assert len(store.profiles)==1 and not (tmp_path/'profiles').exists()


def test_duplicate_names_and_rename_preserve_identity(tmp_path):
    store=store_at(tmp_path);identifier=store.create('  Minha conta  ')
    with pytest.raises(ValueError):store.create('MINHA CONTA')
    with pytest.raises(ValueError):store.rename(identifier,'principal')
    store.rename(identifier,'Secundária');store.activate(identifier)
    restored=ProfileStore(tmp_path)
    assert restored.active==identifier and restored.name()=='Secundária'


def test_missing_save_and_corrupt_index_fail_closed(tmp_path):
    store=store_at(tmp_path);identifier=store.create('Conta 2')
    folder=store.directory(identifier)
    (folder/'progress.json').unlink();(folder/'progress.json.bak').unlink()
    with pytest.raises(StateRecoveryRequired):store.activate(identifier)
    assert store.active=='default' and not (folder/'progress.json').exists()
    (tmp_path/'profiles.json').write_text('{bad')
    with pytest.raises(StateRecoveryRequired):ProfileStore(tmp_path)
    assert (tmp_path/'profiles.json').read_text()=='{bad'


def test_index_path_injection_is_rejected(tmp_path):
    store=store_at(tmp_path)
    data=store.data;data['profiles'].append({'id':'../elsewhere','name':'Outside'})
    write_json(store.path,data)
    with pytest.raises(StateRecoveryRequired):ProfileStore(tmp_path)


def test_external_index_corruption_cannot_replace_good_backup(tmp_path):
    store=store_at(tmp_path);identifier=store.create('Conta 2')
    backup=store.path.with_suffix('.json.bak');before=backup.read_bytes()
    store.path.write_text('{invalid')
    with pytest.raises(StateRecoveryRequired):store.activate(identifier)
    assert backup.read_bytes()==before and store.active=='default'


def controller(store):
    obj=ProfileControls();obj.profile_store=store;obj.region_loading=False
    obj.session=Session([],store.open_progress());obj.selection_epoch=3;obj.automark_generation=5
    obj.automark=SimpleNamespace(reset=lambda:None);obj.display_motion=SimpleNamespace(reset=lambda:None)
    obj.profile_status=SimpleNamespace(set=lambda value:setattr(obj,'status',value))
    obj.sync_profile_controls=lambda:None;obj.sync_pending_candidates=lambda:None;obj.refresh_counts=lambda:None
    obj.close_layers=lambda:None;obj.close_marker_menu=lambda **kw:None;obj.events=queue.Queue()
    return obj


def test_switch_clears_old_actions_and_undo_and_saves_correct_account(tmp_path):
    store=store_at(tmp_path);second=store.create('Conta 2');obj=controller(store)
    first=obj.session.progress;first.mark_collected('A')
    obj.session.undo_ids.append('A');obj.session.undo_records.append(('A',None))
    obj.session.pending_ids={'A'};obj.events.put('collect');obj.events.put('undo');obj.events.put('panel')
    assert obj.change_profile(second)
    assert not obj.session.progress.is_collected('A')
    assert not obj.session.undo_ids and not obj.session.undo_records and not obj.session.pending_ids
    assert obj.events.get_nowait()=='panel' and obj.events.empty()
    obj.session.progress.mark_collected('B');obj.session.progress.save()
    assert obj.change_profile('default')
    assert obj.session.progress.is_collected('A') and not obj.session.progress.is_collected('B')
    assert obj.selection_epoch==5 and ProfileStore(tmp_path).active=='default'


def test_failed_save_or_index_write_does_not_switch_profile(tmp_path,monkeypatch):
    store=store_at(tmp_path);second=store.create('Conta 2');obj=controller(store)
    obj.root=None
    alerts=[]
    monkeypatch.setattr('src.live.profile_controls.showerror',lambda *a,**kw:alerts.append(a))
    old=obj.session.progress
    def fail(*a,**kw):raise OSError('disk unavailable')
    with monkeypatch.context() as patch:
        patch.setattr(old,'save',fail)
        assert not obj.change_profile(second)
    assert store.active=='default' and obj.session.progress is old
    with monkeypatch.context() as patch:
        patch.setattr('src.live.profiles.write_json',fail)
        assert not obj.change_profile(second)
    assert ProfileStore(tmp_path).active=='default' and obj.session.progress is old
    assert len(alerts)==2


def test_settings_profile_ui_creates_and_switches_accounts(tmp_path):
    import subprocess,sys
    from pathlib import Path
    code='''
import sys
from types import SimpleNamespace
from scripts.preview_lunar import PreviewApp
from src.live.profiles import ProfileStore
from src.live.personal_state import prepare_state
from src.live.session import Session
prepare_state(destination=sys.argv[1],legacy_roots=[],allow_new=True)
class Preview(PreviewApp):
 def _panel(self):
  self.profile_store=ProfileStore(sys.argv[1]);super()._panel()
app=Preview();root=app.root;root.attributes('-alpha',0);root.deiconify();root.update()
app.session=Session([],app.profile_store.open_progress())
app.selection_epoch=0;app.automark_generation=0
app.pending_order=[]
app.display_motion=SimpleNamespace(reset=lambda:None)
app.refresh_counts=lambda:None
try:
 section=next(s for s in app.settings_sections if s['title']=='Perfis')
 assert len(app.settings_sections)==7
 section['button'].invoke();root.update()
 app.new_profile_name.set('Conta secundária');app.create_profile();root.update()
 assert app.profile_store.name()=='Conta secundária'
 assert 'Conta secundária' in app.profile_caption.cget('text')
 app.profile_var.set('Principal');app.use_selected_profile();root.update()
 assert app.profile_store.active=='default' and 'Principal' in app.profile_caption.cget('text')
 assert app.profile_box.winfo_width()>80
finally:app.compact.stop();root.destroy()
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
