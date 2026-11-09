# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

root=Path(SPECPATH)
sys.path.insert(0,str(root))
from scripts.package_exporter import package
extension_zip=package(root/'build/exporter-bundle')
a=Analysis(
    [str(root/'src/app.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'data/assets/chests'),'data/assets/chests'),
           (str(root/'data/assets/oculi'),'data/assets/oculi'),
           (str(root/'data/assets/brand'),'data/assets/brand'),
           (str(root/'data/localization'),'data/localization'),
           (str(root/'data/import'),'data/import'),
           (str(extension_zip.parent/'HexenMapExporter'),'data/exporter')],
    hiddenimports=['PIL._tkinter_finder'],
    excludes=['src.legacy_app'],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='HexenMap',
        uac_admin=True,
        console=False,debug=False,strip=False,upx=False,
        disable_windowed_traceback=False,icon=str(root/'data/assets/brand/app.ico'),version=str(root/'data/windows/version_info.txt'))
