"""Stable installation-relative portable storage, independent of working directory."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


DEFAULT_KEYS = {"visibility": "Ctrl+Alt+F12", "collect": "F9", "undo": "F10"}
HOTKEY_OPTIONS=tuple([f"F{i}" for i in range(6,13)]+[f"Ctrl+Alt+F{i}" for i in range(6,13)])


def parse_hotkey(value: str) -> tuple[int,int]:
    if value not in HOTKEY_OPTIONS:
        raise ValueError("Atalho inválido")
    key=value.split("+")[-1]
    return 0x6f+int(key[1:]),0x4000 | (0x3 if value.startswith("Ctrl+Alt+") else 0)


def install_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


def bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", install_dir()))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_settings(path: Path) -> dict:
    defaults = {"categories": [], "hotkeys": dict(DEFAULT_KEYS)}
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
            return defaults
        keys = data.get("hotkeys", {})
        if not isinstance(keys, dict) or set(keys) != set(DEFAULT_KEYS):
            keys = dict(DEFAULT_KEYS)
        allowed = set(HOTKEY_OPTIONS)
        if not all(isinstance(value,str) and value in allowed for value in keys.values()) or len(set(keys.values())) != 3:
            keys = dict(DEFAULT_KEYS)
        return {"categories": [v for v in data["categories"] if isinstance(v, str)], "hotkeys": keys}
    except (ValueError, OSError):
        return defaults
