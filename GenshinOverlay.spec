# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root=Path(SPECPATH)
a=Analysis(
    [str(root/'src/app.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'data/community/mondstadt'),'data/community/mondstadt')],
    hiddenimports=['PIL._tkinter_finder'],
    excludes=['src.legacy_app'],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='GenshinOverlay',
        console=False,debug=False,strip=False,upx=False,
        disable_windowed_traceback=False)
