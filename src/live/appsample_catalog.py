"""Personal AppSample package in its own projected coordinate system."""
import math
import re
from collections import Counter

from src.live.appsample_import import CHEST_TYPES

SPACE='appsample-webmercator-z14'
WORLD_SIZE=256*2**14
MAP_NAMES={'as-map-2':'Teyvat'}
KNOWN={**{key:(value,{'common-chest':'Baús comuns','exquisite-chest':'Baús sofisticados',
    'precious-chest':'Baús preciosos','luxurious-chest':'Baús luxuosos','remarkable-chest':'Baús extraordinários'}[value],'Baús')
    for key,value in CHEST_TYPES.items()},
    'o5':('anemoculus','Anemoculi','Oculi'),'o6':('geoculus','Geoculi','Oculi'),
    'o194':('electroculus','Electroculi','Oculi'),'o403':('dendroculus','Dendroculi','Oculi'),
    'o508':('hydroculus','Hydroculi','Oculi'),'o626':('pyroculus','Pyroculi','Oculi'),
    'o694':('lunoculus','Lunoculi','Oculi'),'o833':('cryoculus','Cryoculi','Oculi'),
    'o77':('seelie','Seelies','Seelies'),'o64':('time-trial','Desafios de tempo','Desafios'),
    'o8':('as-shrine','Santuários das Profundezas','Santuários')}
GROUPS={'Destaques':'Exploração','Baú':'Baús','Materiais de personagem':'Inimigos',
        'Baú de Enigma':'Puzzles','Mineral':'Recursos','Especialidades Locais':'Recursos',
        'Coleção':'Exploração','Guia':'Exploração','Monstro':'Inimigos','Material':'Recursos',
        'Madeira':'Recursos','Peixe':'Recursos','Animal':'Recursos'}


def project(lng,lat,zoom=14):
    if not math.isfinite(lng+lat) or abs(lat)>=85:raise ValueError('Coordenadas fora da projeção qualificada')
    size=256*2**zoom
    return lng/360*size,-math.asinh(math.tan(math.radians(lat)))/(2*math.pi)*size


def source_layer(meta):
    for part in meta.split(';'):
        if not part.startswith('l='):continue
        values=part[2:].split('|')
        if len(values)!=3:raise ValueError('Camada AppSample fora do formato conferido')
        entrances,group,floor=values
        group=group or '0';floor=floor or '0'
        if not group.isdigit() or not floor.isdigit():raise ValueError('Grupo/andar de camada inválido')
        if int(group) or entrances:
            return f'as-layer-{int(group)}-{int(floor)}'
    return 'surface'


def normalized_package(points,labels):
    lookup={}
    for row in labels:
        match=re.search(r'/((?:o)\d+)\.(?:png|webp)',row.get('url',row.get('icon_url','')))
        if match:
            key=match[1]
            if key not in lookup or not lookup[key].get('label') and row.get('label'):lookup[key]=row
    categories={};items=[]
    for point in points:
        known=KNOWN.get(point.marker_type)
        label=lookup.get(point.marker_type,{})
        category,name,group=known or ('as-'+point.marker_type,label.get('label') or 'Tipo '+point.marker_type,
                                     GROUPS.get(label.get('group'),'Exploração'))
        categories.setdefault(category,{'name':name,'source_name':label.get('label',point.marker_type),
            'group':group,'source_type':point.marker_type,'translation_reviewed':bool(known or label.get('label'))})
        x,y=project(point.x,point.y);layer=source_layer(point.layer_meta)
        # Found progress has no resource collection time. Never start a generic
        # respawn timer or transfer a duration policy from another source.
        rule='permanent' if point.level>=5 and group not in {'Recursos','Inimigos'} else 'unknown'
        items.append({'id':point.id,'name':name,'category':category,'category_ids':[category],
            'x':x,'y':y,'region_id':'appsample','map_id':f'as-map-{point.map_id}',
            'layer_id':layer,'layer_ids':[] if layer=='surface' else [layer],
            'area_id':'unclassified','rule_id':rule,'source_marker_id':int(point.external_id)})
    from src.live.localization import localized_metadata
    return items,localized_metadata(categories)
