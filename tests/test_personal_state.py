import json
from pathlib import Path
import pytest

from src.live.personal_state import prepare_state, state_directory, StateRecoveryRequired,NewProfileRequired
from src.progress.progress_manager import ProgressManager, ProgressStorageError


def save(path,ids):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'version':2,'records':{key:{'collected_at':'2026-11-10','notes':'keep'} for key in ids}}))


def test_new_install_folder_uses_same_personal_save(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'profile'))
    old=tmp_path/'old';new=tmp_path/'new'
    save(old/'userData/progress.json',['a','b'])
    state=prepare_state(old)
    first=ProgressManager(str(state/'progress.json'))
    first.mark_collected('c');first.save()
    assert prepare_state(new)==state
    second=ProgressManager(str(prepare_state(new)/'progress.json'))
    assert second.get_collected_ids()=={'a','b','c'}
    assert len(list((state/'migration-backups').rglob('progress.json')))==1
    assert json.loads((old/'userData/progress.json').read_text())['records'].keys()=={'a','b'}


def test_empty_installation_cannot_mask_nonempty_old_save(tmp_path):
    empty=tmp_path/'empty';old=tmp_path/'old'
    save(empty/'progress.json',[]);save(old/'progress.json',['a'])
    state=prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[empty,old])
    assert ProgressManager(str(state/'progress.json')).get_collected_ids()=={'a'}


def test_different_nonempty_saves_require_explicit_recovery(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';save(a/'progress.json',['a']);save(b/'progress.json',['b'])
    with pytest.raises(StateRecoveryRequired):
        prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[a,b])
    assert not (tmp_path/'state/progress.json').exists()


def test_missing_canonical_save_never_silently_starts_over(tmp_path):
    state=prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[],allow_new=True)
    (state/'progress.json').unlink();(state/'progress.json.bak').unlink()
    with pytest.raises(StateRecoveryRequired):
        prepare_state(tmp_path,destination=state,legacy_roots=[])


def test_canonical_uncollection_not_resurrected_by_legacy_copy(tmp_path):
    old=tmp_path/'old';save(old/'progress.json',['a','b'])
    state=prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[old])
    manager=ProgressManager(str(state/'progress.json'));manager.mark_uncollected('b');manager.save()
    prepare_state(tmp_path,destination=state,legacy_roots=[old])
    assert ProgressManager(str(state/'progress.json')).get_collected_ids()=={'a'}


def test_missing_primary_recovers_from_backup_and_corruption_fails_closed(tmp_path):
    path=tmp_path/'progress.json'
    save(Path(str(path)+'.bak'),['a'])
    assert ProgressManager(str(path)).get_collected_ids()=={'a'}
    path.write_text('{}');Path(str(path)+'.bak').write_text('{}')
    with pytest.raises(ProgressStorageError):ProgressManager(str(path))
    assert path.read_text()=='{}'


def test_backup_failure_never_overwrites_last_save(tmp_path,monkeypatch):
    path=tmp_path/'progress.json';save(path,['a']);before=path.read_bytes()
    manager=ProgressManager(str(path));manager.mark_collected('b')
    def fail(*args,**kwargs):raise OSError('disk full')
    monkeypatch.setattr('src.progress.progress_manager.shutil.copy2',fail)
    with pytest.raises(ProgressStorageError):manager.save()
    assert path.read_bytes()==before


def test_install_pointer_preserves_original_profile_after_admin_switch(tmp_path,monkeypatch):
    original=(tmp_path/'original/state').resolve()
    (tmp_path/'state-dir.txt').write_text(str(original),encoding='utf-8')
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'other-admin'))
    assert state_directory(tmp_path)==original


def test_invalid_legacy_data_never_migrated_as_empty(tmp_path):
    old=tmp_path/'old';old.mkdir();(old/'progress.json').write_text('{}')
    with pytest.raises(StateRecoveryRequired):prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[old])
    assert not (tmp_path/'state/progress.json').exists()


def test_first_start_requires_explicit_new_profile_decision(tmp_path):
    with pytest.raises(NewProfileRequired):
        prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[])
    assert not (tmp_path/'state/progress.json').exists()


def test_explicit_backup_from_old_portable_folder_is_migrated(tmp_path):
    source=tmp_path/'download/old-backup.bak';save(source,['a','b'])
    state=prepare_state(tmp_path,destination=tmp_path/'state',legacy_roots=[source])
    assert ProgressManager(str(state/'progress.json')).get_collected_ids()=={'a','b'}


def test_corruption_during_session_cannot_destroy_good_backup(tmp_path):
    path=tmp_path/'progress.json';save(path,['a'])
    manager=ProgressManager(str(path));manager.mark_collected('b');manager.save()
    backup=Path(str(path)+'.bak');before=backup.read_bytes()
    path.write_text('{}')
    with pytest.raises(ProgressStorageError):manager.save()
    assert backup.read_bytes()==before and path.read_text()=='{}'
