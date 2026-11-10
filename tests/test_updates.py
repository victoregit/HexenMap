import hashlib
import io
from pathlib import Path
import pytest

from src.live.updates import Release, REPOSITORY, select_release, version_key, download, discover


def release(version='0.5.0-beta.1', raw=b'MZinstaller'):
    name=f'HexenMap-{version}-Setup-x64.exe'
    asset={'name':name,'size':len(raw),'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),
           'browser_download_url':f'https://github.com/{REPOSITORY}/releases/download/v{version}/{name}'}
    return {'tag_name':'v'+version,'prerelease':'-' in version,'assets':[asset]}


class Response(io.BytesIO):
    def geturl(self):
        return 'https://release-assets.githubusercontent.com/test'


def test_semver_and_beta_channel():
    assert REPOSITORY == 'victoregit/HexenMap-Releases'
    assert version_key('0.4.1-beta.10') > version_key('0.4.1-beta.2')
    assert version_key('0.4.1') > version_key('0.4.1-rc.10')
    assert select_release([release()], '0.4.1-beta.1').version=='0.5.0-beta.1'
    assert select_release([release()], '0.4.1') is None
    assert select_release([release('0.4.1-beta.1')], '0.4.1-beta.1') is None
    assert select_release([release('0.3.0')], '0.4.1-beta.1') is None
    assert select_release([release('0.5.0'),release('0.4.2')], '0.4.1').version=='0.5.0'
    with pytest.raises(ValueError):
        version_key('../../evil')


@pytest.mark.parametrize('field,value',[('digest',None),('digest','sha256:abc'),
    ('browser_download_url','https://evil.invalid/setup.exe'),('size',0),('size',2**40),('name','Other.exe')])
def test_unverified_or_foreign_assets_never_install(field,value):
    row=release()
    row['assets'][0][field]=value
    assert select_release([row],'0.4.1-beta.1') is None


def test_drafts_ignored():
    row=release();row['draft']=True
    assert select_release([row],'0.4.1-beta.1') is None


def test_download_verifies_hash_size_and_executable(tmp_path):
    chosen=select_release([release()],'0.4.1-beta.1')
    updates=[]
    path=download(chosen,tmp_path,updates.append,opener=lambda *a,**kw:Response(b'MZinstaller'))
    assert path.read_bytes()==b'MZinstaller' and updates[-1]==1
    assert not list(tmp_path.glob('*.part'))
    with pytest.raises(ValueError):
        download(chosen,tmp_path,opener=lambda *a,**kw:Response(b'MZcorrupted'))
    assert path.read_bytes()==b'MZinstaller'
    assert not list(tmp_path.glob('*.part'))


def test_installer_does_not_touch_existing_userdata(tmp_path):
    saved=tmp_path/'userData/progress.json';saved.parent.mkdir();saved.write_text('personal')
    chosen=select_release([release()],'0.4.1-beta.1')
    download(chosen,tmp_path/'updates',opener=lambda *a,**kw:Response(b'MZinstaller'))
    assert saved.read_text()=='personal'
    script=(Path(__file__).resolve().parents[1]/'installer/HexenMap.iss').read_text(encoding='utf-8')
    data_line=next(line for line in script.splitlines() if line.startswith('Source:') and '\\userData\\*' in line)
    assert 'onlyifdoesntexist' in data_line and 'uninsneveruninstall' in data_line
    assert '{userprograms}' in script and 'HexenMapLauncher.exe' in script
    assert 'PrivilegesRequired=lowest' in script


def test_api_offline_does_not_modify_installation():
    def offline(*a,**kw):
        raise OSError('offline')
    with pytest.raises(OSError):
        discover('0.4.1-beta.1',opener=offline)
