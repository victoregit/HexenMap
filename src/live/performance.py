"""Low-rate process-tree measurements; no screenshots or per-frame disk flushing."""
import json
import os
import sys
import time

import psutil


class PerformanceTelemetry:
    def __init__(self,path):
        self.file=path.open('a',encoding='utf-8');self.last=-1.;self.cpu={}
        self.process=psutil.Process();self.cores=os.cpu_count() or 1
        self.group_root=self.process
        if getattr(sys,'frozen',False):
            try:
                parent=self.process.parent()
                if parent and parent.exe().casefold()==self.process.exe().casefold():self.group_root=parent
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass

    def record(self,recognizer,mode,state,foreground=False):
        now=time.monotonic()
        if now-self.last<1:return
        processes=[self.group_root,*self.group_root.children(recursive=True)]
        rss=private=peak=0;delta=0.;current={}
        for process in processes:
            try:
                memory=process.memory_info();rss+=memory.rss
                private+=process.memory_full_info().uss
                peak+=getattr(memory,'peak_wset',memory.rss)
                cpu=process.cpu_times();current[process.pid]=cpu.user+cpu.system
                if self.last>=0:delta+=max(0,current[process.pid]-self.cpu.get(process.pid,0))
            except (psutil.NoSuchProcess,psutil.AccessDenied):continue
        value={'monotonic_s':round(now,3),'mode':mode,'state':state,'foreground':foreground,'processes':len(current),
               'rss_MiB':round(rss/1024**2,2),'private_working_MiB':round(private/1024**2,2),
               'sum_process_peak_MiB':round(peak/1024**2,2),
               'cpu_percent_machine':round(delta/max(.001,now-self.last)/self.cores*100,2) if self.last>=0 else None}
        if recognizer is not None and hasattr(recognizer,'diagnostics'):value.update(recognizer.diagnostics())
        self.file.write(json.dumps(value)+'\n');self.file.flush();self.last=now;self.cpu=current

    def close(self):self.file.close()
