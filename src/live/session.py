"""Shared selection, projections, and explicit reversible collection."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

import numpy as np

from src.live.catalog import Item
from src.live.icons import ICON_MARGIN
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager


@dataclass(frozen=True)
class Pin:
    item: Item
    x: float
    y: float


class Session:
    def __init__(self, items: list[Item], progress: ProgressManager):
        self.items = items
        self.progress = progress
        self.selected: set[str] = set()
        self.hidden = False
        self.observation = Observation("hidden", 0)
        self.undo_ids: list[str] = []
        self.pending_ids: set[str] = set()
        self.pending_at = 0.0
        self.notice = ""

    def active(self) -> list[Item]:
        return [i for i in self.items if i.category in self.selected and not self.progress.is_collected(i.id)]

    def invalidate(self, reason: str, clear_pending: bool = True) -> None:
        self.observation = Observation("hidden", time.monotonic(), reason=reason)
        if clear_pending:
            self.pending_ids.clear()

    def pins(self, width: int, height: int, now: float | None = None,
             include_collected: bool = False) -> list[Pin]:
        obs = self.observation
        now = time.monotonic() if now is None else now
        if self.hidden or not obs.fresh(now):
            return []
        pins = []
        items=([i for i in self.items if i.category in self.selected] if include_collected else self.active())
        for item in items:
            x, y = obs.world_to_screen @ np.array([item.x, item.y, 1])
            if not (ICON_MARGIN <= x < width-ICON_MARGIN and ICON_MARGIN <= y < height-ICON_MARGIN):
                continue
            if obs.surface == "minimap":
                if obs.circle is None:
                    continue
                cx, cy, radius = obs.circle
                # Entire icon stays inside the circle, rather than its center only.
                if math.hypot(x-cx, y-cy) > radius-ICON_MARGIN:
                    continue
            elif not (width*.20 <= x <= width*.80 and height*.08 <= y <= height*.90):
                # Leave native sidebars, zoom controls, and close button clear.
                continue
            pins.append(Pin(item, float(x), float(y)))
        return pins

    def hit_test(self, width: int, height: int, x: float, y: float,
                 now: float | None = None) -> list[Item]:
        pins=self.pins(width,height,now,include_collected=True)
        hits=[p for p in pins if abs(p.x-x)<=ICON_MARGIN and abs(p.y-y)<=ICON_MARGIN]
        hits.sort(key=lambda p:(math.hypot(p.x-x,p.y-y),p.item.id))
        return [p.item for p in hits]

    def set_collected(self, identifier: str, collected: bool) -> bool:
        """Explicit marker menu action; map selection doesn't require proximity."""
        if identifier not in {i.id for i in self.items}:
            return False
        previous=self.progress.is_collected(identifier)
        if previous==collected:
            return False
        record=self.progress.get_collection_record(identifier)
        if collected:
            self.progress.mark_collected(identifier)
        else:
            self.progress.mark_uncollected(identifier)
        try:
            self.progress.save()
        except Exception:
            if previous:
                self.progress._collected_records[identifier]=record
            else:
                self.progress.mark_uncollected(identifier)
            raise
        if collected:
            self.undo_ids.append(identifier)
        else:
            self.undo_ids=[i for i in self.undo_ids if i!=identifier]
        self.pending_ids.discard(identifier)
        self.notice="Item marcado como pego." if collected else "Item desmarcado."
        return True

    def candidates(self, now: float) -> list[Item]:
        obs = self.observation
        if self.hidden or obs.surface!="minimap" or not obs.fresh(now) or obs.player is None or obs.circle is None:
            return []
        # Radius is in current minimap pixels: do not invent world-unit meters.
        cx,cy,_ = obs.circle
        result = []
        for item in self.active():
            x,y = obs.world_to_screen @ np.array([item.x,item.y,1])
            distance = math.hypot(x-cx,y-cy)
            if distance <= 22:
                result.append((distance,item))
        return [item for _,item in sorted(result, key=lambda pair: pair[0])]

    def collect(self, now: float | None = None) -> bool:
        stamp = time.monotonic() if now is None else now
        candidates = self.candidates(stamp)
        self.pending_ids = {i.id for i in candidates}
        self.pending_at = stamp
        if len(candidates) == 1:
            return self.confirm(candidates[0].id, stamp)
        self.notice = ("Há vários itens próximos. Selecione o coletado no painel."
                       if candidates else "Nenhum item próximo com localização válida.")
        return False

    def confirm(self, identifier: str, now: float | None = None) -> bool:
        stamp = time.monotonic() if now is None else now
        # Explicit panel confirmation must still refer to the recent candidate set.
        if identifier not in self.pending_ids or not 0 <= stamp-self.pending_at <= 30:
            self.notice = "Seleção expirada. Confirme os itens próximos novamente."
            return False
        if identifier not in {i.id for i in self.active()}:
            return False
        changed = self.progress.mark_collected(identifier)
        if not changed:
            return False
        try:
            self.progress.save()
        except Exception:
            self.progress.mark_uncollected(identifier)
            raise
        self.undo_ids.append(identifier)
        self.pending_ids.clear()
        self.notice = "Item marcado como coletado. Você pode desfazer."
        return True

    def undo(self) -> bool:
        if not self.undo_ids:
            self.notice = "Nenhuma coleta desta sessão para desfazer."
            return False
        identifier = self.undo_ids[-1]
        record = self.progress.get_collection_record(identifier)
        if not self.progress.mark_uncollected(identifier):
            return False
        try:
            self.progress.save()
        except Exception:
            # Restore the exact record, including original timestamp and notes.
            self.progress._collected_records[identifier] = record
            raise
        self.undo_ids.pop()
        self.notice = "Última coleta desfeita."
        return True
