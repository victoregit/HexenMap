"""Selected-package loading; coordinate systems are never silently mixed."""
from pathlib import Path
from dataclasses import dataclass
import json
from src.live.catalog import load_catalog
from src.live.territory import load_inventory
from src.live.respawn import load_rules


@dataclass(frozen=True)
class CatalogPackage:
    id: str
    items: list
    region: str
    coordinate_system: str
    categories: dict


class RegionalCatalog:
    def __init__(self, community: Path):
        self.community=community
        self.inventory,self.territories=load_inventory(community/'kongying/inventory.json')
        self.regions={r['id']:r for r in self.inventory['regions']}
        self.rules=load_rules(community/'kongying/respawn-rules.json')

    @staticmethod
    def default_package(reference_root: Path):
        return 'mondstadt' if (reference_root/'kongying/mondstadt/teyvat/surface/manifest.json').is_file() else 'legacy-mondstadt'

    def load(self,identifier):
        if identifier=='legacy-mondstadt':
            return load_catalog(self.community/'mondstadt'),'mondstadt','leaflet-simple-z7'
        region=self.regions[identifier]
        path=(self.community/region['catalog']).resolve()
        if not path.is_relative_to(self.community.resolve()):
            raise ValueError('Pacote regional fora do catálogo')
        return load_catalog(path),identifier,region['coordinate_system']

    def load_package(self, identifier):
        """Read/validate off the UI thread without changing global drawing metadata."""
        if identifier=='legacy-mondstadt':
            path=self.community/'mondstadt'; region='mondstadt';space='leaflet-simple-z7'
        else:
            info=self.regions[identifier]
            path=(self.community/info['catalog']).resolve()
            if not path.is_relative_to(self.community.resolve()):
                raise ValueError('Pacote regional fora do catálogo')
            region=identifier;space=info['coordinate_system']
        items=load_catalog(path,register=False)
        source=json.loads((path/'SOURCE.json').read_text(encoding='utf-8'))
        return CatalogPackage(identifier,items,region,space,source.get('categories',{}))
