# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root=Path(SPECPATH)
a=Analysis(
    [str(root/'src/app.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'data/assets/chests'),'data/assets/chests'),
           (str(root/'data/assets/oculi'),'data/assets/oculi'),
           (str(root/'data/assets/brand'),'data/assets/brand')],
    hiddenimports=['PIL._tkinter_finder'],
    excludes=['src.legacy_app'],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='HexenMap',
        console=False,debug=False,strip=False,upx=False,
        disable_windowed_traceback=False,icon=str(root/'data/assets/brand/app.ico'),version=str(root/'data/windows/version_info.txt'))
