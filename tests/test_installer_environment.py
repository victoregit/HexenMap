"""Exercise the real post-update launch; a normal install smoke skips [Run]."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(sys.platform!='win32',reason='Native Windows installer')
def test_post_update_launch_resets_environment_in_actual_child(tmp_path):
    root=Path(__file__).resolve().parents[1]
    compiler=root/'build/tools/inno/ISCC.exe'
    csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not compiler.exists() or not csc.exists():pytest.skip('Inno Setup and Windows C# compiler required')
    package=tmp_path/'package';package.mkdir()
    for directory in ('userData','creditos'):(package/directory).mkdir()
    source=tmp_path/'Probe.cs'
    source.write_text('''using System; using System.IO;
class Probe { static void Main() {
File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"environment.txt"),
Environment.GetEnvironmentVariable("PYINSTALLER_RESET_ENVIRONMENT")+"\\n"+
Environment.GetEnvironmentVariable("_PYI_APPLICATION_HOME_DIR"));
} }''')
    def run(args,**kwargs):
        return subprocess.run(list(map(str,args)),capture_output=True,text=True,check=True,timeout=45,**kwargs)
    run([csc,'/nologo','/target:winexe','/out:'+str(package/'HexenMapLauncher.exe'),source])
    for name in ('HexenMap.exe','HexenMapBridge.exe'):(package/name).write_bytes(b'MZfixture')
    for name in ('BUILD.json','LEIA-ME.txt','userData/settings.json','creditos/NOTICE.txt'):
        (package/name).write_text('{}')
    run([compiler,'/Q','/DAppVersion=1.0.4','/DTestSuffix=-EnvironmentTest',
         f'/DPackageDir={package}',f'/DLauncherFile={package / "HexenMapLauncher.exe"}',
         f'/DOutputDir={tmp_path}',root/'installer/HexenMap.iss'])
    installation=tmp_path/'installation'
    env=dict(os.environ)
    env.update(_PYI_ARCHIVE_FILE='expired-launcher.exe',_PYI_APPLICATION_HOME_DIR='expired-parent',_PYI_PARENT_PROCESS_LEVEL='1')
    env.pop('PYINSTALLER_RESET_ENVIRONMENT',None)
    try:
        run([tmp_path/'HexenMap-1.0.4-Setup-x64-EnvironmentTest.exe','/VERYSILENT',
             '/SUPPRESSMSGBOXES','/NORESTART','/UPDATE=1',f'/DIR={installation}'],env=env)
        output=installation/'environment.txt';deadline=time.monotonic()+10
        while not output.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert output.read_text().splitlines()==['1','expired-parent']
    finally:
        uninstaller=installation/'unins000.exe'
        if uninstaller.exists():run([uninstaller,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'])
