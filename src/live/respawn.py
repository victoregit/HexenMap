"""Verified per-node rules, UTC deadlines, and America server reset boundaries."""
from __future__ import annotations
from src.live.i18n import tr as _tr
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path

UTC=timezone.utc


@dataclass(frozen=True)
class RespawnRule:
    id: str
    kind: str
    seconds: int | None = None
    reset_hour: int = 4
    offset_hours: int = -5
    source: str = ""
    checked_at: str = ""
    note: str = ""

    def __post_init__(self):
        if self.kind not in {"permanent","elapsed","server_reset","conditional","unknown"}:
            raise ValueError(_tr("Política de reposição desconhecida"))
        if self.kind in {"elapsed","server_reset"} and (not self.source or not self.checked_at):
            raise ValueError(_tr("Reposição automática exige origem e data de conferência"))
        if self.kind=="elapsed" and (not isinstance(self.seconds,int) or self.seconds<=0):
            raise ValueError(_tr("Duração de reposição inválida"))
        if not 0<=self.reset_hour<24 or not -12<=self.offset_hours<=14:
            raise ValueError(_tr("Horário de servidor inválido"))

    def deadline(self,collected_at: datetime) -> datetime | None:
        if collected_at.tzinfo is None:
            raise ValueError(_tr("A coleta precisa de fuso explícito"))
        if self.kind=="elapsed":
            return collected_at.astimezone(UTC)+timedelta(seconds=self.seconds)
        if self.kind=="server_reset":
            zone=timezone(timedelta(hours=self.offset_hours))
            local=collected_at.astimezone(zone)
            reset=local.replace(hour=self.reset_hour,minute=0,second=0,microsecond=0)
            if reset<=local: reset+=timedelta(days=1)
            return reset.astimezone(UTC)
        return None


PERMANENT=RespawnRule("permanent","permanent")
UNKNOWN=RespawnRule("unknown","unknown",note="Reposição não confirmada")


def parse_utc(value):
    if not isinstance(value,str): return None
    try:
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
        return stamp.astimezone(UTC) if stamp.tzinfo else None
    except ValueError:
        return None


def load_rules(path: Path) -> dict[str,RespawnRule]:
    rules={r.id:r for r in [PERMANENT,UNKNOWN]}
    if path.exists():
        data=json.loads(path.read_text(encoding="utf-8"))
        for row in data["rules"]:
            rule=RespawnRule(**row)
            if rule.id in rules:
                raise ValueError(_tr("Regra de reposição duplicada"))
            rules[rule.id]=rule
    return rules
