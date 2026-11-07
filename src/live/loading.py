"""Latest request wins; no Tk calls, global catalog mutation or personal writes."""
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
        self.pool=ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn'))

    def __call__(self, identifier):
        return self.pool.submit(read_package,self.community,identifier,self.personal_root).result()

    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)


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
                while len(self.cache)>2: self.cache.popitem(last=False)
                error=None
            except Exception as exc:
                value=None;error=str(exc)
            with self.condition:
                if not self.closed and generation==self.generation:
                    self.results.put((generation,identifier,value,error))

    def close(self):
        with self.condition:
            self.closed=True;self.pending=None;self.condition.notify_all()
