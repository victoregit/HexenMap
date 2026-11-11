from pathlib import Path
root=Path(SPECPATH)
a=Analysis([str(root/'src/launcher.py')],pathex=[str(root)],binaries=[],datas=[(str(root/'data/localization/ui-en-US.json'),'data/localization'),(str(root/'data/assets/brand/app.ico'),'data/assets/brand'),
                  (str(root/'data/assets/brand/animations.json'),'data/assets/brand'),
                  (str(root/'data/assets/brand/loading'),'data/assets/brand/loading')],hiddenimports=[],
           excludes=['cv2','numpy','PIL','psutil'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='HexenMapLauncher',console=False,uac_admin=True,
        debug=False,strip=False,upx=False,icon=str(root/'data/assets/brand/app.ico'),
        version=str(root/'data/windows/version_info.txt'))
