import io
import json
import threading
import time
import socket
import ssl
from urllib.error import HTTPError,URLError
from unittest.mock import patch

import pytest
from src.live.support import report_payload,send_report,report_problem,transport_error


@pytest.mark.parametrize('error,expected',[
    (HTTPError('https://formsubmit.co',403,'Forbidden',{},None),'HTTP 403'),
    (URLError(ssl.SSLCertVerificationError('certificate verify failed')),'certificado'),
    (URLError(TimeoutError()),'demorou'),
    (URLError(socket.gaierror()),'localizar'),
    (ValueError(),'resposta inesperada'),
])
def test_transport_errors_explain_cause_without_exposing_message(error,expected):
    assert expected in transport_error(error)


def test_report_only_sends_written_fields_and_version():
    data=report_payload('','Uma sugestão de melhoria')
    assert 'email' not in data and '_replyto' not in data
    assert set(data)=={'_subject','_template','_captcha','_url','aplicativo','versao','mensagem'}
    assert report_payload(' pessoa@example.com ',' Olá ')['_replyto']=='pessoa@example.com'


@pytest.mark.parametrize('email,message',[('', '  '),('inválido','Bug'),('a@b.com\r\nBcc:spam@b.com','Bug'),('', 'x'*5001)])
def test_invalid_report_never_starts_network(email,message):
    with pytest.raises(ValueError):send_report(email,message,opener=lambda *a,**k:pytest.fail('network'))


def test_transport_uses_post_json_and_requires_service_acknowledgement():
    def opener(request,timeout):
        assert request.method=='POST' and timeout==15
        assert request.get_header('Referer')=='https://github.com/victoregit/HexenMap-Releases'
        assert json.loads(request.data)['mensagem']=='Mensagem com acentuação'
        return io.BytesIO(b'{"success":"true"}')
    assert send_report('','Mensagem com acentuação',opener)['success']=='true'
    for raw in [b'{"success":false}',b'not json',b'[]',b'x'*65537]:
        with pytest.raises(RuntimeError):send_report('','Bug',lambda *a,**k:io.BytesIO(raw))
    with pytest.raises(RuntimeError,match='ativação'):
        send_report('','Bug',lambda *a,**k:io.BytesIO(b'{"success":"false","message":"This form needs Activation."}'))


def test_dialog_keeps_draft_on_error_and_does_not_block_tk():
    from scripts.preview_lunar import PreviewApp
    app=PreviewApp();root=app.root;root.attributes('-alpha',0);root.deiconify();root.update()
    dialog=report_problem(root)
    assert report_problem(root) is dialog
    dialog.message.insert('1.0','Uma mensagem de teste')
    started=threading.Event();release=threading.Event();calls=[]
    def fail(*args):
        calls.append(args);started.set();release.wait(2);raise RuntimeError('Falha de teste')
    try:
        with patch('src.live.support.send_report',fail):
            dialog.submit();assert started.wait(1)
            dialog.submit();root.update()
            assert dialog.busy and len(calls)==1
            release.set();deadline=time.monotonic()+3
            while dialog.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert not dialog.busy and not dialog.sent
            assert dialog.message.get('1.0','end-1c')=='Uma mensagem de teste'
        dialog.next_send=0
        with patch('src.live.support.send_report',return_value={'success':True}):
            dialog.submit();deadline=time.monotonic()+3
            while dialog.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert dialog.sent
        dialog.close()
    finally:
        release.set();app.compact.stop();root.destroy()
