"""Latest request wins; no Tk calls, global catalog mutation or personal writes."""
from src.live.i18n import tr as _tr
from collections import OrderedDict
import queue
import threading
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path


def read_package(community, identifier, personal_root=None):
    from src.live.regions import RegionalCatalog
    return RegionalCatalog(Path(community),Path(personal_root) if personal_root else None).load_package(identifier)


class ProcessCatalogSource:
    """JSON decoding and catalog validation cannot hold Tk's Python interpreter."""
    def __init__(self, community, personal_root=None):
        self.community=str(community)
        self.personal_root=str(personal_root) if personal_root else None
        self.pool=None;self.timer=None;self.lock=threading.Lock();self.closed=False;self.generation=0;self.active=0

    def __call__(self, identifier):
        with self.lock:
            if self.closed:raise RuntimeError(_tr('Carregador encerrado'))
            self.generation+=1;generation=self.generation
            if self.timer:self.timer.cancel();self.timer=None
            if self.pool is None:self.pool=ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn'))
            self.active+=1
            future=self.pool.submit(read_package,self.community,identifier,self.personal_root)
        try:return future.result()
        finally:
            with self.lock:
                self.active-=1
                if not self.closed and generation==self.generation:
                    self.timer=threading.Timer(5.,self._idle,args=(generation,));self.timer.daemon=True;self.timer.start()

    def _idle(self,generation=None,wait=False):
        with self.lock:
            if self.active:return
            if generation is not None and generation!=self.generation:return
            pool=self.pool;self.pool=None;self.timer=None
        if pool:pool.shutdown(wait=wait,cancel_futures=True)

    def retire_idle(self):
        self._idle(wait=True)

    def close(self):
        with self.lock:
            self.closed=True
            if self.timer:self.timer.cancel();self.timer=None
            pool=self.pool;self.pool=None
        if pool:pool.shutdown(wait=False,cancel_futures=True)



class CatalogLoader:
    def __init__(self, load):
        self.load=load
        self.condition=threading.Condition()
        self.pending=None
        self.generation=0
        self.closed=False
        self.results=queue.Queue()
        self.cache=OrderedDict()
        self.thread=threading.Thread(target=self._run,name='RegionalCatalog',daemon=True)
        self.thread.start()

    def request(self, identifier):
        with self.condition:
            self.generation+=1
            self.pending=(self.generation,identifier)
            self.condition.notify()
            return self.generation

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:self.closed or self.pending is not None)
                if self.closed: return
                generation,identifier=self.pending;self.pending=None
            try:
                value=self.cache.pop(identifier,None)
                if value is None: value=self.load(identifier)
                self.cache[identifier]=value
                while len(self.cache)>1: self.cache.popitem(last=False)
                error=None
            except Exception as exc:
                value=None;error=str(exc)
            with self.condition:
                if not self.closed and generation==self.generation:
                    self.results.put((generation,identifier,value,error))

    def close(self):
        with self.condition:
            self.closed=True;self.pending=None;self.condition.notify_all()
