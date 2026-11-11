import json
from types import SimpleNamespace
from src.live.desktop import DesktopApp


def test_copy_diagnostics_reports_actual_client_and_empty_selection_without_progress_or_images():
    app=DesktopApp.__new__(DesktopApp);copied=[]
    rect=SimpleNamespace(is_found=True,hwnd=1,x=0,y=0,width=1904,height=1161)
    app.native=SimpleNamespace(game=lambda:rect,dpi_scale=lambda _:1.25,foreground=lambda _:False,
                              desktop_bounds=lambda:(0,0,1920,1200))
    app.root=SimpleNamespace(clipboard_clear=lambda:None,clipboard_append=copied.append)
    app.session=SimpleNamespace(observation=SimpleNamespace(surface='hidden',reason='Aguardando',confidence=0.),
        selected=set(),hidden=False,map_id='as-map-2',layer_id='surface')
    app.settings={'automark':False};app.reference_error='';app.overlay_error='';app.recognizer=None
    app.capture_quality={'uniforme':True}
    app.chest_signals=SimpleNamespace(ready=True,state='idle',scores={},detected_hud_height=None,reason='prontas')
    app.automark_service=SimpleNamespace(status='disabled')
    app.copy_diagnostics();report=json.loads(copied[0])
    assert report['area_cliente']==[1904,1161] and report['tipos_selecionados']==[]
    assert report['referencias']=='carregando' and not report['automark']['ativado']
    assert 'records' not in copied[0] and 'markerIds' not in copied[0]
