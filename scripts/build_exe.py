"""Build a reproducible live-only Windows executable without personal references or saves."""
from __future__ import annotations
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def build_executable(install: bool = True) -> None:
    if sys.platform!="win32":
        raise SystemExit("Build the Windows executable on Windows")
    subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean",
                    "--distpath",str(ROOT/"dist"),"--workpath",str(ROOT/"build/pyinstaller"),
                    str(ROOT/"GenshinOverlay.spec")],cwd=ROOT,check=True)
    if not install:
        print(f"Built: {ROOT/'dist/GenshinOverlay.exe'}")
        return
    staged=ROOT/"GenshinOverlay.exe.new"
    shutil.copy2(ROOT/"dist/GenshinOverlay.exe",staged)
    try:
        os.replace(staged,ROOT/"GenshinOverlay.exe")
    except PermissionError:
        raise SystemExit("Feche a versão anterior e execute o build novamente. O novo arquivo está em dist/GenshinOverlay.exe.")
    print(f"Executable: {ROOT/'GenshinOverlay.exe'}")
    print("Personal reference packs stay in userData; not bundled or redistributed.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-only",action="store_true",help="Build without replacing the running installation")
    build_executable(install=not parser.parse_args().build_only)
