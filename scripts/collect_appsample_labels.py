"""Extract public selector labels from a saved HTML page, never account progress."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.localization import parse_selector


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',type=Path,required=True)
    parser.add_argument('--source-url',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.source_url.startswith('https://genshin-impact-map.appsample.com/'):
        raise ValueError('Use somente uma página pública do AppSample')
    raw=args.html.read_bytes();rows=parse_selector(raw.decode('utf-8-sig'))
    if not rows:raise ValueError('Nenhum seletor encontrado; não sobrescrever os nomes existentes')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'url':args.source_url,'html_sha256':hashlib.sha256(raw).hexdigest(),
        'labels':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(rows)} rótulos; {sum(not r["label"] for r in rows)} nomes pendentes')


if __name__=='__main__':main()
