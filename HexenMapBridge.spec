# Native messaging requires binary stdio and a non-elevated host.
from pathlib import Path
root=Path(SPECPATH)
a=Analysis([str(root/'src/browser_bridge.py')],pathex=[str(root)],binaries=[],datas=[],hiddenimports=[],excludes=['tkinter','cv2','numpy','PIL'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='HexenMapBridge',console=True,uac_admin=False,debug=False,strip=False,upx=False)
