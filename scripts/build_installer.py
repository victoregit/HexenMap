"""Package a reviewed portable release with a launcher elevated before startup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.identity import VERSION


def verify_package(package):
    report=json.loads((package/'BUILD.json').read_text(encoding='utf-8'))
    if report.get('version') != VERSION or report.get('personal_progress_included') is not False:
        raise ValueError('O pacote deve corresponder à versão atual e excluir progresso pessoal')
    for name,digest in report['files'].items():
        path=(package/name).resolve()
        if not path.is_relative_to(package.resolve()) or not path.is_file():
            raise ValueError('Arquivo fora do pacote ou ausente')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Hash divergente: {name}')
    expected=set(report['files'])|{'BUILD.json'}
    actual={str(p.relative_to(package)).replace('\\','/') for p in package.rglob('*') if p.is_file()}
    if expected != actual:
        raise ValueError('Há arquivos não declarados no pacote')
    forbidden=('progress.json','overlay.log','settings.json.bak')
    if any(Path(name).name in forbidden for name in actual):
        raise ValueError('Pacote contém arquivos pessoais')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iscc',type=Path)
    parser.add_argument('--package',type=Path,default=ROOT/f'dist/atual/HexenMap-{VERSION}/Hexen Map')
    args=parser.parse_args()
    verify_package(args.package)
    compiler=args.iscc or shutil.which('ISCC')
    if not compiler:
        raise SystemExit('Instale Inno Setup 6.4+ ou 7 e passe --iscc caminho/ISCC.exe. Veja docs/UPDATES.md.')
    env=os.environ.copy()
    env.pop('PYTHONPATH',None)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm',
                    '--distpath',str(ROOT/'build/release-staging'),
                    '--workpath',str(ROOT/'build/pyinstaller'),str(ROOT/'HexenMapLauncher.spec')],cwd=ROOT,env=env,check=True)
    output=ROOT/'dist/installer'
    target=output/f'HexenMap-{VERSION}-Setup-x64.exe'
    if target.exists():
        raise FileExistsError('Instalador dessa versão já existe; não sobrescreva uma release publicada')
    subprocess.run([str(compiler),'/Q',f'/DAppVersion={VERSION}',f'/DPackageDir={args.package.resolve()}',
                    f'/DLauncherFile={ROOT / "build/release-staging/HexenMapLauncher.exe"}',
                    f'/DOutputDir={output}',str(ROOT/'installer/HexenMap.iss')],cwd=ROOT,check=True)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.exe.sha256').write_text(f'{digest}  {target.name}\n',encoding='utf-8')
    print(json.dumps({'installer':str(target),'sha256':digest,'version':VERSION}))


if __name__=='__main__':main()
