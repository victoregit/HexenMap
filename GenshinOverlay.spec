# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root=Path(SPECPATH)
a=Analysis(
    [str(root/'src/app.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'data/community/mondstadt'),'data/community/mondstadt'),
           (str(root/'data/community/kongying'),'data/community/kongying'),
           (str(root/'data/assets/nations'),'data/assets/nations'),
           (str(root/'data/assets/chests'),'data/assets/chests'),
           (str(root/'data/assets/oculi'),'data/assets/oculi')],
    hiddenimports=['PIL._tkinter_finder'],
    excludes=['src.legacy_app'],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='GenshinOverlay',
        console=False,debug=False,strip=False,upx=False,
        disable_windowed_traceback=False)
