"""Audit every installed source type, without reading or changing collection progress."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.regions import RegionalCatalog
from src.live.category_browser import CategoryModel
from src.live.localization import presentation_catalog


def main():
    package=RegionalCatalog(Path('data/community'),Path('userData/catalogs')).load_package('appsample')
    entries=presentation_catalog();model=CategoryModel(package.items,package.categories)
    identities={c:m['source_type'] for c,m in package.categories.items()}
    maps=defaultdict(set);points=Counter()
    for item in package.items:
        identity=identities[item.category];maps[identity].add(item.map_id);points[identity]+=1
    pending=[{'source_type':key,'points':points[key],'maps':sorted(maps[key]),'reason':entry['reason']}
             for key,entry in entries.items() if entry['status']=='pending']
    report={'checked_at':'2026-11-08','version':1,'total_categories':len(identities),
        'confirmed':sum(e['status']=='confirmed' for e in entries.values()),'pending':len(pending),
        'groups':dict(Counter(e.group for e in model.entries)),
        'resource_subgroups':dict(Counter(e.subgroup for e in model.entries if e.group=='Recursos')),
        'pending_entries':pending,'catalog':'../data/localization/appsample-pt-BR.json',
        'notes':['Names/classification only, not live map validation.','No progress files read; no respawn rules modified.']}
    target=Path('docs/LOCALIZATION_REPORT.json');target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='pending_entries'},ensure_ascii=False))


if __name__=='__main__':main()
