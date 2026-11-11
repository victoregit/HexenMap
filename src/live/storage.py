"""Stable installation-relative portable storage, independent of working directory."""
from __future__ import annotations

from src.live.i18n import tr as _tr
import json
import shutil
import os
from pathlib import Path
import sys
import tempfile
import copy
import queue
import threading


DEFAULT_KEYS = {"visibility": "Ctrl+Alt+F12", "collect": "F9", "undo": "F10", "panel": "F8"}
HOTKEY_OPTIONS=tuple([f"F{i}" for i in range(6,13)]+[f"Ctrl+Alt+F{i}" for i in range(6,13)])


def parse_hotkey(value: str) -> tuple[int,int]:
    if value not in HOTKEY_OPTIONS:
        raise ValueError(_tr("Atalho inválido"))
    key=value.split("+")[-1]
    return 0x6f+int(key[1:]),0x4000 | (0x3 if value.startswith("Ctrl+Alt+") else 0)


def install_dir() -> Path:
    if not getattr(sys,'frozen',False):return Path(__file__).resolve().parents[2]
    directory=Path(sys.executable).parent
    # A developer's dist executable is an update artifact, not a new portable
    # installation. Resolve only this explicit repository layout; ordinary
    # portable folders remain independent and never inherit another's progress.
    repository=directory.parent
    if (directory.name.casefold()=='dist' and (repository/'.git').exists()
            and (repository/'HexenMap.spec').is_file()
            and (repository/'userData/catalogs/appsample/SOURCE.json').is_file()):
        return repository
    return directory


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


class PreferenceWriter:
    """One ordered writer; coalesce pending snapshots, never reorder saves."""
    def __init__(self, path, write=write_json):
        self.path=path;self.write=write
        self.condition=threading.Condition();self.pending=None;self.closed=False
        self.generation=0;self.last_written=0;self.errors=queue.Queue()
        self.thread=threading.Thread(target=self._run,name='OverlayPreferences',daemon=True)
        self.thread.start()

    def request(self, settings):
        snapshot=copy.deepcopy(settings)
        with self.condition:
            if self.closed:raise RuntimeError(_tr('Gravador de preferências encerrado'))
            self.generation+=1
            self.pending=(self.generation,snapshot)
            self.condition.notify()

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:self.pending is not None or self.closed)
                if self.pending is None:return
                generation,snapshot=self.pending;self.pending=None
            try:
                self.write(self.path,snapshot)
                self.last_written=generation
            except Exception as exc:
                self.errors.put((generation,str(exc)))

    def close(self):
        with self.condition:self.closed=True;self.condition.notify_all()
        self.thread.join(timeout=5)
        return not self.thread.is_alive() and self.last_written==self.generation


def read_settings(path: Path) -> dict:
    defaults = {"categories": [], "hotkeys": dict(DEFAULT_KEYS), "performance_mode": "light", "automark":False,"tracking_mode":"auto"}
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
            return defaults
        keys = data.get("hotkeys", {})
        retired_navigation=isinstance(keys,dict) and bool({'farm','farm_next'} & keys.keys())
        if retired_navigation:
            backup=path.with_name(path.name+'.pre-no-compass.bak')
            if not backup.exists():shutil.copy2(path,backup)
            keys={k:v for k,v in keys.items() if k not in {'farm','farm_next'}}
        if (isinstance(keys,dict) and set(keys) in ({"visibility","collect","undo"},{"visibility","collect","undo","panel"})
                and all(isinstance(v,str) and v in HOTKEY_OPTIONS for v in keys.values())
                and len(set(keys.values()))==len(keys)):
            keys=dict(keys)
            for action in ('panel',):
                if action not in keys:
                    candidates=('F8','F7','F6','Ctrl+Alt+F8',*HOTKEY_OPTIONS) if action=='panel' else (DEFAULT_KEYS[action],*HOTKEY_OPTIONS)
                    keys[action]=next(k for k in candidates if k not in keys.values())
        if not isinstance(keys, dict) or set(keys) != set(DEFAULT_KEYS):
            keys = dict(DEFAULT_KEYS)
        allowed = set(HOTKEY_OPTIONS)
        if not all(isinstance(value,str) and value in allowed for value in keys.values()) or len(set(keys.values())) != len(DEFAULT_KEYS):
            keys = dict(DEFAULT_KEYS)
        result={"categories": [v for v in data["categories"] if isinstance(v, str)], "hotkeys": keys}
        # Keep the internal bounded backend; old preferences must not preload maps.
        result['performance_mode']='light'
        result['tracking_mode']='manual' if data.get('tracking_mode')=='manual' else 'auto'
        scope=data.get('resolved_scope')
        if isinstance(scope,list) and len(scope)==2 and all(isinstance(v,str) for v in scope):result['resolved_scope']=scope
        result['capture_visible']=data.get('capture_visible') is True
        result['automark']=data.get('automark') is True
        if isinstance(data.get("regional"),dict):
            result["regional"]={}
            for key,pref in data['regional'].items():
                if not isinstance(key,str) or not isinstance(pref,dict): continue
                categories=pref.get('categories',[])
                result['regional'][key]={
                    'categories':[c for c in categories if isinstance(c,str)] if isinstance(categories,list) else [],
                    'area':None,
                    'layer':pref.get('layer') if isinstance(pref.get('layer'),str) else 'teyvat / surface'}
        if isinstance(data.get("package"),str): result["package"]=data["package"]
        result["server"]="America"
        panel=data.get("panel",{})
        if isinstance(panel,dict):
            result["panel"]={"collapsed":panel.get("collapsed") is True,
                             "detached":panel.get('detached') is not False}
            for key in ("x","y","width","height"):
                if isinstance(panel.get(key),int): result["panel"][key]=panel[key]
            if 'scale' in panel:result['panel']['scale']=panel['scale'] if panel['scale'] in (100,125,150) else 100
        regional_data=data.get('regional',{})
        retired=(data.get('package') not in (None,'appsample') or 'last_kongying_package' in data
                 or (isinstance(regional_data,dict) and any(k!='appsample' for k in regional_data)))
        if retired:
            backup=path.with_name(path.name+'.pre-appsample-only.bak')
            if not backup.exists():shutil.copy2(path,backup)
            result['package']='appsample'
            result['regional']={k:v for k,v in result.get('regional',{}).items() if k=='appsample'}
            if data.get('package')!='appsample':result['categories']=result['regional'].get('appsample',{}).get('categories',[])
            write_json(path,result)
        # Back up the original bytes once before retiring hidden area filters.
        regional=data.get("regional",{})
        if isinstance(regional,dict) and any(isinstance(v,dict) and v.get("area") for v in regional.values()):
            backup=path.with_name(path.name+".pre-nation-layer.bak")
            try:
                if not backup.exists(): shutil.copy2(path,backup)
                write_json(path,result)
            except OSError as exc:
                raise RuntimeError(_tr("Não foi possível preservar as preferências antes da migração")) from exc
        if retired_navigation:write_json(path,result)
        return result
    except (ValueError, OSError):
        return defaults
