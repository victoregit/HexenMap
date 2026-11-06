"""Selected-package loading; coordinate systems are never silently mixed."""
from pathlib import Path
from src.live.catalog import load_catalog
from src.live.territory import load_inventory
from src.live.respawn import load_rules


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
