"""Build the versioned Windows portable release without mixing binaries and data."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.identity import VERSION


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer',action='store_true',help='Gerar também o Setup com launcher')
    parser.add_argument('--iscc',type=Path,help='Caminho do compilador Inno Setup')
    args=parser.parse_args()
    target=ROOT/'dist/atual'/f'HexenMap-{VERSION}'
    if (target/'package-report.json').exists() or (target.parent/f'HexenMap-{VERSION}-Windows-x64.zip').exists():
        raise FileExistsError(f'{VERSION} já existe; incremente a versão ou arquive a entrega anterior.')
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    for spec in ('HexenMap.spec','HexenMapBridge.spec'):
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(ROOT/'build/release-staging'),
                        '--workpath',str(ROOT/'build/pyinstaller'),str(ROOT/spec)],cwd=ROOT,env=env,check=True)
    from scripts.package_portable import main as package
    package()
    if args.installer:
        command=[sys.executable,str(ROOT/'scripts/build_installer.py')]
        if args.iscc:command.extend(['--iscc',str(args.iscc)])
        subprocess.run(command,cwd=ROOT,env=env,check=True)


if __name__=='__main__':main()
