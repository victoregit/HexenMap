"""User-written reports; no credentials, automatic diagnostics or attachments."""
from src.live.i18n import tr as _tr
import json
import queue
import re
import threading
import time
import socket
import ssl
import webbrowser
import tkinter as tk
from tkinter import ttk
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,quote
from src.live.identity import DISPLAY_NAME,SUPPORT_EMAIL,VERSION
from src.live.theme import BG,SURFACE,TEXT,MUTED,ACCENT,SUCCESS,FONT,place_dialog

ENDPOINT=f'https://formsubmit.co/ajax/{SUPPORT_EMAIL}'
MAX_MESSAGE=5000
NETWORK_TIMEOUT=8
CONFIRMATION_TIMEOUT=10


def transport_error(exc):
    reason=exc.reason if isinstance(exc,URLError) else exc
    if isinstance(exc,HTTPError):
        if exc.code==403:
            return _tr('O serviço bloqueou a conexão (HTTP 403). Use “Enviar por e-mail”.')
        return _tr('O serviço recusou o envio (HTTP {0}). Tente novamente mais tarde.',exc.code)
    if isinstance(reason,ssl.SSLCertVerificationError):
        return _tr('Não foi possível validar o certificado da conexão. Confira a data do Windows e a conexão.')
    if isinstance(reason,(TimeoutError,socket.timeout)):
        return _tr('O serviço demorou para responder. Não foi possível confirmar o envio.')
    if isinstance(reason,socket.gaierror):
        return _tr('Não foi possível localizar o serviço. Confira sua conexão com a internet.')
    if isinstance(exc,ValueError):
        return _tr('O serviço retornou uma resposta inesperada. Tente novamente mais tarde.')
    code=getattr(reason,'winerror',None) or getattr(reason,'errno',None)
    return _tr('Falha de conexão com o serviço')+(_tr(' (código {0})',code) if code else '')+'.'


def report_payload(email,message):
    email=email.strip();message=message.strip()
    if not message:raise ValueError(_tr('Escreva seu feedback ou descreva o problema.'))
    if len(message)>MAX_MESSAGE:raise ValueError(_tr('A mensagem pode ter até {0} caracteres.', MAX_MESSAGE))
    if email and (len(email)>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email)):
        raise ValueError(_tr('Confira o e-mail ou deixe o campo vazio.'))
    data={'_subject':f'[{DISPLAY_NAME} {VERSION}] Report / feedback','_template':'table',
          '_captcha':'false','_url':'https://github.com/victoregit/HexenMap-Releases',
          'aplicativo':DISPLAY_NAME,'versao':VERSION,'mensagem':message}
    if email:data['email']=email;data['_replyto']=email
    return data


def send_report(email,message,opener=urlopen):
    data=report_payload(email,message)
    request=Request(ENDPOINT,data=json.dumps(data,ensure_ascii=False).encode('utf-8'),
                    headers={'Content-Type':'application/json','Accept':'application/json',
                             'User-Agent':f'HexenMap/{VERSION}',
                             'Referer':data['_url']},method='POST')
    try:
        with opener(request,timeout=NETWORK_TIMEOUT) as response:raw=response.read(65537)
        if len(raw)>65536:raise ValueError(_tr('Resposta muito grande'))
        result=json.loads(raw)
    except (OSError,ValueError) as exc:
        raise RuntimeError(_tr(transport_error(exc))+_tr(' Sua mensagem foi mantida.')) from exc
    if isinstance(result,dict) and 'needs activation' in str(result.get('message','')).lower():
        raise RuntimeError(_tr('O canal de reports aguarda ativação pelo desenvolvedor. Sua mensagem foi mantida.'))
    if not isinstance(result,dict) or result.get('success') not in (True,'true'):
        raise RuntimeError(_tr('O serviço não confirmou o envio. Sua mensagem foi mantida; tente novamente mais tarde.'))
    return result


class ReportDialog:
    def __init__(self,parent):
        self.parent=parent;self.busy=False;self.sent=False;self.next_send=0
        self.results=queue.Queue();self.poll_job=None
        self.window=tk.Toplevel(parent);window=self.window
        window.withdraw();window.title(_tr('Report · Hexen Map'));window.configure(bg=BG)
        window.transient(parent);window.resizable(False,False)
        window.attributes('-topmost',bool(parent.attributes('-topmost')))
        body=ttk.Frame(window,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text=_tr('Report e feedback'),font=(FONT,12,'bold')).pack(anchor='w')
        ttk.Label(body,text=_tr('Conte o que aconteceu ou compartilhe sua ideia.'),foreground=MUTED).pack(anchor='w',pady=(4,12))
        ttk.Label(body,text=_tr('Seu e-mail (opcional, apenas para responder)')).pack(anchor='w')
        self.email=ttk.Entry(body);self.email.pack(fill='x',pady=(4,12))
        ttk.Label(body,text=_tr('Mensagem')).pack(anchor='w')
        self.message=tk.Text(body,height=7,wrap='word',bg=SURFACE,fg=TEXT,insertbackground=TEXT,
                             relief='flat',font=(FONT,10),padx=8,pady=8,undo=True)
        self.message.pack(fill='both',expand=True,pady=(4,8))
        ttk.Label(body,text=_tr('Envio via FormSubmit ao desenvolvedor. Só enviamos o texto,\no e-mail informado e a versão do app.'),foreground=MUTED).pack(anchor='w')
        self.status=tk.StringVar()
        self.status_label=ttk.Label(body,textvariable=self.status,foreground=ACCENT,wraplength=360)
        self.status_label.pack(fill='x',pady=(8,4))
        actions=ttk.Frame(body);actions.pack(fill='x',pady=(4,0))
        self.close_button=ttk.Button(actions,text=_tr('Cancelar'),command=self.close);self.close_button.pack(side='left')
        self.send_button=ttk.Button(actions,text=_tr('Enviar'),style='Primary.TButton',command=self.submit)
        self.send_button.pack(side='right')
        self.email_button=ttk.Button(actions,text=_tr('Enviar por e-mail'),command=self.open_email)
        self.email_button.pack(side='right',padx=(0,8))
        window.protocol('WM_DELETE_WINDOW',self.close);window.bind('<Escape>',lambda event:self.close())
        window.update_idletasks();scale=getattr(parent,'_lunar_signature',1.)
        place_dialog(window,parent,(420,max(400,window.winfo_reqheight()/scale)))
        window.deiconify();window.lift();self.message.focus_set()

    def submit(self):
        if self.busy or self.sent:return
        email=self.email.get();message=self.message.get('1.0','end-1c')
        try:report_payload(email,message)
        except ValueError as exc:self.status.set(_tr(str(exc)));return
        if time.monotonic()<self.next_send:
            self.status.set(_tr('Aguarde alguns segundos antes de tentar novamente.'));return
        self.next_send=time.monotonic()+3;self.busy=True
        self.deadline=time.monotonic()+CONFIRMATION_TIMEOUT
        # Each attempt owns its queue: a late reply cannot confirm a newer report.
        self.results=queue.Queue();results=self.results
        self.status.set(_tr('Enviando…'));self.send_button.state(['disabled']);self.close_button.state(['disabled'])
        self.email_button.state(['disabled'])
        self.email.state(['disabled']);self.message.configure(state='disabled')
        def worker():
            try:send_report(email,message);results.put(None)
            except Exception as exc:results.put(str(exc) if isinstance(exc,RuntimeError) else 'Falha no envio. Sua mensagem foi mantida.')
        threading.Thread(target=worker,daemon=True,name='HexenMapReport').start()
        self.poll_job=self.window.after(80,self.poll)

    def poll(self):
        self.poll_job=None
        try:error=self.results.get_nowait()
        except queue.Empty:
            if time.monotonic()<self.deadline:
                self.poll_job=self.window.after(80,self.poll);return
            error=_tr('O serviço não respondeu em 10 segundos. Não foi possível confirmar o envio. Sua mensagem foi mantida; use “Enviar por e-mail”.')
        self.busy=False;self.close_button.state(['!disabled'])
        self.email_button.state(['!disabled'])
        if error:
            self.status.set(_tr(error));self.send_button.state(['!disabled'])
            self.email.state(['!disabled']);self.message.configure(state='normal')
        else:
            self.sent=True
            self.close()

    def open_email(self):
        if self.busy:return
        email=self.email.get();message=self.message.get('1.0','end-1c')
        try:data=report_payload(email,message)
        except ValueError as exc:self.status.set(_tr(str(exc)));return
        body=f'{message.strip()}\n\n{DISPLAY_NAME} {VERSION}'
        if email.strip():body+=f'\nResponder para: {email.strip()}'
        url=f'mailto:{SUPPORT_EMAIL}?'+urlencode({'subject':data['_subject'],'body':body},quote_via=quote)
        try:
            opened=webbrowser.open(url)
        except OSError:
            opened=False
        self.status.set(_tr('Conclua o envio no aplicativo de e-mail que foi aberto. A mensagem continua aqui.') if opened else
                        _tr('Não foi possível abrir o aplicativo de e-mail. Copie sua mensagem e envie para {0}.', SUPPORT_EMAIL))

    def close(self):
        if self.busy:self.status.set(_tr('Aguarde a confirmação do envio…'));return
        if not self.window.winfo_exists():return
        if self.poll_job is not None:self.window.after_cancel(self.poll_job)
        self.window.destroy()


def report_problem(parent):
    existing=getattr(parent,'_report_dialog',None)
    if existing is not None and existing.window.winfo_exists():
        existing.window.deiconify();existing.window.lift();return existing
    parent._report_dialog=ReportDialog(parent)
    return parent._report_dialog
