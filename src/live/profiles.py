"""Named local progress profiles; the original save stays in place as Principal."""
import copy
import json
from pathlib import Path
import re
import shutil
import uuid

from src.live.personal_state import StateRecoveryRequired,prepare_state
from src.live.storage import write_json
from src.progress.progress_manager import ProgressManager


class ProfileStore:
    def __init__(self,root):
        self.root=Path(root);self.path=self.root/'profiles.json'
        if self.path.exists():
            try:
                self.data=json.loads(self.path.read_text(encoding='utf-8-sig'))
                self.validate(self.data)
            except (ValueError,KeyError,TypeError,OSError) as exc:
                raise StateRecoveryRequired('O índice de perfis está inválido. Recupere profiles.json ou seu backup; nenhum perfil foi substituído.') from exc
        else:
            if self.path.with_suffix('.json.bak').exists():
                raise StateRecoveryRequired('O índice de perfis está ausente. Recupere profiles.json.bak antes de continuar.')
            self.data={'version':1,'active':'default','profiles':[{'id':'default','name':'Principal'}]}
            self._write(self.data)

    @staticmethod
    def validate(data):
        if not isinstance(data,dict) or data.get('version')!=1:raise ValueError('Índice inválido')
        rows=data['profiles']
        if not isinstance(rows,list) or not rows:raise ValueError('Perfis ausentes')
        ids=set();names=set()
        for row in rows:
            identifier=row['id'];name=ProfileStore.clean_name(row['name'])
            if identifier!='default' and not re.fullmatch(r'[a-f0-9]{32}',identifier):raise ValueError('ID inválido')
            if identifier in ids or name.casefold() in names:raise ValueError('Perfil duplicado')
            ids.add(identifier);names.add(name.casefold())
        if 'default' not in ids or data['active'] not in ids:raise ValueError('Perfil ativo inválido')

    @staticmethod
    def clean_name(name):
        if not isinstance(name,str):raise ValueError('Nome inválido')
        name=name.strip()
        if not name or len(name)>40 or any(ord(c)<32 for c in name):
            raise ValueError('Use um nome de 1 a 40 caracteres.')
        return name

    @property
    def active(self):return self.data['active']

    @property
    def profiles(self):return copy.deepcopy(self.data['profiles'])

    def name(self,identifier=None):
        return next(row['name'] for row in self.data['profiles'] if row['id']==(identifier or self.active))

    def directory(self,identifier):
        if identifier not in {row['id'] for row in self.data['profiles']}:raise ValueError('Perfil desconhecido')
        directory=self.root if identifier=='default' else self.root/'profiles'/identifier
        if not directory.resolve().is_relative_to(self.root.resolve()):raise ValueError('Perfil fora da pasta de saves')
        return directory

    def open_progress(self,identifier=None):
        directory=self.directory(identifier or self.active)
        if not any((directory/name).is_file() for name in ('progress.json','progress.json.bak')):
            raise StateRecoveryRequired('O save deste perfil está ausente. Restaure um backup; nenhum progresso vazio foi criado.')
        return ProgressManager(str(directory/'progress.json'))

    def _write(self,data):
        self.validate(data)
        if self.path.exists():
            try:
                current=json.loads(self.path.read_text(encoding='utf-8-sig'));self.validate(current)
            except (ValueError,KeyError,TypeError,OSError) as exc:
                raise StateRecoveryRequired('O índice de perfis foi alterado ou corrompido. Recupere-o antes de continuar.') from exc
            if current!=self.data:raise StateRecoveryRequired('Os perfis foram alterados fora do app. Reinicie antes de continuar.')
            shutil.copy2(self.path,self.path.with_suffix('.json.bak'))
        elif self.path.with_suffix('.json.bak').exists():
            raise StateRecoveryRequired('O índice de perfis desapareceu. Recupere o backup antes de continuar.')
        write_json(self.path,data)
        self.data=data

    def activate(self,identifier):
        self.open_progress(identifier)
        data=copy.deepcopy(self.data);data['active']=identifier;self._write(data)

    def create(self,name):
        name=self.clean_name(name)
        if name.casefold() in {r['name'].casefold() for r in self.data['profiles']}:
            raise ValueError('Já existe um perfil com esse nome.')
        identifier=uuid.uuid4().hex
        directory=self.root/'profiles'/identifier
        if not directory.resolve().is_relative_to(self.root.resolve()):raise ValueError('Pasta de perfis inválida')
        prepare_state(destination=directory,legacy_roots=[],allow_new=True)
        data=copy.deepcopy(self.data);data['profiles'].append({'id':identifier,'name':name})
        self._write(data)
        return identifier

    def rename(self,identifier,name):
        self.directory(identifier);name=self.clean_name(name)
        if any(r['id']!=identifier and r['name'].casefold()==name.casefold() for r in self.data['profiles']):
            raise ValueError('Já existe um perfil com esse nome.')
        data=copy.deepcopy(self.data)
        next(r for r in data['profiles'] if r['id']==identifier)['name']=name
        self._write(data)
