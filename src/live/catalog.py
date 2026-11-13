"""Read the pinned, unmodified community dataset into its native map space."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
import sys
from pathlib import Path

_intern = sys.intern
_empty_tuple: tuple[str, ...] = ()
_tuple_cache: dict[tuple[str, ...], tuple[str, ...]] = {}


def _intern_tuple(seq) -> tuple[str, ...]:
    if not seq:
        return _empty_tuple
    key = tuple(_intern(s) for s in seq)
    cached = _tuple_cache.get(key)
    if cached is None:
        _tuple_cache[key] = key
        return key
    return cached


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    name: str
    category: str
    x: float
    y: float
    region_id: str = "mondstadt"
    map_id: str = "teyvat"
    layer_id: str = "surface"
    area_id: str = "unclassified"
    rule_id: str = "permanent"
    category_ids: tuple[str,...] = ()
    area_ids: tuple[str,...] = ()
    layer_ids: tuple[str,...] = ()
    source_marker_id: int | None = None
    source_stamp: str | None = None
    source_refresh_value: int | None = None
    source_area_ids: tuple[str,...] = ()


CATEGORIES = {
    "common-chest": ("Baús comuns", "#d4bea0"),
    "exquisite-chest": ("Baús sofisticados", "#8dd9ed"),
    "precious-chest": ("Baús preciosos", "#d5a2f2"),
    "luxurious-chest": ("Baús luxuosos", "#ffd36d"),
    "anemoculus": ("Anemoculi", "#71efca"),
}
CATEGORY_GROUPS={key:("Oculi" if key=="anemoculus" else "Baús") for key in CATEGORIES}


def map_pixel(latitude: float, longitude: float) -> tuple[float, float]:
    """Teyvat.moe Leaflet CRS.Simple, zoom 7 (confirmed in LeafletMap.tsx)."""
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        raise ValueError("Coordenada geográfica inválida")
    return longitude * 128, -latitude * 128


def load_catalog(directory: Path, *, register: bool = True) -> list[Item]:
    source = json.loads((directory / "SOURCE.json").read_text(encoding="utf-8"))
    region=source.get("region_id",directory.name)
    if not isinstance(region,str) or not re.fullmatch(r"[a-z][a-z0-9_-]*",region):
        raise ValueError("Identificador de região inválido")
    categories=dict(CATEGORIES);groups=dict(CATEGORY_GROUPS)
    for key,meta in source.get("categories",{}).items():
        categories[key]=(meta["name"],meta.get("color","#a8d5e5"))
        groups[key]=meta["group"]
    result: list[Item] = []
    seen: set[str] = set()
    for entry in source["files"]:
        path = (directory / entry["file"]).resolve()
        if path.parent != directory.resolve():
            raise ValueError("Arquivo de catálogo fora da pasta de dados")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Dados alterados: {path.name}")
        category = entry.get("category",path.stem)
        if entry.get("format")=="normalized-v1":
            for row in json.loads(raw)["items"]:
                row=dict(row)
                for field in ('category_ids','area_ids','layer_ids','source_area_ids'):
                    values=row.get(field,[])
                    if not isinstance(values,list) or not all(isinstance(v,str) for v in values):
                        raise ValueError('Classificação territorial ou categoria inválida')
                    row[field]=_intern_tuple(values)
                for str_field in ('id','category','region_id','map_id','layer_id','area_id','rule_id','source_stamp'):
                    if str_field in row and isinstance(row[str_field],str):
                        row[str_field]=_intern(row[str_field])
                item=Item(**row)
                if item.region_id!=region or item.id in seen or not math.isfinite(item.x+item.y):
                    raise ValueError("Marcador normalizado inválido ou duplicado")
                declared=source.get('categories',{})
                if item.category not in declared or any(c not in declared for c in item.category_ids):
                    raise ValueError("Categoria sem metadados")
                seen.add(item.id);result.append(item)
            continue
        if category not in categories:
            raise ValueError(f"Categoria não suportada: {category}")
        for row in json.loads(raw)["data"]:
            # Namespace source IDs: old demo progress must never hide real items.
            identifier = f"teyvat.moe:{region}:{category}:{row['id']}"
            if identifier in seen:
                raise ValueError(f"ID duplicado: {identifier}")
            seen.add(identifier)
            x, y = map_pixel(*row["coordinates"])
            title = row.get("popupTitle", {})
            name = title.get("pt") or title.get("en") or categories[category][0]
            result.append(Item(identifier, name, category, x, y,region))
    if register:
        CATEGORIES.update(categories);CATEGORY_GROUPS.update(groups)
    return result
