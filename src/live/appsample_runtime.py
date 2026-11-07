"""Exact source-ID import; no timestamp or respawn deadline is fabricated."""
import hashlib
import json


def import_records(marker_ids,items):
    known={item.id:item for item in items if item.id.startswith('appsample:marker:')}
    ids=sorted(set(marker_ids));records={};missing=[]
    for external in ids:
        identifier='appsample:marker:'+external
        item=known.get(identifier)
        if item is None:missing.append(external);continue
        records[identifier]={'collected_at':'','rule_id':item.rule_id,
            'notes':'Importado do AppSample; data original da coleta não disponível.'}
    key=hashlib.sha256(json.dumps({'ids':ids,'resolved':sorted(records)},separators=(',',':'),sort_keys=True).encode()).hexdigest()
    return records,missing,key
