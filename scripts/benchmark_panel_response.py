"""Controlled UI input cost, with no game capture or user-data writes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import statistics
import time
from types import SimpleNamespace
from scripts.preview_lunar import PreviewApp
from src.live.desktop import DesktopApp


def main():
    # Isolate the old full-catalog poll from the replacement's unchanged-state path.
    items=[SimpleNamespace(id=str(index)) for index in range(200_000)]
    app=SimpleNamespace(session=SimpleNamespace(items=items,pending_ids=set()),pending_order=[])
    def old_poll():return [item for item in app.session.items if item.id in app.session.pending_ids]
    def measure(action,repeats=100):
        samples=[]
        for _ in range(repeats):
            start=time.perf_counter();action();samples.append((time.perf_counter()-start)*1000)
        return round(statistics.median(samples),4)
    poll={'catalog_size':len(items),'before_ms':measure(old_poll),
          'after_ms':measure(lambda:DesktopApp.sync_pending_candidates(app))}
    del items,app
    app=PreviewApp(1.,(1366,768));root=app.root
    root.attributes('-alpha',0);root.deiconify();root.update()
    samples={}
    def run(name,action):
        times=[]
        for _ in range(12):
            start=time.perf_counter();action();root.update()
            times.append((time.perf_counter()-start)*1000)
        samples[name]={'median_ms':round(statistics.median(times),2),'max_ms':round(max(times),2)}
    run('switch_tabs',lambda:(app.show_settings(),root.update(),app.tabs.select(app.explore)))
    run('toggle_settings',lambda:app.settings_sections[0]['button'].invoke())
    app.tabs.select(app.explore);root.update()
    run('toggle_chests',lambda:app.category_browser.activate(next(i for i,r in enumerate(app.category_browser.rows) if r[0]=='group' and r[1]=='Baús'),0))
    app.compact.stop();root.destroy()
    report={'scope':'UI-only simulation, no recognition/capture; warm input timings',
            'pending_poll':poll,'actions':samples}
    path=Path(__file__).resolve().parents[1]/'build/panel-response.json'
    path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
