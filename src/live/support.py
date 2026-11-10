"""User-written reports; no credentials, automatic diagnostics or attachments."""
import json
import queue
import re
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.request import Request,urlopen
from src.live.identity import DISPLAY_NAME,SUPPORT_EMAIL,VERSION
from src.live.theme import BG,SURFACE,TEXT,MUTED,ACCENT,SUCCESS,FONT,place_dialog

ENDPOINT=f'https://formsubmit.co/ajax/{SUPPORT_EMAIL}'
MAX_MESSAGE=5000


def report_payload(email,message):
    email=email.strip();message=message.strip()
    if not message:raise ValueError('Escreva seu feedback ou descreva o problema.')
    if len(message)>MAX_MESSAGE:raise ValueError(f'A mensagem pode ter até {MAX_MESSAGE} caracteres.')
    if email and (len(email)>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email)):
        raise ValueError('Confira o e-mail ou deixe o campo vazio.')
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
        with opener(request,timeout=15) as response:raw=response.read(65537)
        if len(raw)>65536:raise ValueError('Resposta muito grande')
        result=json.loads(raw)
    except (OSError,ValueError) as exc:
        raise RuntimeError('Não foi possível confirmar o envio. Sua mensagem foi mantida; confira a conexão e tente novamente.') from exc
    if isinstance(result,dict) and 'needs activation' in str(result.get('message','')).lower():
        raise RuntimeError('O canal de reports aguarda ativação pelo desenvolvedor. Sua mensagem foi mantida.')
    if not isinstance(result,dict) or result.get('success') not in (True,'true'):
        raise RuntimeError('O serviço não confirmou o envio. Sua mensagem foi mantida; tente novamente mais tarde.')
    return result


class ReportDialog:
    def __init__(self,parent):
        self.parent=parent;self.busy=False;self.sent=False;self.next_send=0
        self.results=queue.Queue();self.poll_job=None
        self.window=tk.Toplevel(parent);window=self.window
        window.withdraw();window.title('Report · Hexen Map');window.configure(bg=BG)
        window.transient(parent);window.resizable(False,False)
        window.attributes('-topmost',bool(parent.attributes('-topmost')))
        body=ttk.Frame(window,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Report e feedback',font=(FONT,12,'bold')).pack(anchor='w')
        ttk.Label(body,text='Conte o que aconteceu ou compartilhe sua ideia.',foreground=MUTED).pack(anchor='w',pady=(4,12))
        ttk.Label(body,text='Seu e-mail (opcional, apenas para responder)').pack(anchor='w')
        self.email=ttk.Entry(body);self.email.pack(fill='x',pady=(4,12))
        ttk.Label(body,text='Mensagem').pack(anchor='w')
        self.message=tk.Text(body,height=7,wrap='word',bg=SURFACE,fg=TEXT,insertbackground=TEXT,
                             relief='flat',font=(FONT,10),padx=8,pady=8,undo=True)
        self.message.pack(fill='both',expand=True,pady=(4,8))
        ttk.Label(body,text='Envio via FormSubmit ao desenvolvedor. Só enviamos o texto,\no e-mail informado e a versão do app.',foreground=MUTED).pack(anchor='w')
        self.status=tk.StringVar()
        self.status_label=ttk.Label(body,textvariable=self.status,foreground=ACCENT,wraplength=360)
        self.status_label.pack(fill='x',pady=(8,4))
        actions=ttk.Frame(body);actions.pack(fill='x',pady=(4,0))
        self.close_button=ttk.Button(actions,text='Cancelar',command=self.close);self.close_button.pack(side='left')
        self.send_button=ttk.Button(actions,text='Enviar',style='Primary.TButton',command=self.submit)
        self.send_button.pack(side='right')
        window.protocol('WM_DELETE_WINDOW',self.close);window.bind('<Escape>',lambda event:self.close())
        window.update_idletasks();scale=getattr(parent,'_lunar_signature',1.)
        place_dialog(window,parent,(420,max(400,window.winfo_reqheight()/scale)))
        window.deiconify();window.lift();self.message.focus_set()

    def submit(self):
        if self.busy or self.sent:return
        email=self.email.get();message=self.message.get('1.0','end-1c')
        try:report_payload(email,message)
        except ValueError as exc:self.status.set(str(exc));return
        if time.monotonic()<self.next_send:
            self.status.set('Aguarde alguns segundos antes de tentar novamente.');return
        self.next_send=time.monotonic()+20;self.busy=True
        self.status.set('Enviando…');self.send_button.state(['disabled']);self.close_button.state(['disabled'])
        self.email.state(['disabled']);self.message.configure(state='disabled')
        def worker():
            try:send_report(email,message);self.results.put(None)
            except Exception as exc:self.results.put(str(exc) if isinstance(exc,RuntimeError) else 'Falha no envio. Sua mensagem foi mantida.')
        threading.Thread(target=worker,daemon=True,name='HexenMapReport').start()
        self.poll_job=self.window.after(80,self.poll)

    def poll(self):
        self.poll_job=None
        try:error=self.results.get_nowait()
        except queue.Empty:
            self.poll_job=self.window.after(80,self.poll);return
        self.busy=False;self.close_button.state(['!disabled'])
        if error:
            self.status.set(error);self.send_button.state(['!disabled'])
            self.email.state(['!disabled']);self.message.configure(state='normal')
        else:
            self.sent=True;self.status_label.configure(foreground=SUCCESS)
            self.status.set('Mensagem enviada. Obrigado pelo feedback!');self.close_button.configure(text='Fechar')

    def close(self):
        if self.busy:self.status.set('Aguarde a confirmação do envio…');return
        if self.poll_job is not None:self.window.after_cancel(self.poll_job)
        self.window.destroy()


def report_problem(parent):
    existing=getattr(parent,'_report_dialog',None)
    if existing is not None and existing.window.winfo_exists():
        existing.window.deiconify();existing.window.lift();return existing
    parent._report_dialog=ReportDialog(parent)
    return parent._report_dialog
