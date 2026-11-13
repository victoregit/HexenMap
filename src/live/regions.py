"""AppSample-only package loading; other provider IDs remain historical progress only."""
from pathlib import Path
from dataclasses import dataclass
import json
from src.live.catalog import load_catalog
from src.live.territory import TerritoryIndex
from src.live.respawn import PERMANENT,UNKNOWN
from src.live.appsample_catalog import SPACE
from src.live.localization import localized_metadata

@dataclass(frozen=True, slots=True)
class CatalogPackage:
    id: str
    items: list
    region: str
    coordinate_system: str
    categories: dict
    map_names: dict | None = None

class RegionalCatalog:
    def __init__(self,community: Path,personal_root: Path | None=None):
        # Keep the constructor's positional shape for local tools; never read community providers.
        self.community=Path(community)
        self.personal_root=Path(personal_root) if personal_root is not None else None
        self.inventory={'provider':'appsample','version':1,'regions':[], 'maps':[], 'coverage_complete':False}
        self.territories=TerritoryIndex([])
        self.regions={}
        self.rules={'permanent':PERMANENT,'unknown':UNKNOWN}

    @property
    def appsample_available(self):
        return self.personal_root is not None and (self.personal_root/'appsample/SOURCE.json').is_file()

    def accepts(self,identifier):return identifier=='appsample' and self.appsample_available

    @staticmethod
    def default_package(reference_root: Path):return 'appsample'

    def load(self,identifier):
        package=self.load_package(identifier)
        return package.items,package.region,package.coordinate_system

    def load_package(self,identifier):
        if identifier!='appsample':raise ValueError('A única fonte operacional é AppSample')
        if not self.appsample_available:raise ValueError('Catálogo AppSample não encontrado nesta pasta. Para uma instalação nova, extraia o ZIP portátil completo e execute HexenMap.exe dentro dele. Para atualizar, substitua apenas o executável na pasta da instalação anterior e mantenha userData, que contém suas coletas. Não apague seu progresso.')
        path=self.personal_root/'appsample'
        source=json.loads((path/'SOURCE.json').read_text(encoding='utf-8'))
        if source.get('coordinate_system')!=SPACE:raise ValueError('Sistema de coordenadas AppSample incompatível')
        items=load_catalog(path,register=False)
        if any(not i.id.startswith('appsample:marker:') or i.region_id!='appsample' or not i.map_id.startswith('as-map-') for i in items):
            raise ValueError('Catálogo contém identificadores de outra fonte')
        from collections import Counter,defaultdict
        counts=Counter(i.map_id for i in items);layers=defaultdict(set)
        for item in items:layers[item.map_id].update(item.layer_ids or (item.layer_id,))
        self.inventory['maps']=[{'id':key,'region_id':'appsample','item_count':count,'layers':sorted(layers[key]),'coordinate_system':SPACE} for key,count in sorted(counts.items())]
        self.inventory['version']=source.get('version',source.get('snapshot','personal'))
        self.regions={'appsample':{'id':'appsample','name':'AppSample','item_count':len(items),'coordinate_system':SPACE}}
        return CatalogPackage('appsample',items,'appsample',SPACE,localized_metadata(source.get('categories',{})),source.get('map_names',{}))
