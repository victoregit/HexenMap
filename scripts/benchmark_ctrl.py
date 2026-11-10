"""Controlled Tk reveal benchmark; no game, personal progress or input automation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ast,json,subprocess,time,statistics,tkinter as tk
from types import SimpleNamespace
from src.live.presentation import MarkerCanvas
from src.live.marker_art import draw_pin,marker_geometry
from src.live.input_regions import region_data,placement_data,InputRegions


def main():
    source=subprocess.check_output(['git','show','d9c8467:src/live/presentation.py'],text=True,encoding='utf-8')
    old=next(node for node in ast.parse(source).body if isinstance(node,ast.ClassDef) and node.name=='MarkerCanvas')
    namespace={};exec(compile(ast.Module(body=[old],type_ignores=[]),'<baseline>','exec'),namespace)
    root=tk.Tk();root.withdraw();canvas=tk.Canvas(root,width=1920,height=1080);canvas.pack()
    geometry=marker_geometry('common-chest','map',1.)
    pins=[SimpleNamespace(item=SimpleNamespace(id=str(n),category='common-chest'),
                          x=390+(n%40)*28,y=90+(n//40)*28,geometry=geometry) for n in range(1000)]
    results={}
    for name,renderer_type in [('before',namespace['MarkerCanvas']),('after',MarkerCanvas)]:
        samples=[]
        for _ in range(20):
            canvas.delete('all');renderer=renderer_type(canvas,draw_pin)
            renderer.render(pins[:100],lambda _:False)
            start=time.perf_counter();renderer.render(pins,lambda identifier:int(identifier)>=100)
            root.update_idletasks();samples.append((time.perf_counter()-start)*1000)
        results[name]={'median_ms':round(statistics.median(samples),2),'p95_ms':round(max(samples),2)}
    start=time.perf_counter();raw=region_data(box for pin in pins for box in geometry.rectangles(pin.x,pin.y))
    previous_ms=(time.perf_counter()-start)*1000
    start=time.perf_counter();raw=placement_data(tuple((round(p.x),round(p.y),p.geometry) for p in pins))
    results['mask_worker']={'before_ms':round(previous_ms,2),'after_ms':round((time.perf_counter()-start)*1000,2),'bytes':len(raw)}
    firsts=[];callbacks=[];complete=[]
    for repeat in range(20):
        canvas.delete('all');renderer=MarkerCanvas(canvas,draw_pin);builder=InputRegions()
        started=time.perf_counter();first_interactive=None
        try:
            while len(renderer.entries)<len(pins) or first_interactive is None:
                tick=time.perf_counter()
                shown=renderer.render(pins,lambda _:True,budget_ms=6.)
                current=tuple((round(p.x),round(p.y),p.geometry) for p in shown)
                ready=builder.get(current,current)
                callbacks.append((time.perf_counter()-tick)*1000)
                root.update_idletasks()
                if ready is not None and shown and first_interactive is None:first_interactive=(time.perf_counter()-started)*1000
                if time.perf_counter()-started>3:raise RuntimeError('Input preparation stalled')
                time.sleep(.016)
            firsts.append(first_interactive);complete.append((time.perf_counter()-started)*1000)
        finally:builder.close()
    results['bounded_reveal']={'runs':len(firsts),'first_interactive_p95_ms':round(sorted(firsts)[18],2),
        'first_interactive_max_ms':round(max(firsts),2),'all_submitted_median_ms':round(statistics.median(complete),2),
        'max_ui_callback_ms':round(max(callbacks),2),'image_cache':'warm; new Canvas entries each run'}
    root.destroy()
    report={'pins':len(pins),'scope':'Tk submission and pure mask build; no monitor latency or game capture','results':results}
    path=Path('build/ctrl-benchmark.json');path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
