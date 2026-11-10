"""Exercise the real installer using tiny dummy binaries and a separate test AppId."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import winreg

ROOT=Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    result=subprocess.run([str(p) for p in command],capture_output=True,text=True,**kwargs)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {result.stdout}\n{result.stderr}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iscc',required=True,type=Path)
    parser.add_argument('--work-dir',type=Path,default=ROOT/'build/installer-smoke')
    args=parser.parse_args()
    home=args.work_dir.resolve()
    package=home/'package'
    if (home/'installation').exists():
        raise FileExistsError('Use a fresh smoke directory; existing data is not deleted')
    (package/'userData').mkdir(parents=True,exist_ok=True)
    (package/'creditos').mkdir(exist_ok=True)
    (package/'creditos/NOTICE.txt').write_text('test')
    (package/'LEIA-ME.txt').write_text('test')
    (package/'userData/settings.json').write_text('{"initial":true}')
    (package/'BUILD.json').write_text('{}')
    launcher=package/'HexenMapLauncher.exe'
    destination=home/'installation'
    suffix='-Smoke'
    registry=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\HexenMap-Smoke_is1'
    for version,payload in [('1.0.1','old'),('1.0.2','new')]:
        for name in ('HexenMap.exe','HexenMapBridge.exe','HexenMapLauncher.exe'):
            (package/name).write_bytes(b'MZ'+payload.encode())
        run([args.iscc.resolve(),'/Q',f'/DAppVersion={version}',f'/DPackageDir={package}',
             f'/DLauncherFile={launcher}',f'/DOutputDir={home}',f'/DTestSuffix={suffix}',ROOT/'installer/HexenMap.iss'])
        setup=home/f'HexenMap-{version}-Setup-x64{suffix}.exe'
        run([setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NORUN=1',f'/DIR={destination}'])
        if payload=='old':
            (destination/'userData/progress.json').write_text('collected:123')
            (destination/'userData/settings.json').write_text('custom settings')
        assert (destination/'userData/progress.json').read_text()=='collected:123'
        assert (destination/'userData/settings.json').read_text()=='custom settings'
        assert (destination/'HexenMap.exe').read_bytes()==b'MZ'+payload.encode()
        assert (destination/'installed-user.txt').read_text(encoding='mbcs').strip()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:
            assert winreg.QueryValueEx(key,'DisplayVersion')[0]==version
    shortcut=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Hexen Map-Smoke.lnk'
    assert shortcut.is_file()
    assert (destination/'.previous/HexenMap.exe').read_bytes()==b'MZold'
    # Match the test installer's isolated mutex namespace. Never close the user's overlay.
    recovery=destination/'Restore-Previous.ps1'
    script=recovery.read_text(encoding='utf-8')
    script=script.replace('Local\\HexenMap.LiveOverlay','HexenMapInstallerSmokeOverlay')
    script=script.replace('Local\\GenshinGemWish.LiveOverlay','HexenMapInstallerSmokeLegacy')
    recovery.write_text(script,encoding='utf-8-sig')
    run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',destination/'Restore-Previous.ps1'],input='\n')
    assert (destination/'HexenMap.exe').read_bytes()==b'MZold'
    assert (destination/'updates-paused').is_file()
    assert (destination/'userData/progress.json').read_text()=='collected:123'
    run([destination/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'])
    assert not shortcut.exists()
    assert (destination/'userData/progress.json').read_text()=='collected:123'
    assert (destination/'userData/settings.json').read_text()=='custom settings'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry):
            raise AssertionError('Uninstall registration remains')
    except FileNotFoundError:
        pass
    print(json.dumps({'clean_install':True,'upgrade':True,'start_menu':True,'uninstall_registration':True,
                      'rollback':True,'userdata_preserved_after_uninstall':True}))


if __name__=='__main__':main()
