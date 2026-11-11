"""Materialize the bundled, self-contained exporter in a permanent local folder."""
from src.live.i18n import tr as _tr
import hashlib
import json
from pathlib import Path

from src.live.storage import bundle_dir,install_dir

FILES=('manifest.json','capture.js','bridge.js','popup.html','popup.css','popup.js',
       'appsample-core.js','LEIA-ME.html')


def prepare_extension(source=None,destination=None):
    source=Path(source) if source is not None else bundle_dir()/'data/exporter'
    if not source.is_dir() and source==bundle_dir()/'data/exporter':
        source=install_dir()/'build/exporter-bundle/HexenMapExporter'
    contents={name:(source/name).read_bytes() for name in FILES}
    manifest=json.loads(contents['manifest.json'].decode('utf-8-sig'))
    if manifest.get('manifest_version')!=3:raise ValueError(_tr('Extensão incluída inválida'))
    digest=hashlib.sha256()
    for name,raw in sorted(contents.items()):digest.update(name.encode()+b'\0'+raw)
    # Keep paths fixed across runs, independent of PyInstaller's temporary folder.
    # A new bundle gets a new directory; an existing browser installation stays intact.
    destination=Path(destination) if destination is not None else install_dir()/'userData/tools'
    folder=destination/('HexenMapExporter-'+digest.hexdigest()[:16])
    folder.mkdir(parents=True,exist_ok=True)
    for name,raw in contents.items():
        path=folder/name
        if path.exists():
            if path.read_bytes()!=raw:raise ValueError(_tr('A pasta local da extensão foi alterada. Preserve-a e escolha uma instalação limpa.'))
        else:path.write_bytes(raw)
    return folder
