"""Public GitHub release discovery and bounded, verified installer downloads."""
from src.live.i18n import tr as _tr
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

REPOSITORY = 'victoregit/HexenMap-Releases'
MAX_INSTALLER = 2 * 1024**3


def version_key(value):
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|rc)\.(0|[1-9]\d*))?', value)
    if not match:
        raise ValueError(_tr('Versão não reconhecida'))
    major, minor, patch, stage, number = match.groups()
    return int(major), int(minor), int(patch), {'alpha':0,'beta':1,'rc':2,None:3}[stage], int(number or 0)


@dataclass(frozen=True)
class Release:
    version: str
    name: str
    url: str
    digest: str
    size: int


def select_release(payload, current):
    installed = version_key(current)
    if not isinstance(payload, list):
        raise ValueError(_tr('Resposta de releases inválida'))
    candidates = []
    for row in payload:
        if not isinstance(row, dict) or row.get('draft'):
            continue
        version = row.get('tag_name', '')
        try:
            key = version_key(version)
        except (ValueError, TypeError):
            continue
        if key <= installed or (installed[3] == 3 and (row.get('prerelease') or key[3] < 3)):
            continue
        normalized = version.removeprefix('v')
        expected = f'HexenMap-{normalized}-Setup-x64.exe'
        for asset in row.get('assets', []):
            if not isinstance(asset, dict) or asset.get('name') != expected:
                continue
            url, digest, size = asset.get('browser_download_url',''), asset.get('digest',''), asset.get('size',0)
            prefix = f'https://github.com/{REPOSITORY}/releases/download/{version}/'
            if (not isinstance(url,str) or url != prefix + expected
                    or not isinstance(digest,str) or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest)
                    or type(size) is not int or not 0 < size <= MAX_INSTALLER):
                continue
            candidates.append((key,Release(normalized,expected,url,digest[7:].lower(),size)))
    return max(candidates,key=lambda r:r[0])[1] if candidates else None


def discover(current, opener=urlopen):
    request = Request(f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=30',
                      headers={'Accept':'application/vnd.github+json','User-Agent':'HexenMapLauncher',
                               'X-GitHub-Api-Version':'2022-11-28'})
    with opener(request, timeout=8) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError(_tr('Resposta de releases grande demais'))
    return select_release(json.loads(raw),current)


def download(release, directory, progress=lambda value:None, opener=urlopen):
    # Revalidate even when called with a constructed Release object.
    valid = select_release([{'tag_name':'v'+release.version,'assets':[{
        'name':release.name,'browser_download_url':release.url,
        'digest':'sha256:'+release.digest,'size':release.size}]}], '0.0.0-alpha.0')
    if valid != release:
        raise ValueError(_tr('Instalador não pertence à release esperada'))
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    target = directory / release.name
    partial = target.with_suffix('.exe.part')
    try:
        digest = hashlib.sha256()
        count = 0
        request = Request(release.url,headers={'User-Agent':'HexenMapLauncher'})
        with opener(request,timeout=20) as response, partial.open('wb') as output:
            final = urlparse(response.geturl())
            if final.scheme != 'https' or final.hostname not in {
                    'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}:
                raise ValueError(_tr('Origem do download inválida'))
            while True:
                chunk = response.read(1024*1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > release.size or count > MAX_INSTALLER:
                    raise ValueError(_tr('Instalador maior que o esperado'))
                output.write(chunk)
                digest.update(chunk)
                progress(count/release.size)
        if count != release.size or digest.hexdigest() != release.digest:
            raise ValueError(_tr('O instalador falhou na verificação SHA-256'))
        with partial.open('rb') as source:
            if source.read(2) != b'MZ':
                raise ValueError(_tr('Instalador Windows inválido'))
        partial.replace(target)
        return target
    finally:
        partial.unlink(missing_ok=True)


def overlay_running():
    import ctypes
    from ctypes import wintypes
    from src.live.identity import INSTANCE_MUTEX, LEGACY_INSTANCE_MUTEX
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenMutexW.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.OpenMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for name in (INSTANCE_MUTEX,LEGACY_INSTANCE_MUTEX):
        handle = kernel.OpenMutexW(0x100000,False,name)
        if handle:
            kernel.CloseHandle(handle)
            return True
        if ctypes.get_last_error() == 5:
            return True
    return False
