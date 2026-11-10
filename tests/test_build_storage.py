from src.live import storage


def test_repository_build_reuses_installed_data(tmp_path,monkeypatch):
    (tmp_path/'.git').mkdir();(tmp_path/'HexenMap.spec').touch()
    source=tmp_path/'userData/catalogs/appsample/SOURCE.json'
    source.parent.mkdir(parents=True);source.write_text('{}')
    monkeypatch.setattr(storage.sys,'frozen',True,raising=False)
    monkeypatch.setattr(storage.sys,'executable',str(tmp_path/'dist/HexenMap.exe'))
    assert storage.install_dir()==tmp_path


def test_portable_build_never_picks_up_neighboring_progress(tmp_path,monkeypatch):
    source=tmp_path/'userData/catalogs/appsample/SOURCE.json'
    source.parent.mkdir(parents=True);source.write_text('{}')
    monkeypatch.setattr(storage.sys,'frozen',True,raising=False)
    monkeypatch.setattr(storage.sys,'executable',str(tmp_path/'dist/HexenMap.exe'))
    assert storage.install_dir()==tmp_path/'dist'
    (tmp_path/'.git').mkdir();(tmp_path/'HexenMap.spec').touch()
    monkeypatch.setattr(storage.sys,'executable',str(tmp_path/'portable/HexenMap.exe'))
    assert storage.install_dir()==tmp_path/'portable'
