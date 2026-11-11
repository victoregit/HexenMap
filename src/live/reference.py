"""Explicit georeferenced image packs; missing artwork never becomes mock terrain."""
from __future__ import annotations

from src.live.i18n import tr as _tr
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


class ReferenceUnavailable(ValueError):
    pass


class ReferenceCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class Terrain:
    image: np.ndarray
    # Maps native catalog pixels (zoom 7) into the reference image.
    world_to_image: np.ndarray
    source: str


@dataclass(frozen=True)
class ReferencePack:
    terrain: Terrain
    # UI templates distinguish the native map from other screens with terrain.
    map_ui: np.ndarray
    gameplay_ui: np.ndarray
    map_ui_roi: tuple[float, float, float, float]
    gameplay_ui_roi: tuple[float, float, float, float]
    extra_terrain: tuple[Terrain, ...] = ()
    region_id: str = "mondstadt"
    map_id: str = "teyvat"
    layer_id: str = "surface"
    coordinate_system: str = "leaflet-simple-z7"
    minimap_terrain: tuple[Terrain, ...] = ()


def load_pack(directory: Path, region_id="mondstadt", map_id="teyvat", layer_id=None,
              coordinate_system="leaflet-simple-z7", cancelled=lambda:False) -> ReferencePack:
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        raise ReferenceUnavailable(_tr("Referência visual deste mapa ainda não instalada e validada."))
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data,dict):
            raise ValueError(_tr("Manifesto deve ser um objeto JSON"))
        if data["region"]!=region_id or data.get("map_id","teyvat")!=map_id or (layer_id and data["layer"]!=layer_id):
            raise ValueError(_tr("O pacote não corresponde à região, mapa ou camada selecionada"))
        if data["coordinate_system"] != coordinate_system:
            raise ValueError(_tr("Sistema de coordenadas incompatível"))
        if not data.get("permission", {}).get("evidence") or not data["permission"].get("usage"):
            raise ValueError(_tr("Falta a origem e a permissão de uso das referências"))

        def read_image(entry: dict) -> np.ndarray:
            if cancelled():raise ReferenceCancelled(_tr('Seleção substituída'))
            if not isinstance(entry,dict):
                raise ValueError(_tr("Metadados de imagem inválidos"))
            path = (directory / entry["file"]).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError(_tr("Referência fora da pasta do pacote"))
            raw = path.read_bytes()
            if not raw or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(_tr('Referência alterada: {0}', path.name))
            image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if cancelled():raise ReferenceCancelled(_tr('Seleção substituída'))
            if image is None or min(image.shape[:2]) < 12:
                raise ValueError(_tr('Imagem inválida: {0}', path.name))
            return image

        matrix = np.asarray(data["world_to_image"], dtype=np.float64)
        if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
            raise ValueError(_tr("Transformação geográfica inválida"))
        if abs(np.linalg.det(matrix[:, :2])) < 1e-10:
            raise ValueError(_tr("Transformação geográfica singular"))
        def roi(entry: dict) -> tuple:
            values = tuple(float(v) for v in entry["roi"])
            if len(values) != 4 or not all(0 <= v <= 1 for v in values) or values[2] <= 0 or values[3] <= 0 or values[0]+values[2] > 1 or values[1]+values[3] > 1:
                raise ValueError(_tr("Área de reconhecimento inválida"))
            return values
        extra=[]; minimap=[]
        for entry in data.get("extra_terrain",[]):
            transform=np.asarray(entry["world_to_image"],dtype=np.float64)
            if transform.shape!=(2,3) or not np.isfinite(transform).all() or abs(np.linalg.det(transform[:,:2]))<1e-10:
                raise ValueError(_tr("Transformação de referência adicional inválida"))
            target=minimap if entry.get('surface')=='minimap' else extra
            target.append(Terrain(read_image(entry),transform,data["source"]))
        return ReferencePack(
            Terrain(read_image(data["terrain"]), matrix, data["source"]),
            read_image(data["map_ui"]), read_image(data["gameplay_ui"]),
            roi(data["map_ui"]), roi(data["gameplay_ui"]), tuple(extra),
            region_id,map_id,data["layer"],coordinate_system,tuple(minimap),
        )
    except (KeyError, TypeError, OSError, ValueError, cv2.error) as exc:
        raise ReferenceUnavailable(_tr('Pacote de referência inválido: {0}', exc)) from exc
