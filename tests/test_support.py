import io
import json
import threading
import time
import socket
import ssl
from urllib.parse import parse_qs,urlsplit
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
        assert request.method=='POST' and timeout==8
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


def test_report_deadline_keeps_draft_and_late_reply_cannot_confirm_new_attempt():
    from scripts.preview_lunar import PreviewApp
    app=PreviewApp();root=app.root;root.attributes('-alpha',0);root.deiconify();root.update()
    dialog=report_problem(root);dialog.message.insert('1.0','Falha de atualização')
    started=threading.Event();release=threading.Event()
    def slow(*args):
        started.set();release.wait(3)
    try:
        with patch('src.live.support.send_report',slow):
            dialog.submit();assert started.wait(1)
            abandoned=dialog.results
            dialog.window.after_cancel(dialog.poll_job);dialog.deadline=0;dialog.poll()
            assert not dialog.busy and not dialog.sent
            assert '10 segundos' in dialog.status.get()
            assert dialog.message.get('1.0','end-1c')=='Falha de atualização'
            dialog.next_send=0;started.clear();dialog.submit();assert started.wait(1)
            assert dialog.results is not abandoned
            abandoned.put(None)
            dialog.window.after_cancel(dialog.poll_job);dialog.poll()
            assert dialog.busy and not dialog.sent
    finally:
        release.set();app.compact.stop();root.destroy()


def test_email_fallback_opens_a_draft_without_claiming_it_was_sent():
    from unittest.mock import Mock
    from src.live.support import ReportDialog
    dialog=ReportDialog.__new__(ReportDialog)
    dialog.busy=False;dialog.sent=False
    dialog.message=Mock();dialog.message.get.return_value='Bug com acentuação & detalhes'
    dialog.email=Mock();dialog.email.get.return_value='player@example.com'
    dialog.status=Mock()
    with patch('src.live.support.webbrowser.open',return_value=True) as opened:
        dialog.open_email()
    url=urlsplit(opened.call_args.args[0]);query=parse_qs(url.query)
    assert url.scheme=='mailto'
    assert 'Bug com acentuação & detalhes' in query['body'][0]
    assert 'player@example.com' in query['body'][0]
    assert not dialog.sent and 'Conclua o envio' in dialog.status.set.call_args.args[0]
