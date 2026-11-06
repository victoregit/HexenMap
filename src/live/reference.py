"""Explicit georeferenced image packs; missing artwork never becomes mock terrain."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


class ReferenceUnavailable(ValueError):
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


def load_pack(directory: Path) -> ReferencePack:
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        raise ReferenceUnavailable("Referência visual de Mondstadt ainda não instalada e validada.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data,dict):
            raise ValueError("Manifesto deve ser um objeto JSON")
        if data["region"] != "mondstadt" or data["layer"] != "surface":
            raise ValueError("O pacote deve corresponder à superfície de Mondstadt")
        if data["coordinate_system"] != "leaflet-simple-z7":
            raise ValueError("Sistema de coordenadas incompatível")
        if not data.get("permission", {}).get("evidence") or not data["permission"].get("usage"):
            raise ValueError("Falta a origem e a permissão de uso das referências")

        def read_image(entry: dict) -> np.ndarray:
            if not isinstance(entry,dict):
                raise ValueError("Metadados de imagem inválidos")
            path = (directory / entry["file"]).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError("Referência fora da pasta do pacote")
            raw = path.read_bytes()
            if not raw or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(f"Referência alterada: {path.name}")
            image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if image is None or min(image.shape[:2]) < 12:
                raise ValueError(f"Imagem inválida: {path.name}")
            return image

        matrix = np.asarray(data["world_to_image"], dtype=np.float64)
        if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
            raise ValueError("Transformação geográfica inválida")
        if abs(np.linalg.det(matrix[:, :2])) < 1e-10:
            raise ValueError("Transformação geográfica singular")
        def roi(entry: dict) -> tuple:
            values = tuple(float(v) for v in entry["roi"])
            if len(values) != 4 or not all(0 <= v <= 1 for v in values) or values[2] <= 0 or values[3] <= 0 or values[0]+values[2] > 1 or values[1]+values[3] > 1:
                raise ValueError("Área de reconhecimento inválida")
            return values
        extra=[]
        for entry in data.get("extra_terrain",[]):
            transform=np.asarray(entry["world_to_image"],dtype=np.float64)
            if transform.shape!=(2,3) or not np.isfinite(transform).all() or abs(np.linalg.det(transform[:,:2]))<1e-10:
                raise ValueError("Transformação de referência adicional inválida")
            extra.append(Terrain(read_image(entry),transform,data["source"]))
        return ReferencePack(
            Terrain(read_image(data["terrain"]), matrix, data["source"]),
            read_image(data["map_ui"]), read_image(data["gameplay_ui"]),
            roi(data["map_ui"]), roi(data["gameplay_ui"]), tuple(extra),
        )
    except (KeyError, TypeError, OSError, ValueError, cv2.error) as exc:
        raise ReferenceUnavailable(f"Pacote de referência inválido: {exc}") from exc
