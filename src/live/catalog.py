"""Read the pinned, unmodified community dataset into its native map space."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    x: float
    y: float


CATEGORIES = {
    "common-chest": ("Baús comuns", "#d4bea0"),
    "exquisite-chest": ("Baús sofisticados", "#8dd9ed"),
    "precious-chest": ("Baús preciosos", "#d5a2f2"),
    "luxurious-chest": ("Baús luxuosos", "#ffd36d"),
    "anemoculus": ("Anemoculi", "#71efca"),
}


def map_pixel(latitude: float, longitude: float) -> tuple[float, float]:
    """Teyvat.moe Leaflet CRS.Simple, zoom 7 (confirmed in LeafletMap.tsx)."""
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        raise ValueError("Coordenada geográfica inválida")
    return longitude * 128, -latitude * 128


def load_catalog(directory: Path) -> list[Item]:
    source = json.loads((directory / "SOURCE.json").read_text(encoding="utf-8"))
    result: list[Item] = []
    seen: set[str] = set()
    for entry in source["files"]:
        path = (directory / entry["file"]).resolve()
        if path.parent != directory.resolve():
            raise ValueError("Arquivo de catálogo fora da pasta de dados")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Dados alterados: {path.name}")
        category = path.stem
        if category not in CATEGORIES:
            raise ValueError(f"Categoria não suportada: {category}")
        for row in json.loads(raw)["data"]:
            # Namespace source IDs: old demo progress must never hide real items.
            identifier = f"teyvat.moe:mondstadt:{category}:{row['id']}"
            if identifier in seen:
                raise ValueError(f"ID duplicado: {identifier}")
            seen.add(identifier)
            x, y = map_pixel(*row["coordinates"])
            title = row.get("popupTitle", {})
            name = title.get("pt") or title.get("en") or CATEGORIES[category][0]
            result.append(Item(identifier, name, category, x, y))
    return result
