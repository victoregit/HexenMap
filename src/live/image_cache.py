"""Byte-bounded PIL caches and a Tk cache that never discards images used by widgets."""
from collections import OrderedDict,namedtuple
from functools import wraps
import threading

from PIL import ImageTk


def image_lru(max_bytes,maxsize):
    def decorate(function):
        values=OrderedDict();lock=threading.RLock();used=hits=misses=0
        @wraps(function)
        def call(*args,**kwargs):
            nonlocal used,hits,misses
            key=(args,tuple(sorted(kwargs.items())))
            with lock:
                if key in values:
                    hits+=1;values.move_to_end(key);return values[key][0]
                misses+=1;value=function(*args,**kwargs)
                size=value.width*value.height*len(value.getbands()) if value is not None else 0
                if size>max_bytes:return value
                while values and (used+size>max_bytes or len(values)>=maxsize):
                    _,(_,old_size)=values.popitem(last=False);used-=old_size
                values[key]=(value,size);used+=size
                return value
        def clear():
            nonlocal used,hits,misses
            with lock:values.clear();used=hits=misses=0
        call.cache_clear=clear
        info=namedtuple('ImageCacheInfo','hits misses maxsize currsize bytes')
        call.cache_info=lambda:info(hits,misses,maxsize,len(values),used)
        return call
    return decorate


class PhotoCache:
    def __init__(self,root,budget=8*1024**2):
        self.root=root;self.budget=budget;self.values=OrderedDict();self.bytes=0

    def get(self,key,image,canvas):
        if key in self.values:
            self.values.move_to_end(key);return self.values[key][0]
        photo=ImageTk.PhotoImage(image,master=canvas);size=image.width*image.height*4
        self.values[key]=(photo,size);self.bytes+=size
        if self.bytes>self.budget:self.prune(protect={str(photo)})
        return photo

    def prune(self,force=False,protect=()):
        used=set(protect)
        def visit(widget):
            if widget.winfo_class()=='Canvas':
                for item in widget.find_all():
                    if widget.type(item)=='image':used.add(widget.itemcget(item,'image'))
            for child in widget.winfo_children():visit(child)
        visit(self.root)
        for key,(photo,size) in list(self.values.items()):
            if str(photo) not in used and (force or self.bytes>self.budget):
                del self.values[key];self.bytes-=size


def cached_photo(canvas,key,image):
    root=canvas._root()
    if not hasattr(root,'_hexen_photos'):root._hexen_photos=PhotoCache(root)
    return root._hexen_photos.get(key,image,canvas)
