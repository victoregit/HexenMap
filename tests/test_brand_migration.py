from types import SimpleNamespace
import pytest
import src.live.native as native
from src.live.identity import INSTANCE_MUTEX,LEGACY_INSTANCE_MUTEX


@pytest.mark.parametrize('legacy_running',[False,True])
def test_new_brand_prevents_duplicate_instances_with_previous_builds(monkeypatch,legacy_running):
    instance=native.Windows.__new__(native.Windows);instance.instance_handle=None
    created=[];closed=[]
    def create(owner,initial,name):created.append(name);return 100+len(created)
    monkeypatch.setattr(native.ct,'get_last_error',lambda:183 if legacy_running and len(created)==2 else 0,raising=False)
    instance.k=SimpleNamespace(CreateMutexW=create,CloseHandle=lambda h:closed.append(h))
    instance.existing_panel=lambda:None
    assert instance.acquire_instance()==(not legacy_running)
    assert created==[INSTANCE_MUTEX,LEGACY_INSTANCE_MUTEX]
    if not legacy_running:instance.release_instance()
    assert closed==[101,102]
