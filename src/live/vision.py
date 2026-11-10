"""Screen recognition and current-frame SIFT registration, with rejection gates."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
import time

import cv2
import numpy as np

from src.live.reference import ReferencePack, Terrain
from src.live.minimap_glyph import pointer_shape


@dataclass(frozen=True)
class Observation:
    surface: str
    captured_at: float
    world_to_screen: np.ndarray | None = None
    confidence: float = 0.0
    error_px: float = math.inf
    circle: tuple[float, float, float] | None = None
    player: tuple[float, float] | None = None
    reason: str = "Localizando…"
    map_id: str | None = None
    layer_id: str | None = None
    continuity_id: int = 0
    position_uncertainty_px: float = 0.

    def fresh(self, now: float, ttl: float = 0.65) -> bool:
        age = now - self.captured_at
        return (self.surface in {"minimap", "map"} and 0 <= age <= ttl
                and self.world_to_screen is not None and self.confidence >= 0.65
                and np.isfinite(self.world_to_screen).all())


def gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def steady_circle(current,previous):
    """Keep fixed HUD geometry only after a fresh circle independently agrees."""
    if current is not None and previous is not None:
        if math.hypot(current[0]-previous[0],current[1]-previous[1])<=2 and abs(current[2]-previous[2])<=previous[2]*.08:
            return previous
    return current


class TerrainMatcher:
    """Every frame is registered independently, including after a teleport.

    Similarity fitting handles zoom and minimap rotation without interpreting
    player heading as terrain rotation. No stale-transform fallback is used.
    """
    def __init__(self, terrain: Terrain):
        self.terrain = terrain
        budget=min(100000,max(10000,terrain.image.shape[0]*terrain.image.shape[1]//100))
        self.sift = cv2.SIFT_create(nfeatures=budget, contrastThreshold=0.025)
        self.keys, self.descriptors = self.sift.detectAndCompute(gray(terrain.image), None)
        if self.descriptors is None or len(self.keys) < 20:
            raise ValueError("A referência não contém detalhes suficientes para localização")
        self.matcher = cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=96))
        self.matcher.add([self.descriptors])
        self.matcher.train()
        self.points=np.float32([key.pt for key in self.keys])

    def query(self, frame: np.ndarray, mask: np.ndarray | None = None):
        """Extract screen features once, shared by all blocks of this surface."""
        image=frame
        ox=oy=0
        local_mask=mask
        if mask is not None:
            nonzero=cv2.findNonZero(mask)
            if nonzero is None:
                return None
            x,y,w,h=cv2.boundingRect(nonzero)
            ox=max(0,x-12); oy=max(0,y-12)
            x2=min(image.shape[1],x+w+12); y2=min(image.shape[0],y+h+12)
            image=image[oy:y2,ox:x2]
            local_mask=mask[oy:y2,ox:x2]
        factor=getattr(self,'query_scale',1.)
        if factor!=1.:
            image=cv2.resize(image,None,fx=factor,fy=factor,interpolation=cv2.INTER_CUBIC)
            if local_mask is not None:local_mask=cv2.resize(local_mask,None,fx=factor,fy=factor,interpolation=cv2.INTER_NEAREST)
        keys, descriptors = self.sift.detectAndCompute(gray(image), local_mask)
        if factor!=1.:
            for key in keys:key.pt=(key.pt[0]/factor,key.pt[1]/factor)
        if descriptors is None or len(keys) < 14:
            return None
        return keys,descriptors,ox,oy

    def match(self, frame: np.ndarray, mask: np.ndarray | None = None, query=None):
        query=self.query(frame,mask) if query is None else query
        if query is None:return None
        keys,descriptors,ox,oy=query
        pairs = self.matcher.knnMatch(descriptors, k=2)
        matches = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < 0.68*b.distance]
        # Multiple UI features cannot vote for the same reference feature.
        unique = {}
        for match in sorted(matches, key=lambda m: m.distance):
            unique.setdefault(match.trainIdx, match)
        matches = list(unique.values())
        if len(matches) < 14:
            return None
        src = self.points[[m.trainIdx for m in matches]]
        dst = np.float32([keys[m.queryIdx].pt for m in matches])+np.float32([ox,oy])
        matrix, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                                    ransacReprojThreshold=3.0, maxIters=3000)
        if matrix is None or inliers is None or not np.isfinite(matrix).all():
            return None
        good = inliers.ravel().astype(bool)
        count = int(good.sum())
        ratio = count / len(matches)
        scale = float(np.linalg.norm(matrix[:, 0]))
        if count < 12 or ratio < 0.65 or not 0.03 <= scale <= 20:
            return None
        target = dst[good]
        # A tiny patch or single landmark cannot anchor an entire map.
        h, w = frame.shape[:2]
        area = cv2.contourArea(cv2.convexHull(target))
        usable_area = cv2.countNonZero(mask) if mask is not None else h*w
        if area < usable_area * 0.08:
            return None
        predicted = cv2.transform(src[good].reshape(1, -1, 2), matrix)[0]
        error = float(np.percentile(np.linalg.norm(predicted-target, axis=1), 95))
        if error > 3.0:
            return None
        world = np.vstack([self.terrain.world_to_image, [0, 0, 1]])
        return (matrix @ world, ratio, error)


@lru_cache(maxsize=64)
def template_variants(shape,dtype,raw,frame_size=None):
    template=np.frombuffer(raw,dtype=np.dtype(dtype)).reshape(shape)
    source=gray(template)
    silhouettes=[];grays=[]
    factors=[.65,.8,1.,1.25,1.5,2.]
    # Installed legacy HUD templates were captured at 1366x768. Include the
    # exact client-height and width scale, including windowed 16:10 clients.
    if frame_size:
        w,h=frame_size
        factors=[v for v in (h/768,w/1366) if .5<=v<=4.]+factors
    for factor in dict.fromkeys(round(v,6) for v in factors):
        resized=cv2.resize(template,None,fx=factor,fy=factor)
        grays.append(cv2.resize(source,None,fx=factor,fy=factor))
        if template.ndim==3:
            silhouettes.append(cv2.inRange(cv2.cvtColor(resized,cv2.COLOR_BGR2HSV),(0,0,205),(180,70,255)))
    return source.std()>=8,tuple(grays),tuple(silhouettes)


def template_visible(frame: np.ndarray, template: np.ndarray, roi: tuple) -> bool:
    h,w=frame.shape[:2];x,y,rw,rh=roi
    crop=gray(frame[int(y*h):int((y+rh)*h),int(x*w):int((x+rw)*w)])
    if crop.size==0:return False
    textured,variants,_=template_variants(template.shape,template.dtype.str,template.tobytes(),(w,h))
    if not textured:return False
    for t in variants:
        if t.shape[0]<=crop.shape[0] and t.shape[1]<=crop.shape[1]:
            if cv2.minMaxLoc(cv2.matchTemplate(crop,t,cv2.TM_CCOEFF_NORMED))[1]>=.88:return True
    return False


def foreground_ui_visible(frame: np.ndarray, template: np.ndarray, roi: tuple) -> bool:
    if not isinstance(template,np.ndarray) or template.ndim!=3 or frame.ndim!=3:return False
    h,w=frame.shape[:2];x,y,rw,rh=roi
    crop=frame[int(y*h):int((y+rh)*h),int(x*w):int((x+rw)*w)]
    if crop.size==0:return False
    crop=cv2.inRange(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV),(0,0,205),(180,70,255))
    _,_,variants=template_variants(template.shape,template.dtype.str,template.tobytes(),(w,h))
    for t in variants:
        if t.shape[0]>crop.shape[0] or t.shape[1]>crop.shape[1]:continue
        fraction=cv2.countNonZero(t)/t.size
        if .1<fraction<.85 and cv2.minMaxLoc(cv2.matchTemplate(crop,t,cv2.TM_CCOEFF_NORMED))[1]>=.82:return True
    return False


def detect_circle(frame: np.ndarray) -> tuple[float, float, float] | None:
    h, w = frame.shape[:2]
    # The standard desktop HUD is anchored to client height. Validate its
    # native glyph now, rather than allowing a coastline Hough circle to
    # shrink the map. Other layouts retain visual circumference recovery.
    if w/h>=1.45:
        candidates=[]
        heights=((h,) if w/h>=1.7 else ())+(min(h,w*768/1366),)
        for hud_height in dict.fromkeys(heights):
            standard=(hud_height*.154,hud_height*.115,hud_height*.10)
            shape=pointer_shape(frame,standard)
            if shape is not None:
                x,y,r=standard;margin=max(12,round(r*.27))
                point=shape[1]+[max(0,round(x)-margin),max(0,round(y)-margin)]
                candidates.append((math.hypot(point[0]-x,point[1]-y)/r,standard))
        if candidates:return min(candidates,key=lambda pair:pair[0])[1]
    crop = gray(frame[:int(h*0.35), :int(w*0.28)])
    if crop.size == 0:
        return None
    scale = h / 1080
    circles = cv2.HoughCircles(cv2.GaussianBlur(crop, (5, 5), 1), cv2.HOUGH_GRADIENT,
                               dp=1, minDist=max(6, int(12*scale)), param1=70, param2=30,
                               minRadius=max(15, int(55*scale)), maxRadius=max(20, int(130*scale)))
    if circles is None:
        return None
    hsv=cv2.cvtColor(frame[:crop.shape[0],:crop.shape[1]],cv2.COLOR_BGR2HSV)
    cyan=cv2.inRange(hsv,(80,100,160),(110,255,255))
    count,_,stats,centers=cv2.connectedComponentsWithStats(cyan)
    # HUD positions scale with client height. This is a broad image-only search
    # region, not a player/world coordinate or a manual calibration.
    expected=np.array([h*.154,h*.115])
    def near_hud(px,py):return np.linalg.norm(np.array([px,py])-expected)<=h*.03
    candidates=[]
    def add(px,py,radius):
        if not (near_hud(px,py) and radius>=max(15,55*scale) and px-radius>=0 and py-radius>=0
                and px+radius<crop.shape[1] and py+radius<crop.shape[0]):return
        candidate=(float(px),float(py),radius)
        previous=next((n for n,(a,b,_) in enumerate(candidates) if math.hypot(px-a,py-b)<5),None)
        if previous is None:candidates.append(candidate)
        elif radius>candidates[previous][2]:candidates[previous]=candidate
    # Keep the established colour test when it is unambiguous. The local
    # contrast path is recovery for a small glyph or water-connected component.
    for x,y,r in circles[0]:
        for i in range(1,count):
            px,py=centers[i];_,_,aw,ah,area=stats[i];offset=math.hypot(px-x,py-y)
            if (.015*r*r<area<.07*r*r and .65<aw/max(ah,1)<1.5 and offset<r*.4):
                add(px,py,float(r)-offset)
    if candidates:return candidates[0] if len(candidates)==1 else None
    for x,y,r in circles[0]:
        if not (w*.065<x<w*.18 and h*.04<y<h*.22):continue
        pointer=pointer_shape(frame,(x,y,r),center_fraction=.3)
        if pointer is None:continue
        _,center=pointer
        margin=max(12,round(r*.27));left=max(0,round(x)-margin);top=max(0,round(y)-margin)
        px,py=center+[left,top];add(px,py,float(r)-math.hypot(px-x,py-y))
    return candidates[0] if len(candidates)==1 else None


def confirmed_circle(frame,previous=None):
    """Reuse HUD geometry only when the current native player glyph confirms it.

    This caches the minimap's screen rectangle, never the player's world pose.
    Ice, water and map decorations otherwise make Hough fluctuate each request.
    """
    if previous is not None:
        x,y,r=previous;h,w=frame.shape[:2];scale=h/1080
        if (w*.065<x<w*.18 and h*.04<y<h*.22 and 55*scale<=r<=130*scale
                and x-r>=0 and y-r>=0 and x+r<w*.28 and y+r<h*.35):
            if pointer_shape(frame,previous) is not None:return previous
    return detect_circle(frame)


class LayerRecognizer:
    """One coarse index per selected map; refine only candidate layers.

Factories release nonselected artwork after indexing. At most three full SIFT
recognizers are retained, rather than loading every floor into the hot loop.
"""
    def __init__(self,factories,cancelled=lambda:False):
        self.factories=[];self.owners=[];self.cache={};self.last=None
        self.sift=cv2.SIFT_create(nfeatures=1800,contrastThreshold=.025)
        self.matcher=cv2.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=64))
        self.surface_index=None
        self.circle_hint=None
        for factory in factories:
            if cancelled():
                from src.live.reference import ReferenceCancelled
                raise ReferenceCancelled('Seleção substituída')
            try: pack=factory()
            except (ValueError,OSError): continue
            index=len(self.factories);self.factories.append(factory)
            if index==0: self.pack=pack
            if pack.layer_id=='surface': self.surface_index=index
            for terrain in (pack.terrain,*pack.extra_terrain):
                if cancelled():
                    from src.live.reference import ReferenceCancelled
                    raise ReferenceCancelled('Seleção substituída')
                _,descriptors=self.sift.detectAndCompute(gray(terrain.image),None)
                if descriptors is not None and len(descriptors)>=20:
                    self.matcher.add([descriptors]);self.owners.append(index)
        if not self.factories or not self.owners:
            raise ValueError("Nenhuma camada com referência compatível instalada")
        self.matcher.train()

    def observe(self,frame,stamp):
        if frame is None or frame.size==0: return Observation('hidden',stamp,reason='Captura indisponível')
        h,w=frame.shape[:2]
        is_map=template_visible(frame,self.pack.map_ui,self.pack.map_ui_roi)
        if is_map:
            crop=frame[int(.08*h):int(.90*h),int(.20*w):int(.80*w)]
        elif (template_visible(frame,self.pack.gameplay_ui,self.pack.gameplay_ui_roi) or
              foreground_ui_visible(frame,self.pack.gameplay_ui,self.pack.gameplay_ui_roi)):
            circle=confirmed_circle(frame,self.circle_hint)
            if circle is None: return Observation('hidden',stamp,reason='Minimapa não reconhecido')
            self.circle_hint=circle
            x,y,r=circle
            crop=frame[max(0,int(y-r)):int(y+r),max(0,int(x-r)):int(x+r)]
        else: return Observation('hidden',stamp,reason='Menu, carregamento ou tela não reconhecida')
        _,query=self.sift.detectAndCompute(gray(crop),None)
        votes={}
        if query is not None:
            unique=set()
            for pair in self.matcher.knnMatch(query,k=2):
                if len(pair)!=2: continue
                a,b=pair
                identity=(a.imgIdx,a.trainIdx)
                if a.distance<.7*b.distance and identity not in unique:
                    unique.add(identity);owner=self.owners[a.imgIdx]
                    votes[owner]=votes.get(owner,0)+1
        candidates=[i for i,count in sorted(votes.items(),key=lambda p:-p[1])[:2] if count>=6]
        if len(self.factories)==1: candidates=[0]
        for index in (self.last,self.surface_index):
            if index is not None and index not in candidates: candidates.append(index)
        candidates=candidates[:3]
        matches=[]
        for index in candidates:
            if index not in self.cache:
                self.cache[index]=ScreenRecognizer(self.pack if index==0 else self.factories[index]())
            recognizer=self.cache.pop(index);self.cache[index]=recognizer
            while len(self.cache)>3: self.cache.pop(next(iter(self.cache)))
            matches.append((index,recognizer.observe(frame,stamp)))
        valid=[(i,o) for i,o in matches if o.fresh(stamp)]
        if len(valid)==1:
            self.last=valid[0][0]
            return valid[0][1]
        return Observation("hidden",stamp,reason="Camada ambígua" if valid else "Mapa ou camada não reconhecidos")


class ScreenRecognizer:
    def __init__(self, pack: ReferencePack):
        self.pack = pack
        self.matcher = TerrainMatcher(pack.terrain)
        self.matchers=[self.matcher]+[TerrainMatcher(t) for t in pack.extra_terrain]
        self.minimap_matchers=[]
        for terrain in getattr(pack,'minimap_terrain',()):
            # Atlas edges can contain only sea/empty tiles. Such a block must
            # not disable all the detailed blocks that do contain landmarks.
            try:self.minimap_matchers.append(TerrainMatcher(terrain))
            except ValueError:continue
        self.last_minimap_matcher=None
        self.last_minimap_player=None
        self.raster_fallback=None
        self.circle_hint=None

    def minimap_candidates(self):
        matchers=list(self.minimap_matchers)
        point=self.last_minimap_player
        if point is not None:
            def distance(matcher):
                terrain=matcher.terrain
                x,y=terrain.world_to_image@np.array([*point,1.])
                h,w=terrain.image.shape[:2]
                # Distance outside each raster, expressed in world units.
                scale=np.linalg.norm(terrain.world_to_image[:,0])
                return math.hypot(max(0,-x,x-w),max(0,-y,y-h))/scale
            matchers.sort(key=distance)
        if self.last_minimap_matcher in matchers:
            matchers.remove(self.last_minimap_matcher)
            matchers.insert(0,self.last_minimap_matcher)
        return matchers

    def observe(self, frame: np.ndarray, captured_at: float | None = None) -> Observation:
        stamp = time.monotonic() if captured_at is None else captured_at
        if frame is None or frame.size == 0:
            return Observation("hidden", stamp, reason="Captura indisponível")
        h, w = frame.shape[:2]
        circle = None
        # Require positive visual UI evidence; textured menus are not gameplay.
        if template_visible(frame, self.pack.map_ui, self.pack.map_ui_roi):
            surface = "map"
            mask = np.zeros((h,w), np.uint8)
            mask[int(.08*h):int(.90*h), int(.20*w):int(.80*w)] = 255
        elif (template_visible(frame, self.pack.gameplay_ui, self.pack.gameplay_ui_roi) or
              foreground_ui_visible(frame,self.pack.gameplay_ui,self.pack.gameplay_ui_roi)):
            circle = confirmed_circle(frame,self.circle_hint)
            if circle is None:
                return Observation("hidden", stamp, reason="Minimapa não reconhecido")
            self.circle_hint=circle
            surface = "minimap"
            cx, cy, r = circle
            mask = np.zeros((h,w), np.uint8)
            cv2.circle(mask, (round(cx), round(cy)), max(1, round(r-8)), 255, -1)
            # Exclude the player arrow and minimap border from feature matching.
            cv2.circle(mask, (round(cx), round(cy)), max(8, round(r*.17)), 0, -1)
        else:
            return Observation("hidden", stamp, reason="Menu, carregamento ou tela não reconhecida")
        fit=None
        masks=[mask]
        if circle:
            # Native quest/waypoint glyphs can dominate a particular annulus.
            # Retry inner terrain with exactly the same geometric rejection gates.
            for fraction in (.85,.7):
                inner=mask.copy()
                disk=np.zeros_like(mask)
                cv2.circle(disk,(round(cx),round(cy)),max(1,round((r-8)*fraction)),255,-1)
                masks.append(cv2.bitwise_and(inner,disk))
        matchers=self.matchers
        if circle and self.minimap_matchers:
            matchers=self.minimap_candidates()
        queries={}
        # Exhaust the current block and its neighbours across all annuli before
        # searching distant blocks. Teleports still fall through to a full search.
        groups=[matchers[:3],matchers[3:]] if circle else [matchers]
        for group in groups:
            for index,candidate_mask in enumerate(masks):
                if index not in queries:queries[index]=matchers[0].query(frame,candidate_mask)
                query=queries[index]
                if query is None:continue
                for matcher in group:
                    fit=matcher.match(frame,candidate_mask,query=query)
                    if fit is not None:
                        if circle:self.last_minimap_matcher=matcher
                        break
                if fit is not None:break
            if fit is not None: break
        if fit is None and circle:
            # Re-sampling changes SIFT extrema at HUD scale; CRS and geometric
            # rejection gates remain unchanged. Cache just this selected pack.
            if self.raster_fallback is None:
                terrain=max((self.pack.terrain,*self.pack.extra_terrain),
                            key=lambda t:abs(np.linalg.det(t.world_to_image[:,:2])))
                image=cv2.resize(terrain.image,None,fx=1.25,fy=1.25,interpolation=cv2.INTER_CUBIC)
                self.raster_fallback=TerrainMatcher(Terrain(image,terrain.world_to_image*1.25,terrain.source))
            fit=self.raster_fallback.match(frame,mask)
        if fit is None:
            return Observation("hidden", stamp, reason="Localizando no mapa selecionado…")
        matrix, confidence, error = fit
        player = None
        if circle:
            inverse = cv2.invertAffineTransform(matrix)
            point = inverse @ np.array([circle[0], circle[1], 1])
            player = (float(point[0]), float(point[1]))
            self.last_minimap_player=player
        return Observation(surface, stamp, matrix, confidence, error, circle, player,
                           "Explorando" if circle else "Mapa reconhecido",self.pack.map_id,self.pack.layer_id)
