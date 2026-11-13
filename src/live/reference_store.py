"""Bounded reference residency. Original rasters are immutable, derived indices disposable."""
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading

import cv2
import numpy as np
from PIL import Image

from src.live.reference import ReferenceUnavailable, ReferenceCancelled, Terrain
from src.live.vision import TerrainMatcher

# 1536 stays below the cold SIFT workspace peak; the format permits at most 2048.
TILE_SIDE=1536
OVERLAP=128
CACHE_BYTES=256*1024**2
INDEX_VERSION=1
SIFT_FEATURES=20000


def check_cancel(cancelled):
    if cancelled():raise ReferenceCancelled('Seleção substituída')


def checked_path(directory,entry):
    path=(directory/entry['file']).resolve()
    if not path.is_relative_to(directory.resolve()):raise ReferenceUnavailable('Referência fora do pacote')
    return path


@dataclass(frozen=True,eq=False)
class Raster:
    path: Path
    digest: str
    matrix: np.ndarray
    width: int
    height: int
    surface: str
    pack_index: int
    map_compatible: bool=False


@dataclass(frozen=True,eq=False)
class Block:
    raster: Raster
    box: tuple
    scale: float=1.

    @property
    def matrix(self):
        result=self.raster.matrix.copy()
        result[:,2]-=self.box[:2]
        return result*self.scale

    @property
    def key(self):
        k=getattr(self,'_cached_key',None)
        if k is None:
            payload=(INDEX_VERSION,cv2.__version__,SIFT_FEATURES,self.raster.digest,str(self.raster.path),self.raster.matrix.tolist(),self.raster.pack_index,self.box,self.scale)
            k=hashlib.sha256(repr(payload).encode()).hexdigest()
            object.__setattr__(self,'_cached_key',k)
        return k

    def distance(self,point):
        if point is None:return math.inf
        x,y=self.raster.matrix@np.array([*point,1.])
        a,b,c,d=self.box
        return math.hypot(max(0,a-x,x-c),max(0,b-y,y-d))/np.linalg.norm(self.raster.matrix[:,0])


@dataclass
class PackSpec:
    map_ui: np.ndarray
    gameplay_ui: np.ndarray
    map_ui_roi: tuple
    gameplay_ui_roi: tuple
    region_id: str
    map_id: str
    layer_id: str
    coordinate_system: str
    rasters: tuple


def read_spec(directory,region_id,map_id,layer_id,coordinate_system,pack_index=0):
    directory=Path(directory)
    try:
        data=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        if (data['region']!=region_id or data.get('map_id','teyvat')!=map_id
                or layer_id and data['layer']!=layer_id or data['coordinate_system']!=coordinate_system):
            raise ValueError('Referência incompatível com a seleção')
        if region_id=='appsample' and not data.get('source','').startswith('https://game-cdn.appsample.com/gim/'):
            raise ValueError('Origem visual AppSample não qualificada')
        if not all(data.get('permission',{}).get(k) for k in ('usage','evidence')):
            raise ValueError('Falta origem/permissão das referências')
        def ui(name):
            entry=data[name];raw=checked_path(directory,entry).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Template alterado')
            image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
            roi=tuple(float(v) for v in entry['roi'])
            if image is None or len(roi)!=4 or not all(0<=v<=1 for v in roi) or min(roi[2:])<=0 or roi[0]+roi[2]>1 or roi[1]+roi[3]>1:
                raise ValueError('Template/ROI inválido')
            return image,roi
        rasters=[]
        for entry in (dict(data['terrain'],world_to_image=data['world_to_image']),*data.get('extra_terrain',())):
            path=checked_path(directory,entry)
            matrix=np.asarray(entry['world_to_image'],dtype=np.float64)
            if matrix.shape!=(2,3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix[:,:2]))<1e-10:
                raise ValueError('Coordenadas de referência inválidas')
            with Image.open(path) as image:width,height=image.size
            if min(width,height)<12:raise ValueError('Imagem de referência inválida')
            rasters.append(Raster(path,entry['sha256'],matrix,width,height,'minimap' if entry.get('surface')=='minimap' else 'map',pack_index,entry.get('map_compatible') is True))
        map_ui,map_roi=ui('map_ui');game_ui,game_roi=ui('gameplay_ui')
        return PackSpec(map_ui,game_ui,map_roi,game_roi,region_id,map_id,data['layer'],coordinate_system,tuple(rasters))
    except (KeyError,TypeError,ValueError,OSError) as exc:
        raise ReferenceUnavailable(f'Pacote de referência inválido: {exc}') from exc


def blocks(raster,scale=1.):
    # Resampled fallbacks are partitioned before allocation as well.
    side=int(TILE_SIDE/scale);step=side-int(OVERLAP/scale)
    def starts(length):
        result=[0]
        while result[-1]+side<length:result.append(result[-1]+step)
        return result
    for y in starts(raster.height):
        for x in starts(raster.width):
            yield Block(raster,(x,y,min(raster.width,x+side),min(raster.height,y+side)),scale)



class FeatureCache:
    def __init__(self,directory,cancelled=lambda:False):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.cancelled=cancelled;self.verified=set();self.build_lock=threading.Lock()
        self.builds=0;self.hits=0

    def verify(self,raster):
        key=(raster.path,raster.digest,raster.path.stat().st_mtime_ns,raster.path.stat().st_size)
        if key not in self.verified:
            digest=hashlib.sha256()
            with raster.path.open('rb') as source:
                while chunk:=source.read(1024*1024):
                    check_cancel(self.cancelled);digest.update(chunk)
            if digest.hexdigest()!=raster.digest:raise ReferenceUnavailable('Referência alterada: '+raster.path.name)
            self.verified.add(key)

    def read(self,key,columns=128,dtype=np.float32):
        try:
            with np.load(self.directory/(key+'.npz'),allow_pickle=False) as data:
                points=data['points'];descriptors=data['descriptors']
            if points.ndim!=2 or points.shape[1]!=2 or descriptors.shape!=(len(points),columns) or len(points)>100000 or not np.isfinite(points).all() or not np.isfinite(descriptors).all():return None
            self.hits+=1;return points.astype(np.float32,copy=False),descriptors.astype(dtype,copy=False)
        except (OSError,ValueError,KeyError,EOFError,TypeError):return None

    def write(self,key,points,descriptors):
        fd,name=tempfile.mkstemp(prefix=key,suffix='.tmp',dir=self.directory)
        try:
            with os.fdopen(fd,'wb') as file:np.savez(file,points=points,descriptors=descriptors)
            os.replace(name,self.directory/(key+'.npz'))
        finally:
            if os.path.exists(name):os.unlink(name)

    def features(self,block):
        with self.build_lock:
            check_cancel(self.cancelled);self.verify(block.raster)
            value=self.read(block.key)
            if value is not None:return value
            with Image.open(block.raster.path) as source:
                image=source.crop(block.box).convert('L')
                if block.scale!=1:image=image.resize((round(image.width*block.scale),round(image.height*block.scale)),Image.Resampling.BICUBIC)
            source.close()
            array=np.asarray(image)
            sift=cv2.SIFT_create(nfeatures=SIFT_FEATURES,contrastThreshold=.025)
            keys,descriptors=sift.detectAndCompute(array,None)
            check_cancel(self.cancelled)
            points=np.float32([k.pt for k in keys]).reshape(-1,2)
            if descriptors is None:descriptors=np.empty((0,128),np.float32)
            self.write(block.key,points,descriptors);self.builds+=1
            return points,descriptors

    def coarse(self,raster,budget):
        key=hashlib.sha256(repr((INDEX_VERSION,cv2.__version__,'coarse',raster.digest,budget)).encode()).hexdigest()
        self.verify(raster);value=self.read(key)
        if value is not None:return value
        check_cancel(self.cancelled)
        with Image.open(raster.path) as source:
            image=source.convert('L');scale=min(1.,1536/max(image.size))
            if scale!=1:image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
        source.close()
        keys,descriptors=cv2.SIFT_create(nfeatures=budget,contrastThreshold=.025).detectAndCompute(np.asarray(image),None)
        points=np.float32([k.pt for k in keys]).reshape(-1,2)/scale
        if descriptors is None:descriptors=np.empty((0,128),np.float32)
        check_cancel(self.cancelled);self.write(key,points,descriptors)
        return points,descriptors



class IndexedMatcher(TerrainMatcher):
    def __init__(self,block,points,descriptors):
        if len(points)<20:raise ValueError('Bloco sem detalhes suficientes')
        self.block=block;self.points=points;self.descriptors=descriptors
        self.terrain=Terrain(np.empty((0,0),np.uint8),block.matrix,str(block.raster.path))
        self.sift=None
        self.matcher=cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=96))
        self.matcher.add([descriptors]);self.matcher.train()
        # Include conservative native copies/tree overhead, not just the ndarray.
        self.bytes=descriptors.nbytes*4+points.nbytes+2*1024**2

    def close(self):
        if hasattr(self,'matcher') and self.matcher is not None:
            try:self.matcher.clear()
            except Exception:pass
            self.matcher=None
        self.points=None
        self.descriptors=None
        self.sift=None


class ReferenceStore:
    def __init__(self,features,mode='light'):
        self.features=features;self.mode=mode;self.cache=OrderedDict();self.bytes=0;self.evictions=0
        self.protected_key=None
        import psutil
        self.global_limit=min(2*1024**3,int(psutil.virtual_memory().available*.4))

    def get(self,block):
        check_cancel(self.features.cancelled)
        if block.key in self.cache:
            self.cache.move_to_end(block.key);return self.cache[block.key]
        # Evict before constructing an index so old/new native allocations do not overlap.
        if self.mode=='light':
            while self.cache and (len(self.cache)>=2 or self.bytes> CACHE_BYTES-48*1024**2):self.evict()
        if self.mode=='global' and self.bytes+48*1024**2>self.global_limit:raise MemoryError('Memória insuficiente para cobertura global')
        points,descriptors=self.features.features(block)
        value=IndexedMatcher(block,points,descriptors)
        if self.mode=='light':
            while self.cache and self.bytes+value.bytes>CACHE_BYTES:self.evict()
            if value.bytes>CACHE_BYTES:raise MemoryError('Índice excede o orçamento leve')
        self.cache[block.key]=value;self.bytes+=value.bytes
        return value

    def evict(self):
        # Failed search candidates must not displace the last verified terrain.
        # Still evict it when it alone exceeds the available byte budget.
        key=next((key for key in self.cache if key!=self.protected_key),next(iter(self.cache)))
        value=self.cache.pop(key);self.bytes-=value.bytes;self.evictions+=1
        if hasattr(value,'close'):value.close()

    def close(self):
        for val in self.cache.values():
            if hasattr(val,'close'):val.close()
        self.cache.clear();self.bytes=0;self.protected_key=None

    def diagnostics(self):
        return {'mode':self.mode,'resident_blocks':len(self.cache),'reference_bytes_estimated':self.bytes,
                'evictions':self.evictions,'disk_hits':self.features.hits,'indices_built':self.features.builds}
