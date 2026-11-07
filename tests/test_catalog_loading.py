import queue
import threading
from types import SimpleNamespace

from src.live.loading import CatalogLoader
from src.live.desktop import DesktopApp
from src.live.storage import PreferenceWriter


def test_only_latest_request_runs_after_inflight_work_and_cache_is_bounded():
    entered=threading.Event();release=threading.Event();calls=[]
    def load(identifier):
        calls.append(identifier)
        if identifier=='first':entered.set();assert release.wait(3)
        return identifier+'-package'
    loader=CatalogLoader(load)
    try:
        loader.request('first');assert entered.wait(3)
        loader.request('skipped');generation=loader.request('last')
        release.set()
        assert loader.results.get(timeout=3)==(generation,'last','last-package',None)
        assert calls==['first','last']
        generation=loader.request('first')
        assert loader.results.get(timeout=3)==(generation,'first','first-package',None)
        assert calls==['first','last']
        g=loader.request('third')
        assert loader.results.get(timeout=3)==(g,'third','third-package',None)
        assert len(loader.cache)==2
    finally:release.set();loader.close();loader.thread.join(3)
    assert not loader.thread.is_alive()


def test_failure_is_a_result_and_does_not_kill_loader():
    def load(identifier):
        if identifier=='bad':raise ValueError('Hash inválido')
        return identifier
    loader=CatalogLoader(load)
    try:
        g=loader.request('bad')
        assert loader.results.get(timeout=3)==(g,'bad',None,'Hash inválido')
        g=loader.request('ok')
        assert loader.results.get(timeout=3)==(g,'ok','ok',None)
    finally:loader.close();loader.thread.join(3)


def test_ui_ignores_already_queued_obsolete_completions():
    app=DesktopApp.__new__(DesktopApp)
    results=queue.Queue()
    results.put((1,'first',object(),None))
    app.catalog_loader=SimpleNamespace(results=results)
    app.preference_writer=SimpleNamespace(errors=queue.Queue())
    app.catalog_generation=2;app.requested_package='last';app.region_loading=True
    app.package_id='original'
    app.poll_catalog()
    assert app.package_id=='original' and app.region_loading


def test_failed_latest_selection_restores_old_panel_without_touching_progress():
    app=DesktopApp.__new__(DesktopApp)
    results=queue.Queue();results.put((2,'last',None,'Hash inválido'))
    app.catalog_loader=SimpleNamespace(results=results)
    app.preference_writer=SimpleNamespace(errors=queue.Queue())
    app.catalog_generation=2;app.requested_package='last';app.region_loading=True
    app.package_id='original';app.region_names={'Original':'original','Last':'last'}
    calls=[];app.region_var=SimpleNamespace(set=lambda v:calls.append(v))
    progress=object();app.session=SimpleNamespace(notice='',progress=progress)
    app.populate_region_controls=lambda:calls.append('restore-controls')
    app.reload_reference=lambda:calls.append('restore-reference')
    app.poll_catalog()
    assert calls==['Original','restore-controls','restore-reference']
    assert app.session.progress is progress and app.package_id=='original'
    assert not app.region_loading


def test_preferences_are_ordered_snapshots_and_flush_latest_on_close(tmp_path):
    entered=threading.Event();release=threading.Event();written=[]
    def save(path,data):
        if data['value']==1:entered.set();assert release.wait(3)
        written.append(data)
    writer=PreferenceWriter(tmp_path/'settings.json',write=save)
    settings={'value':1,'categories':['first']}
    writer.request(settings);assert entered.wait(3)
    settings['value']=2;settings['categories'].append('second');writer.request(settings)
    settings['value']=3;writer.request(settings)
    settings['categories'].append('not-submitted')
    release.set()
    assert writer.close()
    assert written==[{'value':1,'categories':['first']},{'value':3,'categories':['first','second']}]


def test_preference_failure_is_reported_and_next_save_can_recover(tmp_path):
    failed=threading.Event()
    def save(path,data):
        if data['value']==1:failed.set();raise OSError('Disk failure')
    writer=PreferenceWriter(tmp_path/'settings.json',write=save)
    writer.request({'value':1});assert failed.wait(3)
    assert writer.errors.get(timeout=3)==(1,'Disk failure')
    writer.request({'value':2})
    assert writer.close()


def test_layer_index_cancelled_before_loading_obsolete_pack():
    import pytest
    from src.live.vision import LayerRecognizer
    from src.live.reference import ReferenceCancelled
    calls=[]
    with pytest.raises(ReferenceCancelled):
        LayerRecognizer([lambda:calls.append('loaded')],cancelled=lambda:True)
    assert calls==[]
