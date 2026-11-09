import io
import json
from pathlib import Path
import struct

import pytest
from src.live.browser_connector import (ORIGIN,MAX_BYTES,EXTENSION_ID,read_message,
    serve,validated_payload,queue_import)


def frame(payload):
    raw=json.dumps(payload).encode();return io.BytesIO(struct.pack('<I',len(raw))+raw)


def payload():return {'source':'appsample','version':1,'markerIds':['001','1','001']}


def response(sink):
    sink.seek(0);size,=struct.unpack('<I',sink.read(4));return json.loads(sink.read(size))


def test_message_exact_ids_and_partial_pipe():
    class Slow(io.BytesIO):
        def read(self,size):return super().read(min(size,2))
    assert read_message(Slow(frame(payload()).getvalue()))['markerIds']==['001','1']


@pytest.mark.parametrize('data',[{'source':'other','version':1,'markerIds':['1']},
    {'source':'appsample','version':True,'markerIds':[]},dict(payload(),command='run'),
    {'source':'appsample','version':1,'markerIds':[1]}])
def test_reject_invalid_contract(data):
    with pytest.raises(ValueError):validated_payload(data)


def test_limits_and_truncated_pipe():
    for data in (b'abc',struct.pack('<I',MAX_BYTES+1),struct.pack('<I',20)+b'{}'):
        with pytest.raises(ValueError):read_message(io.BytesIO(data))


def test_delivery_is_queued_not_applied_and_origin_checked(tmp_path):
    called=[];sink=io.BytesIO()
    assert serve(ORIGIN,frame(payload()),sink,tmp_path,launcher=called.append)==0
    assert response(sink)=={'ok':True,'count':2,'status':'queued'}
    queued=list((tmp_path/'userData/browser-imports').glob('*.json'))
    assert len(queued)==1 and json.loads(queued[0].read_text())['markerIds']==['001','1']
    assert not (tmp_path/'userData/progress.json').exists()
    assert called==[tmp_path]
    sink=io.BytesIO();assert serve('chrome-extension://foreign/',frame(payload()),sink,tmp_path,launcher=called.append)==1
    assert response(sink)['ok'] is False and len(called)==1


def test_cancelled_launch_removes_pending_delivery(tmp_path):
    def fail(_):raise OSError('private-path')
    sink=io.BytesIO();assert serve(ORIGIN,frame(payload()),sink,tmp_path,launcher=fail)==1
    assert not list((tmp_path/'userData/browser-imports').glob('*.json'))
    assert 'private-path' not in sink.getvalue().decode('utf8',errors='ignore')


def test_bounded_pending_inbox(tmp_path):
    for _ in range(8):queue_import(tmp_path,payload())
    with pytest.raises(ValueError):queue_import(tmp_path,payload())


def test_manifest_key_identity_and_permissions():
    import base64,hashlib
    manifest=json.loads((Path(__file__).resolve().parents[1]/'extensions/hexen-map-exporter/manifest.json').read_text())
    digest=hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32]
    assert ''.join(chr(97+int(h,16)) for h in digest)==EXTENSION_ID
    assert manifest['permissions']==['nativeMessaging']

def test_registration_is_user_scoped_and_allows_only_exporter(tmp_path,monkeypatch):
    import sys
    from types import SimpleNamespace
    from src.live.browser_connector import register_connector,HOST_NAME
    writes=[]
    class Key:
        def __init__(self,path):self.path=path
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def create(hive,path,*args):
        assert hive=='user';return Key(path)
    fake=SimpleNamespace(HKEY_CURRENT_USER='user',KEY_SET_VALUE=2,REG_SZ=1,
        CreateKeyEx=create,SetValueEx=lambda key,name,reserved,kind,value:writes.append((key.path,value)))
    monkeypatch.setitem(sys.modules,'winreg',fake)
    (tmp_path/'HexenMapBridge.exe').write_bytes(b'test-fixture')
    manifest=register_connector(tmp_path);data=json.loads(manifest.read_text())
    assert data['allowed_origins']==[ORIGIN] and data['type']=='stdio'
    assert data['path']==str((tmp_path/'HexenMapBridge.exe').resolve())
    assert {p for p,_ in writes}=={f'Software\\Google\\Chrome\\NativeMessagingHosts\\{HOST_NAME}',f'Software\\Microsoft\\Edge\\NativeMessagingHosts\\{HOST_NAME}'}
    assert all(value==str(manifest) for _,value in writes)
