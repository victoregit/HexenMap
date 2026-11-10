"""Personal saves live outside versioned program folders. Never guess between saves."""
from pathlib import Path
import hashlib
import json
import os
import shutil

from src.live.storage import install_dir, write_json


class StateRecoveryRequired(RuntimeError):
    pass


class NewProfileRequired(StateRecoveryRequired):
    pass


class OpeningCancelled(RuntimeError):
    """An explicit cancellation ends startup without creating a save."""


class AmbiguousProfilesRequired(StateRecoveryRequired):
    pass


def state_directory(home=None):
    home=Path(home) if home is not None else install_dir()
    pointer=home/'state-dir.txt'
    if pointer.exists():
        target=Path(pointer.read_text(encoding='utf-8-sig').strip())
        if not target.is_absolute():
            raise StateRecoveryRequired('Caminho de saves inválido. Nenhuma coleta será gravada.')
        return target
    base=os.environ.get('LOCALAPPDATA')
    if not base:
        raise StateRecoveryRequired('Não foi possível localizar os dados pessoais do usuário.')
    return Path(base)/'HexenMap'/'state'


def read_progress(path):
    raw=path.read_bytes()
    data=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data,dict) or data.get('version',1) not in (1,2):
        raise ValueError('Versão de progresso inválida')
    records=data.get('records')
    if not isinstance(records,(dict,list)) or not isinstance(data.get('metadata',{}),dict):
        raise ValueError('Formato de progresso inválido')
    if 'collected_count' in data and (type(data['collected_count']) is not int or data['collected_count']!=len(records)):
        raise ValueError('Contagem de progresso inválida')
    if isinstance(records,dict) and any(not isinstance(k,str) or not isinstance(v,dict) for k,v in records.items()):
        raise ValueError('Registros inválidos')
    if isinstance(records,list) and any(not isinstance(k,str) for k in records):
        raise ValueError('IDs inválidos')
    return raw,data


def prepare_state(home=None, destination=None, legacy_roots=None, allow_new=False):
    home=Path(home) if home is not None else install_dir()
    target=Path(destination) if destination is not None else state_directory(home)
    target.mkdir(parents=True,exist_ok=True)
    progress=target/'progress.json'
    marker=target/'initialized.json'
    if progress.exists() or (target/'progress.json.bak').exists():
        # Existing canonical state is authoritative, including explicit uncollections.
        # ProgressManager validates/recoveries it; do not resurrect old installations.
        if not marker.exists():write_json(marker,{'version':1})
        return target
    if any(target.iterdir()):
        raise StateRecoveryRequired(f'O save pessoal está ausente em {target}. Restaure um backup; não será criado um progresso vazio.')
    roots=list(legacy_roots) if legacy_roots is not None else [home/'userData']
    if legacy_roots is None and os.environ.get('LOCALAPPDATA'):
        roots.append(Path(os.environ['LOCALAPPDATA'])/'Programs'/'Hexen Map'/'userData')
    # Daily/import backups are also evidence of prior use. Never hide them behind
    # a newly created empty profile when the primary and immediate backup vanished.
    expanded=[]
    for root in (Path(p) for p in roots):
        if root.is_dir() and not any((root/name).exists() for name in ('progress.json','progress.json.bak')):
            backups=sorted(root.glob('progress.json*.bak'))
            if backups:
                expanded.extend(backups);continue
            if any((root/name).exists() for name in ('initialized.json','profiles.json','profiles.json.bak')):
                raise StateRecoveryRequired(f'Há sinais de uso anterior em {root}, mas o save está ausente. Recupere um backup antes de continuar.')
        expanded.append(root)
    roots=expanded
    candidates=[]
    for root in dict.fromkeys(Path(p).resolve() for p in roots):
        primary=root/'progress.json'
        paths=[root] if root.is_file() else [p for p in (primary,root/'progress.json.bak') if p.exists()]
        if not paths:continue
        chosen=None
        for path in paths:
            try:
                raw,data=read_progress(path)
                chosen=(path,raw,data)
                break
            except (OSError,ValueError,UnicodeError):
                continue
        if chosen is None:
            raise StateRecoveryRequired(f'Progresso anterior inválido em {root}. Recupere o arquivo antes de continuar.')
        candidates.append(chosen)
    nonempty=[row for row in candidates if row[2]['records']]
    fingerprints={json.dumps(row[2]['records'],sort_keys=True,ensure_ascii=False) for row in nonempty}
    if len(fingerprints)>1:
        locations='; '.join(str(row[0]) for row in nonempty)
        raise AmbiguousProfilesRequired('Há saves diferentes. Escolha qual recuperar antes de continuar: '+locations)
    chosen=(nonempty or candidates or [None])[0]
    if chosen is not None:
        source,raw,data=chosen
        backup=target/'migration-backups'/hashlib.sha256(raw).hexdigest()
        backup.mkdir(parents=True,exist_ok=True)
        if not (backup/'progress.json').exists():shutil.copy2(source,backup/'progress.json')
        # Exclusive creation prevents an initialization race from replacing a save.
        with progress.open('xb') as output:
            output.write(raw);output.flush();os.fsync(output.fileno())
        shutil.copy2(progress,target/'progress.json.bak')
        settings=source.parent/'settings.json'
        if settings.exists() and not (target/'settings.json').exists():
            shutil.copy2(settings,target/'settings.json')
    else:
        if not allow_new:
            raise NewProfileRequired('Nenhum save anterior encontrado. Escolha importar suas marcações ou iniciar um perfil novo explicitamente.')
        write_json(progress,{'version':2,'records':{},'metadata':{},'collected_count':0})
        shutil.copy2(progress,target/'progress.json.bak')
    write_json(marker,{'version':1,'migrated_from':str(chosen[0]) if chosen else None})
    return target


def prepare_state_interactive(home=None):
    try:
        # A clean first download needs no import question. Existing saves and all
        # signs of previous use are checked before automatic initialization.
        return prepare_state(home,allow_new=True)
    except AmbiguousProfilesRequired as recovery:
        import tkinter as tk
        from src.live import alerts as messagebox
        root=tk.Tk();root.withdraw()
        try:
            messagebox.showinfo('Saves diferentes encontrados',
                str(recovery)+'\n\nSelecione o progresso correto. Cancelar encerra o aplicativo sem modificar suas marcações.',parent=root)
            selected=messagebox.select_progress(root)
            if not selected:
                raise OpeningCancelled('Recuperação cancelada. Nenhum save vazio foi criado.')
            return prepare_state(home,legacy_roots=[Path(selected)])
        finally:
            root.destroy()
