"""Compact settings sections; technical controls remain available on demand."""
import tkinter as tk
from tkinter import ttk
from src.live.storage import HOTKEY_OPTIONS


def build_settings(app, parent, *, bg, muted):
    canvas=tk.Canvas(parent,bg=bg,highlightthickness=0)
    scrollbar=ttk.Scrollbar(parent,orient='vertical',command=canvas.yview)
    scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    body=ttk.Frame(canvas);window=canvas.create_window(0,0,window=body,anchor='nw')
    def body_changed(event):
        bounds=canvas.bbox('all')
        if bounds!=getattr(canvas,'_content_bounds',None):
            canvas._content_bounds=bounds;canvas.configure(scrollregion=bounds)
    def canvas_changed(event):
        if event.width!=getattr(canvas,'_content_width',None):
            canvas._content_width=event.width;canvas.itemconfigure(window,width=event.width)
    body.bind('<Configure>',body_changed)
    canvas.bind('<Configure>',canvas_changed)
    app.settings_sections=[]

    def note(container,text):
        label=ttk.Label(container,text=text,wraplength=280,foreground=muted,justify='left')
        label.pack(fill='x',pady=(2,8))
        def wrap(event):
            width=max(160,event.width)
            if int(label.cget('wraplength'))!=width:label.configure(wraplength=width)
        label.bind('<Configure>',wrap)

    def section(title):
        frame=ttk.Frame(body);frame.pack(fill='x',pady=2)
        content=ttk.Frame(frame,padding=(8,6,8,8))
        state={'open':False,'body':content,'title':title}
        def toggle():
            opening=not state['open']
            for item in app.settings_sections:
                if item['open']:
                    item['open']=False;item['body'].pack_forget();item['button'].configure(text='▸ '+item['title'])
            if opening:
                state['open']=True;content.pack(fill='x');button.configure(text='▾ '+state['title'])
            canvas.yview_moveto(0)
        button=ttk.Button(frame,text='▸ '+title,style='Section.TButton',command=toggle)
        button.pack(fill='x');state['button']=button;app.settings_sections.append(state)
        content.section_state=state
        return content

    def title_for(content,title):
        state=content.section_state;state['title']=title
        state['button'].configure(text=('▾ ' if state['open'] else '▸ ')+title)

    appearance=section('Painel e compartilhamento')
    app.panel_scale_var=tk.StringVar(value=str(app.settings.get('panel',{}).get('scale',100))+'%')
    ttk.Label(appearance,text='Tamanho dos textos e controles').pack(anchor='w')
    scale_box=ttk.Combobox(appearance,textvariable=app.panel_scale_var,values=['100%','125%','150%'],state='readonly',width=10)
    scale_box.pack(fill='x',pady=3);scale_box.bind('<<ComboboxSelected>>',app.change_panel_scale)
    ttk.Button(appearance,text='Restaurar tamanho padrão',command=app.reset_panel_size).pack(fill='x',pady=3)
    note(appearance,'Puxe as bordas da janela para aumentar o painel. No modo fixado, use a alça no canto inferior direito. Tamanho e escala são salvos.')
    ttk.Label(appearance,text='Mapa e camada do rastreamento').pack(anchor='w',pady=(6,0))
    app.build_scope_controls(appearance)
    app.panel_mode_button=ttk.Button(appearance,text=app.panel_mode_label(),command=app.toggle_panel_mode)
    app.panel_mode_button.pack(fill='x',pady=3)
    note(appearance,'Janela independente: mova o painel para fora da área do jogo. Fixado ao jogo: acompanha o foco do Genshin.')
    app.capture_button=ttk.Button(appearance,text=app.capture_label(),command=app.toggle_capture_visibility)
    app.capture_button.pack(fill='x',pady=3)
    note(appearance,'Controla se os ícones aparecem no compartilhamento de tela. Não desliga o reconhecimento. Para incluir os pins, compartilhe a tela inteira; só a janela do jogo pode não incluí-los.')

    automark=section('AutoMark · Beta')
    app.automark_var=tk.BooleanVar(value=app.settings.get('automark',False))
    app.automark_toggle=ttk.Checkbutton(automark,text='Marcar baús automaticamente',variable=app.automark_var,command=app.change_automark)
    app.automark_toggle.pack(anchor='w',pady=3)
    if not app.chest_signals.ready:app.automark_toggle.state(['disabled'])
    def automark_summary(*args):
        state=('ativo' if app.automark_var.get() else 'desligado') if app.chest_signals.ready else 'indisponível'
        title_for(automark,'AutoMark · Beta · '+state)
    app.automark_var.trace_add('write',automark_summary);automark_summary()
    note(automark,'Reconhece a abertura e as recompensas e confirma somente um baú próximo sem ambiguidade. Use Desfazer se precisar corrigir uma coleta.')
    if not app.chest_signals.ready:
        note(automark,'Indisponível nesta instalação: faltam referências visuais qualificadas. Consulte Diagnóstico para ver o motivo.')

    if app.catalogs.appsample_available:
        imports=section('Coletados do AppSample')
        note(imports,'Traga os itens que você já marcou no site. A prévia pede confirmação e a mesclagem preserva seu progresso com backup.')
        ttk.Button(imports,text='Abrir pasta da extensão…',command=app.open_exporter_folder).pack(fill='x',pady=3)
        note(imports,'Instalação manual: no Chrome ou Edge, abra Extensões, ative Modo do desenvolvedor e use Carregar sem compactação. Selecione a pasta aberta pelo botão acima. Não mova nem apague essa pasta após instalar.')
        ttk.Button(imports,text='Importar arquivo de coletados…',command=app.import_appsample_progress).pack(fill='x',pady=3)
        ttk.Button(imports,text='Ativar conexão com a extensão…',command=app.install_browser_connector).pack(fill='x',pady=3)
        note(imports,'Ative a conexão uma vez para usar Enviar ao Hexen Map na extensão. Sem conexão, você pode baixar o JSON e importar o arquivo.')
        ttk.Button(imports,text='Como trazer meus coletados?',style='Quiet.TButton',command=app.show_appsample_export).pack(fill='x',pady=3)

    performance=section('Desempenho')
    app.performance_var=tk.StringVar(value='Global' if app.settings.get('performance_mode')=='global' else 'Leve')
    app.performance_var.trace_add('write',lambda *args:title_for(performance,'Desempenho · '+app.performance_var.get()))
    title_for(performance,'Desempenho · '+app.performance_var.get())
    box=ttk.Combobox(performance,textvariable=app.performance_var,values=['Leve','Global'],state='readonly')
    box.pack(fill='x',pady=3);box.bind('<<ComboboxSelected>>',app.change_performance_mode)
    note(performance,'Leve · recomendado: carrega o entorno conforme necessário. Após viagens longas, pode levar um instante para recuperar a posição.')
    note(performance,'Global: prepara o mapa e as camadas selecionadas. Consome mais memória e pode aumentar o uso de CPU e o tempo de carregamento. A mudança é salva automaticamente.')

    shortcuts=section('Atalhos')
    app.key_vars={}
    for action,label in (('panel','Abrir / recolher painel'),('visibility','Mostrar / ocultar ícones'),('collect','Confirmar coleta próxima'),('undo','Desfazer coleta')):
        row=ttk.Frame(shortcuts);row.pack(fill='x',pady=4)
        ttk.Label(row,text=label).pack(side='left')
        var=tk.StringVar(value=app.settings['hotkeys'][action]);app.key_vars[action]=var
        ttk.Combobox(row,textvariable=var,values=HOTKEY_OPTIONS,state='readonly',width=13).pack(side='right')
    ttk.Button(shortcuts,text='Salvar atalhos',command=app.save_keys).pack(fill='x',pady=6)
    note(shortcuts,'Funcionam com o jogo em foco. Ctrl + clique abre o cartão de coleta; segurar Ctrl revela os itens já pegos em cinza.')

    diagnostics=section('Diagnóstico · avançado')
    ttk.Button(diagnostics,text='Copiar diagnóstico para suporte',command=app.copy_diagnostics).pack(fill='x',pady=3)
    note(diagnostics,'Use estas opções se os marcadores não reaparecerem após voltar ao jogo.')
    ttk.Button(diagnostics,text='Recarregar reconhecimento',command=app.reload_reference).pack(fill='x',pady=3)
    note(diagnostics,'Reinicia a localização visual sem alterar coletas ou filtros.')
    ttk.Label(diagnostics,textvariable=app.status,wraplength=280,foreground=muted).pack(fill='x',pady=5)
    note(diagnostics,'AutoMark: '+app.chest_signals.reason)
    note(diagnostics,'Os prazos conhecidos de reset usam o servidor América. Recursos sem regra confirmada não recebem um temporizador genérico.')
    ttk.Button(diagnostics,text='Exportação manual (avançado)…',style='Quiet.TButton',command=lambda:app.show_appsample_export(manual=True)).pack(fill='x',pady=3)
    ttk.Separator(body).pack(fill='x',pady=(12,6))
    ttk.Button(body,text='Encerrar Hexen Map',style='Quiet.TButton',command=app.close).pack(fill='x',pady=(0,8))

    def wheel(event):
        # Do not scroll a short collapsed page into an empty region.
        bounds=canvas.bbox('all')
        if bounds and bounds[3]>canvas.winfo_height():canvas.yview_scroll(-int(event.delta/120),'units')
        return 'break'
    def bind_scroll(widget):
        widget.bind('<MouseWheel>',wheel)
        for child in widget.winfo_children():bind_scroll(child)
    bind_scroll(canvas)
    return canvas
