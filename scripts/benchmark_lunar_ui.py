"""Compare UI-only redraw cost on the same catalog, window and selected items."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types
import psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.preview_lunar import PreviewApp


def load_source(name,path,revision):
    source=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT).decode('utf-8')
    module=types.ModuleType(name);sys.modules[name]=module;exec(compile(source,path,'exec'),module.__dict__);return module


def sample(variant,revision):
    cls=PreviewApp
    if variant=='baseline':
        categories=load_source('baseline_categories','src/live/category_browser.py',revision)
        panel=load_source('baseline_panel','src/live/panel.py',revision);panel.CategoryBrowser=categories.CategoryBrowser
        class Baseline(PreviewApp):
            _panel=panel.CompactPanel._panel
        cls=Baseline
    app=cls(screen=(1920,1080));root=app.root;root.attributes('-alpha',0);root.deiconify();root.update()
    canvas=app.category_browser;canvas.collapsed.discard('Baús');canvas.rebuild()
    for _ in range(20):canvas.paint();root.update_idletasks()
    process=psutil.Process();rss=process.memory_info().rss
    durations=[]
    for _ in range(3):
        start=time.process_time()
        for i in range(300):canvas.paint();root.update_idletasks()
        durations.append((time.process_time()-start)/300*1000)
    images=len(getattr(root,'_lunar_images',()))
    print(json.dumps({'variant':variant,'median_cpu_ms_per_redraw':statistics.median(durations),'rss_mib':rss/1024**2,'theme_images':images}))
    app.compact.stop();root.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sample',choices=['baseline','lunar']);parser.add_argument('--baseline',default='6edf222');args=parser.parse_args()
    if args.sample:sample(args.sample,args.baseline)
    else:
        results=[]
        for case in ['baseline','lunar']:
            result=subprocess.run([sys.executable,__file__,'--sample',case,'--baseline',args.baseline],cwd=ROOT,text=True,capture_output=True,check=True)
            results.append(json.loads(result.stdout))
        out=ROOT/'build/lunar-ui-benchmark.json';out.write_text(json.dumps({'baseline':args.baseline,'scope':'UI only; no game frames, capture or recognizer running','results':results},indent=2))
        print(out.read_text())
