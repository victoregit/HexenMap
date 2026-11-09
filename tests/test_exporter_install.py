import json
import pytest
from scripts.package_exporter import package
from src.live.exporter_install import prepare_extension,FILES


def test_bundled_extension_is_complete_stable_and_ready_to_load(tmp_path):
    package(tmp_path/'bundle')
    source=tmp_path/'bundle/HexenMapExporter'
    folder=prepare_extension(source,tmp_path/'installed')
    assert folder==prepare_extension(source,tmp_path/'installed')
    assert {p.name for p in folder.iterdir()}==set(FILES)
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'))
    for entry in manifest['content_scripts']:
        for name in entry['js']:
            assert 'const HexenAppSample = globalThis.HexenAppSample' in (folder/name).read_text(encoding='utf-8')
    assert not any('progress' in path.name for path in folder.rglob('*'))


def test_new_bundle_keeps_existing_browser_folder_and_never_overwrites_edits(tmp_path):
    package(tmp_path/'bundle');source=tmp_path/'bundle/HexenMapExporter'
    old=prepare_extension(source,tmp_path/'installed')
    (source/'popup.css').write_text('/* new bundle */',encoding='utf-8')
    new=prepare_extension(source,tmp_path/'installed')
    assert old!=new and old.is_dir()
    (new/'popup.css').write_text('local edit',encoding='utf-8')
    with pytest.raises(ValueError):prepare_extension(source,tmp_path/'installed')
    assert (new/'popup.css').read_text(encoding='utf-8')=='local edit'
