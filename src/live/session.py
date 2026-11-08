"""Shared selection, projections, and explicit reversible collection."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from datetime import datetime,timezone

import numpy as np

from src.live.catalog import Item
from src.live.marker_art import MarkerGeometry, LEGACY, marker_geometry
from src.live.vision import Observation
from src.progress.progress_manager import ProgressManager
from src.live.respawn import PERMANENT,UNKNOWN,parse_utc
from src.live.territory import TerritoryIndex
from src.live.chest_farm import ChestFarm


@dataclass(frozen=True)
class Pin:
    item: Item
    x: float
    y: float
    geometry: MarkerGeometry = LEGACY


@dataclass(frozen=True)
class CollectionCount:
    collected: int
    total: int

    @property
    def remaining(self) -> int:
        return self.total-self.collected


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
        self.region_id: str | None = None
        self.map_id: str | None = None
        self.layer_id: str | None = None
        self.area_id: str | None = None
        self.territories=TerritoryIndex([])
        self.rules={"permanent":PERMANENT,"unknown":UNKNOWN}
        self.clock=lambda:datetime.now(timezone.utc)
        self.undo_records=[]
        self.collection_epoch=0
        self._scope_key=None
        self._scope_items=[]
        self._lookup_key=None
        self._lookup={}
        self._projection_key=None
        self._projection_items=[]
        self._projection_points=np.empty((0,3))
        self.marker_dpi=1.
        self.farm=ChestFarm()

    def item_by_id(self,identifier):
        key=(id(self.items),len(self.items))
        if key!=self._lookup_key:
            self._lookup={i.id:i for i in self.items};self._lookup_key=key
        return self._lookup.get(identifier)

    def scoped_items(self) -> list[Item]:
        key=(id(self.items),len(self.items),self.region_id,self.map_id,self.layer_id,self.area_id,id(self.territories))
        if key==self._scope_key: return self._scope_items
        areas=self.territories.descendants(self.area_id) if self.area_id else None
        self._scope_items=[i for i in self.items if
                (not self.region_id or i.region_id==self.region_id) and
                (not self.map_id or i.map_id==self.map_id) and
                (not self.layer_id or self.layer_id in (i.layer_ids or (i.layer_id,))) and
                (areas is None or (self.area_id=="unclassified" and i.area_id=="unclassified") or
                 bool(set(i.area_ids or (i.area_id,)) & areas))]
        self._scope_key=key
        return self._scope_items

    def is_collected(self,identifier: str) -> bool:
        record=self.progress.get_collection_record(identifier)
        if record is None: return False
        item=self.item_by_id(identifier)
        rule=self.rules.get(item.rule_id,UNKNOWN) if item else UNKNOWN
        if rule.kind not in {'elapsed','server_reset'}: return True
        deadline=parse_utc(record.get("ready_at"))
        return deadline is None or self.clock()<deadline

    def get_collection_record(self,identifier):
        return self.progress.get_collection_record(identifier)

    def respawn_text(self,item: Item) -> str:
        rule=self.rules.get(item.rule_id,UNKNOWN)
        record=self.progress.get_collection_record(item.id)
        if rule.kind in {"unknown","conditional"}: return "Reposição não confirmada"
        if rule.kind=='permanent': return ''
        deadline=parse_utc(record.get("ready_at")) if record else None
        if deadline and self.is_collected(item.id):
            seconds=max(0,int((deadline-self.clock()).total_seconds()))
            days,remainder=divmod(seconds,86400);hours,minutes=divmod(remainder//60,60)
            return f"Reposição estimada: {days}d {hours:02d}h {minutes:02d}min"
        if record and rule.kind in {'elapsed','server_reset'} and deadline is None:
            return "Reposição não confirmada"
        if deadline: return "Disponibilidade estimada — confira no jogo"
        return ""

    def active(self) -> list[Item]:
        return [i for i in self.scoped_items() if bool(set(i.category_ids or (i.category,)) & self.selected)
                and not self.is_collected(i.id)]

    def collection_counts(self) -> dict[str,CollectionCount]:
        """Count this catalog only, independently of visibility and selected filters."""
        values={}
        for item in self.scoped_items():
            for category in set(item.category_ids or (item.category,)):
                collected,total=values.get(category,(0,0))
                values[category]=(collected+int(self.is_collected(item.id)),total+1)
        return {category:CollectionCount(*count) for category,count in values.items()}

    def progress_summary(self):
        items=self.scoped_items()
        key=(self._scope_key,id(self.rules))
        if getattr(self,'_summary_key',None)!=key:
            self._permanent_ids={i.id for i in items if self.rules.get(i.rule_id,UNKNOWN).kind=='permanent'}
            self._other_ids={i.id for i in items}-self._permanent_ids
            self._summary_key=key
        collected=unavailable=0
        for identifier in self.progress.get_collected_ids():
            if identifier in self._permanent_ids and self.is_collected(identifier):collected+=1
            elif identifier in self._other_ids and self.is_collected(identifier):unavailable+=1
        return collected,len(self._permanent_ids),unavailable

    def invalidate(self, reason: str, clear_pending: bool = True) -> None:
        self.observation = Observation("hidden", time.monotonic(), reason=reason)
        if clear_pending:
            self.pending_ids.clear()

    def pins(self, width: int, height: int, now: float | None = None,
             include_collected: bool = False, observation: Observation | None = None) -> list[Pin]:
        obs = self.observation if observation is None else observation
        now = time.monotonic() if now is None else now
        if self.hidden or not obs.fresh(now):
            return []
        if (self.region_id and (not obs.map_id or not obs.layer_id)) or (self.map_id and obs.map_id!=self.map_id):
            return []
        pins = []
        scoped=self.scoped_items()
        key=(self._scope_key,frozenset(self.selected),obs.map_id,obs.layer_id)
        if key!=self._projection_key:
            self._projection_items=[i for i in scoped if
                bool(set(i.category_ids or (i.category,)) & self.selected) and
                (not obs.map_id or i.map_id==obs.map_id) and
                (not obs.layer_id or obs.layer_id in (i.layer_ids or (i.layer_id,)))]
            self._projection_points=np.array([(i.x,i.y,1) for i in self._projection_items],dtype=np.float64)
            self._projection_key=key
        items=self._projection_items
        if not items: return []
        projected=self._projection_points @ obs.world_to_screen.T
        visible=(projected[:,0]>=0)&(projected[:,0]<width)&(projected[:,1]>=0)&(projected[:,1]<height)
        if obs.surface=='minimap':
            if obs.circle is None: return []
            cx,cy,radius=obs.circle
            visible &= np.hypot(projected[:,0]-cx,projected[:,1]-cy)<=radius
        else:
            visible &= ((projected[:,0]>=width*.20)&(projected[:,0]<=width*.80)&
                        (projected[:,1]>=height*.08)&(projected[:,1]<=height*.90))
        for index in np.flatnonzero(visible):
            item=items[index]
            # Query deadlines only for visible points, so expiry still takes effect
            # on the exact frame without rebuilding the static coordinate index.
            if not include_collected and self.is_collected(item.id): continue
            x,y=projected[index]
            geometry=marker_geometry(item.category,obs.surface,self.marker_dpi)
            left,top,right,bottom=geometry.bounds(x,y)
            if left<0 or top<0 or right>width or bottom>height:continue
            if obs.surface=='minimap' and not geometry.inside_circle(x,y,cx,cy,radius):continue
            pins.append(Pin(item, float(x), float(y),geometry))
        return pins

    def hit_test(self, width: int, height: int, x: float, y: float,
                 now: float | None = None) -> list[Item]:
        pins=self.pins(width,height,now,include_collected=True)
        hits=[p for p in pins if p.geometry.contains(p.x,p.y,x,y)]
        hits.sort(key=lambda p:(math.hypot(p.x-x,p.y-y),p.item.id))
        return [p.item for p in hits]

    def set_collected(self, identifier: str, collected: bool) -> bool:
        self.collection_epoch+=1
        """Explicit marker menu action; map selection doesn't require proximity."""
        if identifier not in {i.id for i in self.scoped_items()}:
            return False
        previous=self.is_collected(identifier)
        if previous==collected:
            return False
        record=self.progress.get_collection_record(identifier)
        if collected:
            item=next(i for i in self.items if i.id==identifier)
            stamp=self.clock()
            if stamp.tzinfo is None: raise ValueError("Horário da coleta sem fuso")
            stamp=stamp.astimezone(timezone.utc)
            rule=self.rules.get(item.rule_id,UNKNOWN)
            deadline=rule.deadline(stamp)
            updated={"collected_at":stamp.isoformat(),"notes":"","rule_id":rule.id}
            if deadline: updated["ready_at"]=deadline.isoformat()
            self.progress.replace_record(identifier,updated)
        else:
            self.progress.mark_uncollected(identifier)
        try:
            self.progress.save()
        except Exception:
            self.progress.replace_record(identifier,record)
            raise
        self.undo_ids.append(identifier)
        self.undo_records.append((identifier,record))
        self.pending_ids.discard(identifier)
        self.notice="Item marcado como pego." if collected else "Item desmarcado."
        return True

    def candidates(self, now: float) -> list[Item]:
        obs = self.observation
        if self.hidden or obs.surface!="minimap" or not obs.fresh(now) or obs.player is None or obs.circle is None:
            return []
        if (self.region_id and (not obs.map_id or not obs.layer_id)) or (self.map_id and obs.map_id!=self.map_id):
            return []
        # Radius is in current minimap pixels: do not invent world-unit meters.
        cx,cy,_ = obs.circle
        result = []
        for item in self.active():
            if obs.map_id and item.map_id!=obs.map_id: continue
            if obs.layer_id and obs.layer_id not in (item.layer_ids or (item.layer_id,)): continue
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
        if not self.set_collected(identifier,True): return False
        self.pending_ids.clear()
        self.notice = "Item marcado como coletado. Você pode desfazer."
        return True

    def undo(self) -> bool:
        self.collection_epoch+=1
        scoped={i.id for i in self.scoped_items()}
        index=next((n for n in range(len(self.undo_ids)-1,-1,-1) if self.undo_ids[n] in scoped),None)
        if index is None:
            self.notice = "Nenhuma alteração deste recorte para desfazer."
            return False
        identifier = self.undo_ids[index]
        record = self.progress.get_collection_record(identifier)
        previous=self.undo_records[index][1] if index<len(self.undo_records) else None
        self.progress.replace_record(identifier,previous)
        try:
            self.progress.save()
        except Exception:
            # Restore the exact record, including original timestamp and notes.
            self.progress.replace_record(identifier,record)
            raise
        self.undo_ids.pop(index)
        if index<len(self.undo_records): self.undo_records.pop(index)
        self.notice = "Última coleta desfeita."
        return True
