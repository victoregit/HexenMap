"""Build a dependency-free load-unpacked extension ZIP, never including user data."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('manifest.json', 'capture.js', 'bridge.js', 'popup.html', 'popup.css', 'popup.js')

def package(output=None):
    output = Path(output or ROOT / 'dist')
    output.mkdir(parents=True, exist_ok=True)
    folder = output / 'HexenMapExporter'
    folder.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copyfile(ROOT / 'extensions/hexen-map-exporter' / name, folder / name)
    # Each execution world gets a complete entry point. Do not rely on a
    # global established by a separately injected content-script file.
    core = (ROOT / 'data/import/appsample-core.js').read_text(encoding='utf-8-sig')
    for name in ('capture.js', 'bridge.js'):
        entry = (ROOT / 'extensions/hexen-map-exporter' / name).read_text(encoding='utf-8-sig')
        (folder / name).write_text(
            '/* Generated entry: shared core + observer in one execution. */\n'
            '(() => {\n' + core + '\nconst HexenAppSample = globalThis.HexenAppSample;\n' + entry + '\n})();\n',
            encoding='utf-8')
    shutil.copyfile(ROOT / 'data/import/appsample-core.js', folder / 'appsample-core.js')
    shutil.copyfile(ROOT / 'docs/EXPORTER_INSTALL.html', folder / 'LEIA-ME.html')
    version = json.loads((folder / 'manifest.json').read_text(encoding='utf-8-sig'))['version']
    target = output / f'HexenMapExporter-{version}-teste.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in (*FILES, 'appsample-core.js', 'LEIA-ME.html'):
            archive.write(folder / name, 'HexenMapExporter/' + name)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest + '  ' + target.name + '\n', encoding='utf-8')
    return target

if __name__ == '__main__':
    print(package())
