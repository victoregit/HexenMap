"""Audit imported data and personal reference candidates without approving gameplay."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.regions import RegionalCatalog
from src.live.reference import load_pack


def report():
    catalogs=RegionalCatalog(ROOT/'data/community')
    result={'snapshot':catalogs.inventory['snapshot'],'coverage_complete':False,
            'regions':[],'unclassified_region_points':catalogs.inventory['unclassified_region_count'],
            'note':'Personal reference availability is not evidence of live gameplay acceptance.'}
    for region in catalogs.regions:
        items,_,space=catalogs.load(region)
        required={(i.map_id,layer) for i in items for layer in (i.layer_ids or (i.layer_id,))}
        valid=set();invalid=[]
        root=ROOT/'userData/references/kongying'/region
        for candidate in sorted(root.glob('*/*/manifest.json')):
            mapid,layer=candidate.parent.parent.name,candidate.parent.name
            try: load_pack(candidate.parent,region_id=region,map_id=mapid,layer_id=layer,coordinate_system=space)
            except (OSError,ValueError) as exc:
                invalid.append({'map':mapid,'layer':layer,'error':str(exc)});continue
            valid.add((mapid,layer))
        result['regions'].append({'id':region,'items':len(items),'unclassified_area_items':sum(i.area_id=='unclassified' for i in items),
            'reference_candidates':len(valid),'invalid_references':invalid,
            'missing_reference_layers':[{'map':m,'layer':l} for m,l in sorted(required-valid)],
            'maps_live_accepted':[]})
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=report()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'items':sum(r['items'] for r in result['regions']),
                      'reference_candidates':sum(r['reference_candidates'] for r in result['regions']),
                      'invalid_references':sum(len(r['invalid_references']) for r in result['regions']),
                      'coverage_complete':False},indent=2))
