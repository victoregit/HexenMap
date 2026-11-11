"""Prepare personal AppSample progress without guessing cross-source marker IDs."""
from src.live.i18n import tr as _tr
from collections import defaultdict
from collections import Counter
from dataclasses import dataclass,asdict
import hashlib
import json
import math
from pathlib import Path

from src.live.catalog import load_catalog
from src.live.storage import write_json


def parse_marker_ids(payload):
    """Accept the observed Firestore batchGet response or a normalized ID export.

    Return only marker IDs. Document names, account IDs, timestamps and other
    fields are deliberately excluded from the personal archive.
    """
    candidates=[]
    if isinstance(payload,dict) and 'markerIds' in payload:
        candidates.append(payload['markerIds'])
    else:
        entries=payload if isinstance(payload,list) else [payload]
        for entry in entries:
            if not isinstance(entry,dict):continue
            found=entry.get('found',{})
            if not isinstance(found,dict):raise ValueError(_tr('Documento Firestore inválido'))
            fields=found.get('fields',{})
            if not isinstance(fields,dict):raise ValueError(_tr('Campos Firestore inválidos'))
            if 'markerIds' not in fields:continue
            value=fields['markerIds']
            if not isinstance(value,dict) or not isinstance(value.get('arrayValue'),dict):
                raise ValueError(_tr('markerIds não é uma lista Firestore'))
            values=value['arrayValue'].get('values',[])
            if not isinstance(values,list):raise ValueError(_tr('Lista markerIds inválida'))
            ids=[]
            for item in values:
                if not isinstance(item,dict) or set(item)!={'stringValue'}:
                    raise ValueError(_tr('ID Firestore fora do formato confirmado'))
                ids.append(item['stringValue'])
            candidates.append(ids)
    if len(candidates)!=1:raise ValueError(_tr('Esperado exatamente um documento de progresso com markerIds'))
    ids=candidates[0]
    if not isinstance(ids,list) or len(ids)>300000:raise ValueError(_tr('Lista de IDs inválida ou grande demais'))
    # Current AppSample official markers use decimal string IDs. Do not coerce
    # numbers, strip prefixes or equate unrelated namespaces by numeric value.
    if any(not isinstance(i,str) or not i.isascii() or not i.isdigit() or len(i)>32 for i in ids):
        raise ValueError(_tr('ID fora do formato decimal confirmado do AppSample'))
    return tuple(sorted(set(ids))),len(ids)-len(set(ids))


def explicit_aliases(community: Path):
    """Retired cross-provider bridge. Personal historical records are never reassigned."""
    return {}


def audit(marker_ids,aliases,duplicates=0):
    matches=[];ambiguous=[];unmatched=[]
    for external in marker_ids:
        targets=aliases.get(external,{})
        if len(targets)==1:
            matches.append({'appsample_id':external,**next(iter(targets.values()))})
        elif targets:ambiguous.append(external)
        else:unmatched.append(external)
    return {'source':'appsample','applied':False,'total_unique':len(marker_ids),'duplicates_removed':duplicates,
            'matched_explicitly':len(matches),'ambiguous':len(ambiguous),'unmatched':len(unmatched),
            'matches':matches,'ambiguous_ids':ambiguous,'unmatched_ids':unmatched,
            'note':'No cross-provider, nearest-position or same-number transfer is applied.'}


def archive_progress(marker_ids,report,directory: Path):
    payload={'source':'appsample','version':1,'markerIds':list(marker_ids)}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    output=directory/digest[:20]
    existing=output/'progress.json'
    if existing.exists():
        if json.loads(existing.read_text(encoding='utf-8'))!=payload:raise ValueError(_tr('Arquivo de importação existente diverge do conteúdo'))
    else:write_json(existing,payload)
    if report is not None:write_json(output/'report.json',{**report,'normalized_sha256':digest})
    return output


@dataclass(frozen=True)
class AppSamplePoint:
    external_id: str
    marker_type: str
    map_id: int
    level: int
    x: float
    y: float
    layer_meta: str

    @property
    def id(self):
        # Source IDs are globally unique, even when a point changes map later.
        return 'appsample:marker:'+self.external_id


def parse_catalog(payload):
    """Decode the observed public v5 column table without executing site code.

    Its signed ID deltas continue across category changes. Coordinates retain
    the source's normalized CRS; they must retain their own projected coordinate system.
    Encoded coordinates require a separately reviewed decoder, not a guess.
    """
    if not isinstance(payload,dict):raise ValueError(_tr('Catálogo AppSample inválido'))
    if payload.get('code',0)!=0:raise ValueError(_tr('Coordenadas codificadas ainda não qualificadas'))
    if payload.get('compressionVersion')!=1:raise ValueError(_tr('Versão de compactação não suportada'))
    encoding=payload.get('encoding',{})
    if not isinstance(encoding,dict) or encoding.get('delta')!=['id']:
        raise ValueError(_tr('Codificação delta não reconhecida'))
    headers=payload.get('headers');data=payload.get('data')
    if (not isinstance(headers,list) or not all(isinstance(h,str) for h in headers)
            or len(set(headers))!=len(headers) or not isinstance(data,dict)
            or not {'id','type','lng','lat'}.issubset(headers)):
        raise ValueError(_tr('Colunas obrigatórias ausentes ou duplicadas'))
    deltas=data.get('id')
    if not isinstance(deltas,list) or len(deltas)>500000:raise ValueError(_tr('Lista de pontos inválida'))
    count=len(deltas)
    for key in headers:
        column=data.get(key)
        if not isinstance(column,list) or len(column)!=count:raise ValueError(_tr('Colunas com tamanhos diferentes'))
    points=[];seen=set();identifier=0
    for index,delta in enumerate(deltas):
        if type(delta) is not int:raise ValueError(_tr('Delta de ID inválido'))
        identifier+=delta
        if not 0<identifier<2**53 or identifier in seen:raise ValueError(_tr('ID inválido ou duplicado no catálogo'))
        seen.add(identifier)
        marker_type=data['type'][index]
        if not isinstance(marker_type,str) or not marker_type or len(marker_type)>128:
            raise ValueError(_tr('Tipo de marcador inválido'))
        x,y=data['lng'][index],data['lat'][index]
        if (type(x) not in (int,float) or type(y) not in (int,float)
                or not math.isfinite(x) or not math.isfinite(y)):
            raise ValueError(_tr('Coordenada inválida'))
        map_id=data['mid'][index] if 'mid' in headers else 0
        level=data['level'][index] if 'level' in headers else 0
        if type(map_id) is not int or map_id<0 or type(level) is not int or level<0:
            raise ValueError(_tr('Mapa ou nível inválido'))
        layer=data['meta'][index] if 'meta' in headers else ''
        if not isinstance(layer,str):raise ValueError(_tr('Metadados de camada inválidos'))
        points.append(AppSamplePoint(str(identifier),marker_type,map_id,level,float(x),float(y),layer))
    return points


CHEST_TYPES={'o17':'common-chest','o44':'exquisite-chest','o45':'precious-chest',
             'o46':'luxurious-chest','o269':'remarkable-chest'}


def resolve_catalog_progress(marker_ids,points):
    lookup={point.external_id:point for point in points}
    if len(lookup)!=len(points):raise ValueError(_tr('IDs duplicados no catálogo'))
    resolved=[lookup[identifier] for identifier in marker_ids if identifier in lookup]
    missing=[identifier for identifier in marker_ids if identifier not in lookup]
    chest_counts=Counter(CHEST_TYPES[p.marker_type] for p in resolved if p.marker_type in CHEST_TYPES)
    return {'source':'appsample','applied':False,'coordinate_system':'appsample-normalized-v5',
            'runtime_ready':False,'total_unique':len(marker_ids),'catalog_points':len(points),
            'resolved':len(resolved),'missing':len(missing),'missing_ids':missing,
            'resolved_chests':sum(chest_counts.values()),'chests_by_type':dict(chest_counts),
            'resolved_by_map':dict(Counter(str(p.map_id) for p in resolved)),
            'collection_timestamp':None,
            'records':[{'id':p.id,**asdict(p)} for p in resolved],
            'note':'Exact AppSample IDs only. Map IDs, coordinates and layer metadata retain the source system. Native-map reference calibration and source selection are required before rendering. Missing IDs remain in the original progress archive.'}


def archive_catalog_progress(marker_ids,report,catalog_path: Path,directory: Path,source_url: str):
    # The public catalog stays in the personal archive, never in the executable.
    output=archive_progress(marker_ids,None,directory)
    raw=catalog_path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    catalog_name='catalog-'+digest[:16]+'.json'
    target=output/catalog_name
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError(_tr('Catálogo arquivado foi alterado'))
    else:
        temporary=target.with_suffix('.json.tmp');temporary.write_bytes(raw);temporary.replace(target)
    write_json(output/'source-progress.json',report)
    write_json(output/'SOURCE.json',{
        'source':'AppSample personal progress preparation','catalog_url':source_url,
        'catalog_file':catalog_name,'catalog_sha256':digest,
        'coordinate_system':'appsample-normalized-v5',
        'usage':'Personal local processing only; no general data redistribution permission established',
        'source_id_namespace':'appsample:marker:','runtime_ready':False})
    return output
