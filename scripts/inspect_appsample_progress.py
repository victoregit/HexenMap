"""Archive a user's AppSample export and report proven ID matches; never modify saves."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.appsample_import import (parse_marker_ids,explicit_aliases,audit,archive_progress,
    parse_catalog,resolve_catalog_progress,archive_catalog_progress)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--catalog',type=Path,help='Reviewed public compressed AppSample catalog saved locally')
    parser.add_argument('--catalog-url',default='',help='Exact source URL retained in the personal provenance manifest')
    args=parser.parse_args()
    if args.input.stat().st_size>16*1024*1024:raise ValueError('Arquivo maior que o limite de 16 MiB')
    progress=ROOT/'userData/progress.json'
    before=hashlib.sha256(progress.read_bytes()).hexdigest() if progress.exists() else None
    ids,duplicates=parse_marker_ids(json.loads(args.input.read_text(encoding='utf-8-sig')))
    if args.catalog:
        if args.catalog.stat().st_size>64*1024*1024:raise ValueError('Catálogo maior que 64 MiB')
        points=parse_catalog(json.loads(args.catalog.read_text(encoding='utf-8-sig')))
        report=resolve_catalog_progress(ids,points)
        directory=archive_catalog_progress(ids,report,args.catalog,ROOT/'userData/imports/appsample',args.catalog_url)
        fields=('applied','total_unique','catalog_points','resolved','missing','resolved_chests','runtime_ready')
    else:
        aliases=explicit_aliases(ROOT/'data/community')
        report=audit(ids,aliases,duplicates)
        directory=archive_progress(ids,report,ROOT/'userData/imports/appsample')
        fields=('applied','total_unique','matched_explicitly','ambiguous','unmatched')
    after=hashlib.sha256(progress.read_bytes()).hexdigest() if progress.exists() else None
    assert before==after,'O progresso principal mudou durante a conferência'
    print(json.dumps({key:report[key] for key in fields}))
    print(directory)


if __name__=='__main__':main()
