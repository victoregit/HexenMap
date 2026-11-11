import json
from pathlib import Path
import string
import subprocess
import sys

import pytest

from src.live import i18n


@pytest.fixture
def preference(tmp_path, monkeypatch):
    path = tmp_path / 'HexenMap' / 'language.json'
    monkeypatch.setattr(i18n, 'language_path', lambda: path)
    i18n.get_language.cache_clear()
    yield path
    i18n.get_language.cache_clear()


@pytest.mark.parametrize('raw', ['{}', 'null', '{', '{"language":[]}', '{"language":"invalid"}'])
def test_invalid_preference_preserves_portuguese_default(preference, raw):
    preference.parent.mkdir()
    preference.write_text(raw, encoding='utf-8')
    assert i18n.get_language() == 'pt-BR'


def test_preference_is_atomic_and_applies_on_reopen_without_creating_a_save(preference):
    assert i18n.get_language() == 'pt-BR'
    i18n.save_language('en-US')
    assert json.loads(preference.read_text()) == {'language': 'en-US'}
    assert i18n.get_language() == 'pt-BR'
    assert not (preference.parent / 'state').exists()
    assert list(preference.parent.iterdir()) == [preference]
    i18n.get_language.cache_clear()
    assert i18n.get_language() == 'en-US'
    with pytest.raises(ValueError):
        i18n.save_language('fr-FR')
    assert json.loads(preference.read_text())['language'] == 'en-US'


def test_original_installation_pointer_selects_shared_preference(tmp_path, monkeypatch):
    home = tmp_path / 'app'; home.mkdir()
    state = tmp_path / 'original-user' / 'HexenMap' / 'state'
    (home / 'state-dir.txt').write_text(str(state), encoding='utf-8-sig')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(home / 'HexenMapLauncher.exe'))
    assert i18n.language_path() == state.parent / 'language.json'


def test_catalog_keeps_all_format_fields_and_qualified_game_hud():
    formatter = string.Formatter()
    fields = lambda text: sorted((field, spec, conversion) for _, field, spec, conversion in formatter.parse(text) if field is not None)
    messages = i18n.english_messages()
    assert messages
    for portuguese, english in messages.items():
        assert english.strip()
        assert fields(portuguese) == fields(english), portuguese
    assert any('Portuguese game HUD' in value for value in messages.values())


def test_english_catalog_preserves_ids_groups_and_bilingual_search(monkeypatch):
    from src.live.category_browser import CategoryModel
    from src.live.catalog import Item
    from src.live.labels import normalized
    from src.live.localization import localized_metadata
    metadata = localized_metadata({'as-o161': {'name': 'Menta', 'source_name': 'Menta', 'source_type': 'o161', 'group': 'Recursos'}})
    item = Item('appsample:marker:123', 'Original', 'as-o161', 1, 2)
    monkeypatch.setattr(i18n, 'get_language', lambda: 'pt-BR')
    pt = CategoryModel([item], metadata).entries[0]
    monkeypatch.setattr(i18n, 'get_language', lambda: 'en-US')
    en = CategoryModel([item], metadata).entries[0]
    assert en.label == 'Mint'
    assert en.key == pt.key and en.members == pt.members and en.group == pt.group
    assert normalized(pt.label) in en.search and normalized(en.label) in en.search
    assert item.id == 'appsample:marker:123' and metadata['as-o161']['name'] == 'Menta'


def test_reports_keep_user_text_in_english_interface(monkeypatch):
    from src.live.support import report_payload, transport_error
    monkeypatch.setattr(i18n, 'get_language', lambda: 'en-US')
    payload = report_payload('', 'Jogar')
    assert payload['mensagem'] == 'Jogar'
    assert 'timed out' in transport_error(TimeoutError())


def test_profile_name_is_not_translated_even_when_it_matches_a_button(monkeypatch):
    from types import SimpleNamespace
    from src.live.profile_controls import ProfileControls
    monkeypatch.setattr(i18n, 'get_language', lambda: 'en-US')
    caption = {}
    variable = []
    app = SimpleNamespace(
        profile_store=SimpleNamespace(profiles=[{'id': 'default', 'name': 'Jogar'}], name=lambda: 'Jogar'),
        profile_box=SimpleNamespace(configure=lambda **kw: None),
        profile_var=SimpleNamespace(set=variable.append),
        profile_caption=SimpleNamespace(configure=lambda **kw: caption.update(kw)),
    )
    ProfileControls.sync_profile_controls(app)
    assert variable == ['Jogar'] and caption['text'] == 'Profile: Jogar'


@pytest.mark.parametrize('scale', [1., 1.25, 1.5])
def test_english_panel_layout_and_language_selection(scale, tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = f'''
import gc; gc.disable()
from src.live import i18n
i18n.get_language=lambda:'en-US'
i18n.language_path=lambda:__import__('pathlib').Path({str(tmp_path / 'language.json')!r})
from scripts.preview_lunar import check,PreviewApp
check({scale},(1366,768))
app=PreviewApp({scale},(1366,768))
app.show_settings();app.root.update_idletasks()
from tkinter import ttk
def children(widget):
    for child in widget.winfo_children():
        yield child
        yield from children(child)
box=next(w for w in children(app.prefs) if isinstance(w,ttk.Combobox) and tuple(w.cget('values'))==tuple(i18n.LANGUAGES.values()))
assert box.get()=='English'
box.set('Português (Brasil)');box.event_generate('<<ComboboxSelected>>');app.root.update()
assert __import__('json').loads(i18n.language_path().read_text())['language']=='pt-BR'
assert app.items_tab.cget('text')=='⌖  Items'
app.compact.stop();app.root.destroy()
'''
    subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True, timeout=35, check=True)


def test_installer_language_choice_and_silent_update_preservation(tmp_path):
    from src.live.identity import VERSION
    root = Path(__file__).resolve().parents[1]
    compiler = root / 'build/tools/inno/ISCC.exe'
    if sys.platform != 'win32' or not compiler.exists():
        pytest.skip('Windows and Inno Setup required')
    package = tmp_path / 'package'; package.mkdir()
    for directory in ('userData', 'creditos'):
        (package / directory).mkdir()
    for name in ('HexenMap.exe', 'HexenMapLauncher.exe', 'HexenMapBridge.exe'):
        (package / name).write_bytes(b'MZfixture')
    for name in ('BUILD.json', 'userData/settings.json', 'creditos/NOTICE.txt'):
        (package / name).write_text('{}')
    def run(args):
        return subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=45,check=True)
    run([compiler, '/Q', f'/DAppVersion={VERSION}', '/DTestSuffix=-LanguageTest',
         f'/DPackageDir={package}', f'/DLauncherFile={package / "HexenMapLauncher.exe"}',
         f'/DOutputDir={tmp_path}', root / 'installer/HexenMap.iss'])
    installation = tmp_path / 'installation'
    installer = tmp_path / f'HexenMap-{VERSION}-Setup-x64-LanguageTest.exe'
    preference = installation / 'test-user-data/language.json'
    def install(language):
        run([installer, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NORUN=1',
             f'/LANG={language}', f'/DIR={installation}'])
    try:
        install('english')
        assert json.loads(preference.read_text())['language'] == 'en-US'
        preference.write_text('{"language":"pt-BR"}')
        install('english')
        assert json.loads(preference.read_text())['language'] == 'pt-BR'
        preference.unlink()
        install('brazilianportuguese')
        assert json.loads(preference.read_text())['language'] == 'pt-BR'
    finally:
        uninstaller = installation / 'unins000.exe'
        if uninstaller.exists():
            run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
