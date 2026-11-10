"""Build the versioned Windows portable release without mixing binaries and data."""
from pathlib import Path
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.identity import VERSION


def main():
    target=ROOT/'dist/atual'/f'HexenMap-{VERSION}'
    if (target/'package-report.json').exists() or (target.parent/f'HexenMap-{VERSION}-Windows-x64.zip').exists():
        raise FileExistsError(f'{VERSION} já existe; incremente a versão ou arquive a entrega anterior.')
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    for spec in ('HexenMap.spec','HexenMapBridge.spec'):
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(ROOT/'build/release-staging'),
                        '--workpath',str(ROOT/'build/pyinstaller'),str(ROOT/spec)],cwd=ROOT,env=env,check=True)
    from scripts.package_portable import main as package
    package()


if __name__=='__main__':main()
