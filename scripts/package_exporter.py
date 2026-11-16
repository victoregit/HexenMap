"""Build a dependency-free load-unpacked extension ZIP, never including user data."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'manifest.json', 'capture.js', 'bridge.js', 'hoyolab-capture.js', 'hoyolab-bridge.js',
    'popup.html', 'popup.css', 'popup.js',
    'icon-16.png', 'icon-32.png', 'icon-48.png', 'icon-128.png'
)

def package(output=None):
    version = json.loads((ROOT / 'extensions/hexen-map-exporter/manifest.json').read_text(encoding='utf-8-sig'))['version']
    output = Path(output or ROOT / 'dist/extensoes' / version)
    output.mkdir(parents=True, exist_ok=True)
    folder = output / 'HexenMapExporter'
    folder.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copyfile(ROOT / 'extensions/hexen-map-exporter' / name, folder / name)

    # Each execution world gets a complete entry point. Do not rely on a
    # global established by a separately injected content-script file.
    appsample_core = (ROOT / 'data/import/appsample-core.js').read_text(encoding='utf-8-sig')
    for name in ('capture.js', 'bridge.js'):
        entry = (ROOT / 'extensions/hexen-map-exporter' / name).read_text(encoding='utf-8-sig')
        (folder / name).write_text(
            '/* Generated entry: shared core + observer in one execution. */\n'
            '(() => {\n' + appsample_core + '\nconst HexenAppSample = globalThis.HexenAppSample;\n' + entry + '\n})();\n',
            encoding='utf-8')

    hoyolab_core = (ROOT / 'extensions/hexen-map-exporter/hoyolab-core.js').read_text(encoding='utf-8-sig')
    hoyolab_index = (ROOT / 'extensions/hexen-map-exporter/hoyolab-index.json').read_text(encoding='utf-8-sig')

    capture_entry = (ROOT / 'extensions/hexen-map-exporter/hoyolab-capture.js').read_text(encoding='utf-8-sig')
    (folder / 'hoyolab-capture.js').write_text(
        '/* Generated entry: shared HoYoLAB core + capture in one execution. */\n'
        '(() => {\n' + hoyolab_core + '\nconst HexenHoYoLAB = globalThis.HexenHoYoLAB;\n' + capture_entry + '\n})();\n',
        encoding='utf-8')

    bridge_entry = (ROOT / 'extensions/hexen-map-exporter/hoyolab-bridge.js').read_text(encoding='utf-8-sig')
    (folder / 'hoyolab-bridge.js').write_text(
        '/* Generated entry: shared HoYoLAB core + index + bridge in one execution. */\n'
        '(() => {\n' + hoyolab_core + '\nconst HexenHoYoLAB = globalThis.HexenHoYoLAB;\n'
        'globalThis.HexenHoYoLabIndex = ' + hoyolab_index.strip() + ';\n' + bridge_entry + '\n})();\n',
        encoding='utf-8')

    shutil.copyfile(ROOT / 'data/import/appsample-core.js', folder / 'appsample-core.js')
    shutil.copyfile(ROOT / 'extensions/hexen-map-exporter/hoyolab-core.js', folder / 'hoyolab-core.js')
    shutil.copyfile(ROOT / 'extensions/hexen-map-exporter/hoyolab-index.json', folder / 'hoyolab-index.json')
    shutil.copyfile(ROOT / 'docs/EXPORTER_INSTALL.html', folder / 'LEIA-ME.html')

    version = json.loads((folder / 'manifest.json').read_text(encoding='utf-8-sig'))['version']
    target = output / f'HexenMapExporter-{version}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in (*FILES, 'appsample-core.js', 'hoyolab-core.js', 'hoyolab-index.json', 'LEIA-ME.html'):
            archive.write(folder / name, 'HexenMapExporter/' + name)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest + '  ' + target.name + '\n', encoding='utf-8')
    return target

if __name__ == '__main__':
    print(package())
