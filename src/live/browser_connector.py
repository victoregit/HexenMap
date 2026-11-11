"""Explicit browser-to-app delivery. No network, game capture or account access."""
from __future__ import annotations
from src.live.i18n import tr as _tr
import json
import os
from pathlib import Path
import struct
import sys
import uuid

HOST_NAME = 'com.hexenmap.exporter'
EXTENSION_ID = 'eaginfmeemocboabidkcpjlpnhgglndl'
ORIGIN = f'chrome-extension://{EXTENSION_ID}/'
MAX_BYTES = 16 * 1024 * 1024


def validated_payload(payload):
    from src.live.appsample_import import parse_marker_ids
    if not isinstance(payload, dict) or set(payload) != {'source', 'version', 'markerIds'}:
        raise ValueError(_tr('Formato de exportação inválido'))
    if payload['source'] != 'appsample' or type(payload['version']) is not int or payload['version'] != 1:
        raise ValueError(_tr('Origem ou versão inválida'))
    ids, _ = parse_marker_ids(payload)
    return {'source': 'appsample', 'version': 1, 'markerIds': list(ids)}


def read_exact(stream, size):
    parts = bytearray()
    while len(parts) < size:
        chunk = stream.read(size - len(parts))
        if not chunk:
            raise ValueError(_tr('Mensagem incompleta'))
        parts.extend(chunk)
    return bytes(parts)


def read_message(stream):
    size, = struct.unpack('<I', read_exact(stream, 4))
    if not 0 < size <= MAX_BYTES:
        raise ValueError(_tr('Mensagem acima do limite'))
    return validated_payload(json.loads(read_exact(stream, size).decode('utf-8')))


def write_message(stream, payload):
    raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    stream.write(struct.pack('<I', len(raw)) + raw)
    stream.flush()


def queue_import(root, payload):
    from src.live.storage import write_json
    payload = validated_payload(payload)
    inbox = Path(root) / 'userData/browser-imports'
    inbox.mkdir(parents=True, exist_ok=True)
    if len(list(inbox.glob('*.json'))) >= 8:
        raise ValueError(_tr('Há importações aguardando confirmação no aplicativo'))
    path = inbox / (uuid.uuid4().hex + '.json')
    write_json(path, payload)
    return path


def app_running():
    import ctypes
    from ctypes import wintypes
    from src.live.identity import INSTANCE_MUTEX
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenMutexW(0x00100000, False, INSTANCE_MUTEX)
    if handle:
        kernel.CloseHandle(handle)
        return True
    # Access denied also means the elevated application's mutex exists.
    return ctypes.get_last_error() == 5


def open_app(root):
    if app_running():
        return
    import ctypes
    exe = Path(root) / 'HexenMap.exe'
    if not exe.is_file():
        raise OSError(_tr('Aplicativo não instalado'))
    shell = ctypes.windll.shell32.ShellExecuteW
    shell.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                     ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
    shell.restype = ctypes.c_void_p
    result = shell(None, 'open', str(exe), None, str(root), 1)
    if not result or result <= 32:
        raise OSError(_tr('A abertura do aplicativo foi cancelada ou bloqueada'))


def serve(origin, source, sink, root, launcher=open_app):
    path = None
    try:
        if origin not in (ORIGIN, ORIGIN[:-1]):
            raise ValueError(_tr('Extensão não autorizada'))
        payload = read_message(source)
        path = queue_import(root, payload)
        try:
            launcher(root)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        write_message(sink, {'ok': True, 'count': len(payload['markerIds']), 'status': 'queued'})
        return 0
    except Exception:
        # Never send local paths, input data or account fields through errors.
        write_message(sink, {'ok': False, 'error': 'Não foi possível enviar. Confira o conector e abra o Hexen Map.'})
        return 1


def register_connector(root):
    import winreg
    from src.live.storage import write_json
    root = Path(root).resolve()
    host = root / 'HexenMapBridge.exe'
    if not host.is_file():
        raise FileNotFoundError(_tr('HexenMapBridge.exe não encontrado junto do aplicativo'))
    manifest = root / 'userData/browser-connector/host.json'
    write_json(manifest, {'name': HOST_NAME, 'description': 'Hexen Map — importação com prévia',
                        'path': str(host), 'type': 'stdio', 'allowed_origins': [ORIGIN]})
    for browser in ('Google\\Chrome', 'Microsoft\\Edge'):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f'Software\\{browser}\\NativeMessagingHosts\\{HOST_NAME}',
                                0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(manifest))
    return manifest


def main():
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    return serve(sys.argv[1] if len(sys.argv) > 1 else '', sys.stdin.buffer, sys.stdout.buffer, root)


if __name__ == '__main__':
    raise SystemExit(_tr(main()))
