"""Check embedded regional catalogs against local references in an isolated install."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=ROOT/'HexenMap.exe')
    args=parser.parse_args()
    work=ROOT/'build/regional-package-check'
    (work/'userData').mkdir(parents=True,exist_ok=True)
    executable=work/'HexenMap.exe'
    shutil.copy2(args.exe,executable)
    inventory=json.loads((ROOT/'data/community/kongying/inventory.json').read_text(encoding='utf-8'))
    rows=[]
    for region in inventory['regions']:
        identifier=region['id']
        settings={'package':identifier,'categories':[],
                  'regional':{identifier:{'categories':[],'layer':'teyvat / surface'}}}
        (work/'userData/settings.json').write_text(json.dumps(settings),encoding='utf-8')
        reference=ROOT/'userData/references/kongying'/identifier/'teyvat/surface'
        result=subprocess.run([str(executable),'--diagnose','--references',str(reference)],
                              capture_output=True,text=True,timeout=90)
        rows.append({'region':identifier,'passed':result.returncode==0,'stdout':result.stdout.strip(),'stderr':result.stderr.strip()})
        print(f"{identifier}: {'PASS' if result.returncode==0 else 'FAIL'}",flush=True)
    (work/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(r['passed'] for r in rows) else 2


if __name__=='__main__':raise SystemExit(main())
