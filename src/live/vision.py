"""Screen recognition and current-frame SIFT registration, with rejection gates."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

import cv2
import numpy as np

from src.live.reference import ReferencePack, Terrain


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

    def fresh(self, now: float, ttl: float = 0.65) -> bool:
        age = now - self.captured_at
        return (self.surface in {"minimap", "map"} and 0 <= age <= ttl
                and self.world_to_screen is not None and self.confidence >= 0.65
                and np.isfinite(self.world_to_screen).all())


def gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


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

    def match(self, frame: np.ndarray, mask: np.ndarray | None = None):
        image=gray(frame)
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
        keys, descriptors = self.sift.detectAndCompute(image, local_mask)
        if descriptors is None or len(keys) < 14:
            return None
        pairs = self.matcher.knnMatch(descriptors, k=2)
        matches = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < 0.68*b.distance]
        # Multiple UI features cannot vote for the same reference feature.
        unique = {}
        for match in sorted(matches, key=lambda m: m.distance):
            unique.setdefault(match.trainIdx, match)
        matches = list(unique.values())
        if len(matches) < 14:
            return None
        src = np.float32([self.keys[m.trainIdx].pt for m in matches])
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


def template_visible(frame: np.ndarray, template: np.ndarray, roi: tuple) -> bool:
    h, w = frame.shape[:2]
    x, y, rw, rh = roi
    crop = gray(frame[int(y*h):int((y+rh)*h), int(x*w):int((x+rw)*w)])
    # UI changes with resolution/DPI, so search a limited scale pyramid.
    if crop.size == 0 or gray(template).std() < 8:
        return False
    for factor in (0.65, 0.8, 1.0, 1.25, 1.5, 2.0):
        t = cv2.resize(gray(template), None, fx=factor, fy=factor)
        if t.shape[0] > crop.shape[0] or t.shape[1] > crop.shape[1]:
            continue
        if cv2.minMaxLoc(cv2.matchTemplate(crop, t, cv2.TM_CCOEFF_NORMED))[1] >= 0.88:
            return True
    return False


def detect_circle(frame: np.ndarray) -> tuple[float, float, float] | None:
    h, w = frame.shape[:2]
    crop = gray(frame[:int(h*0.35), :int(w*0.28)])
    if crop.size == 0:
        return None
    scale = h / 1080
    circles = cv2.HoughCircles(cv2.GaussianBlur(crop, (5, 5), 1), cv2.HOUGH_GRADIENT,
                               dp=1, minDist=max(20, int(70*scale)), param1=70, param2=30,
                               minRadius=max(15, int(55*scale)), maxRadius=max(20, int(130*scale)))
    if circles is None:
        return None
    # Require the cyan player arrow near the detected center; terrain circles
    # alone are not evidence of the gameplay minimap. Refine its center from
    # that arrow instead of trusting a partly occluded circumference.
    hsv=cv2.cvtColor(frame[:crop.shape[0],:crop.shape[1]],cv2.COLOR_BGR2HSV)
    cyan=cv2.inRange(hsv,(80,100,160),(110,255,255))
    count,_,stats,centers=cv2.connectedComponentsWithStats(cyan)
    candidates=[]
    for x,y,r in circles[0]:
        if not (x-r>=0 and y-r>=0 and x+r<crop.shape[1] and y+r<crop.shape[0]):
            continue
        for i in range(1,count):
            px,py=centers[i]; _,_,aw,ah,area=stats[i]
            if (w*.065<px<w*.18 and h*.04<py<h*.22 and
                    .015*r*r<area<.07*r*r and .65<aw/max(ah,1)<1.5 and
                    math.hypot(px-x,py-y)<r*.20):
                candidate=(float(px),float(py),float(r))
                if not any(math.hypot(px-a,py-b)<5 for a,b,_ in candidates):
                    candidates.append(candidate)
    return candidates[0] if len(candidates)==1 else None


class ScreenRecognizer:
    def __init__(self, pack: ReferencePack):
        self.pack = pack
        self.matcher = TerrainMatcher(pack.terrain)
        self.matchers=[self.matcher]+[TerrainMatcher(t) for t in pack.extra_terrain]

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
        elif template_visible(frame, self.pack.gameplay_ui, self.pack.gameplay_ui_roi):
            circle = detect_circle(frame)
            if circle is None:
                return Observation("hidden", stamp, reason="Minimapa não reconhecido")
            surface = "minimap"
            cx, cy, r = circle
            mask = np.zeros((h,w), np.uint8)
            cv2.circle(mask, (round(cx), round(cy)), max(1, round(r-8)), 255, -1)
            # Exclude the player arrow and minimap border from feature matching.
            cv2.circle(mask, (round(cx), round(cy)), max(8, round(r*.17)), 0, -1)
        else:
            return Observation("hidden", stamp, reason="Menu, carregamento ou tela não reconhecida")
        fit=None
        for matcher in self.matchers:
            fit=matcher.match(frame,mask)
            if fit is not None:
                break
        if fit is None:
            return Observation("hidden", stamp, reason="Localizando em Mondstadt…")
        matrix, confidence, error = fit
        player = None
        if circle:
            inverse = cv2.invertAffineTransform(matrix)
            point = inverse @ np.array([circle[0], circle[1], 1])
            player = (float(point[0]), float(point[1]))
        return Observation(surface, stamp, matrix, confidence, error, circle, player,
                           "Explorando Mondstadt" if circle else "Mapa de Mondstadt")
