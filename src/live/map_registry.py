"""Map identities and published tile extents; never derived from marker density."""
from functools import lru_cache
import json
from pathlib import Path

from src.live import i18n
from src.live.storage import bundle_dir, install_dir


@lru_cache(maxsize=1)
def maps():
    data = json.loads((bundle_dir() / 'data/world_map/MAPS.json').read_text(encoding='utf-8'))
    if data.get('schema') != 1:
        raise ValueError('Unsupported map registry')
    result = {}
    for row in data['maps']:
        if row['map_id'] != f"as-map-{row['source_id']}" or row['map_id'] in result:
            raise ValueError('Invalid map identity')
        if not row['source'].startswith('https://game-cdn.appsample.com/gim/'):
            raise ValueError('Invalid map source')
        result[row['map_id']] = row
    return result


def map_name(map_id):
    row = maps().get(map_id)
    return row['names'].get(i18n.get_language(), row['names']['pt-BR']) if row else map_id


def tile_metadata(map_id, layer='surface'):
    row = maps()[map_id]
    overlay=None
    if layer != 'surface':
        overlay=next((l for l in row.get('layers',[]) if l['layer_id']==layer),None)
        if overlay is None:raise ValueError('Unknown map layer')
    b = row['tile_bounds'][str(row['base_zoom'])]
    return dict(row, layer=layer, overlay=overlay,
                bounds_base_tiles=[b['minX'], -b['maxY']-1, b['maxX'], -b['minY']-1], tile_size=256)


def layer_name(map_id,layer):
    from src.live.i18n import tr
    if layer=='surface':return tr('Superfície')
    entry=next((l for l in maps().get(map_id,{}).get('layers',[]) if l['layer_id']==layer),None)
    if entry is None:return layer
    return entry['name']+' · '+tr('Área {0}',entry['area'])


def scope_name(scope):
    return map_name(scope[0])+' · '+layer_name(*scope)


def installed_scopes(root=None):
    root = Path(root) if root is not None else install_dir() / 'userData/references/appsample'
    return [(key,layer) for key,row in maps().items()
            for layer in ['surface',*[l['layer_id'] for l in row.get('layers',[])]]
            if (root / key / layer / 'manifest.json').is_file()]
