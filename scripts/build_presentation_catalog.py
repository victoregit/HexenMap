"""Build reviewed offline names from public selector exports and matched game names."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.live.appsample_catalog import KNOWN
from src.live.localization import PENDING


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def folded(text):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',text.casefold()))


def sources(main,maps):
    rows=defaultdict(list)
    for page in [load(main),*load(maps)]:
        for row in page['labels']:
            if row.get('source_type') and row.get('label'):
                rows[row['source_type']].append({**row,'page_url':page['url']})
    return rows


def classify(kind,en_name,game_type):
    if kind=='Especialidades Locais' or game_type.startswith('Local Specialty'):return 'Recursos','Especialidades locais'
    if kind=='Mineral' or game_type=='Forging Ore':return 'Recursos','Minérios'
    if kind=='Madeira':return 'Recursos','Madeiras'
    if kind in ('Peixe','Animal'):return 'Recursos','Pesca e animais'
    if kind=='Material':
        # These flowers are harvested materials even when used in alchemy.
        flowers={'Mist Flower Corolla','Flaming Flower Stamen','Viparyas','Windrest Flower','Snowball Flower','Nocturnal Blossom','Embercore Flower'}
        if game_type=='Cooking Ingredient' or en_name in flowers:return 'Recursos','Plantas e ingredientes'
        if en_name=='Electro Crystal':return 'Recursos','Minérios'
        return 'Recursos','Outros materiais'
    return {'Baú':'Baús','Baú de Enigma':'Enigmas','Monstro':'Inimigos','Materiais de personagem':'Inimigos',
            'Coleção':'Exploração','Guia':'Exploração','Destaques':'Exploração'}.get(kind,'Exploração'),None


ALIASES={
    'o31':['Copo-de-Leite'],'o33':['Grama do Pequeno Sino'],'o38':['Vidro de Lily'],
    'o185':['Ganoderma do Mar'],'o462':['Pupa de Areia'],'o92':['Boca-de-Dragão'],
    'o500':['Concha Azulada'],'o548':['Lírio Lakelight'],'o549':['Gota de Orvalho Primordial'],
    'o566':['Jade de Água Pura'],'o695':['Flor Noturna'],'o431':['Baga Vermelha'],
}


def build(metadata,pt,en,game,checked):
    pairs=defaultdict(dict)
    for row in game['records']:pairs[row['path']][row['language']]=row
    index=defaultdict(list)
    for path,pair in pairs.items():
        if 'English' in pair and 'Portuguese' in pair and pair['English'].get('id')==pair['Portuguese'].get('id'):
            index[folded(pair['English']['name'])].append(pair)
    entries={}
    for category,old in sorted(metadata.items()):
        identity=old['source_type'];portuguese=pt.get(identity,[]);english=en.get(identity,[])
        base={'source_type':identity,'checked_at':checked,'aliases':ALIASES.get(identity,[])}
        if not portuguese or not english:
            entries[identity]={**base,'status':'pending','name_pt':None,'group':PENDING,'subgroup':None,
                'source_urls':[],'reason':'Ausente nos seletores públicos PT/EN dos sete mapas conferidos; não identificar por imagem.'}
            continue
        # Character-material shortcuts repeat entries. The ordinary source
        # section wins, particularly for regional specialties.
        row=next((r for r in portuguese if r['group']=='Especialidades Locais'),
                 next((r for r in portuguese if r['group']!='Materiais de personagem'),portuguese[0]))
        eng=next((r for r in english if r['group'] not in ('CHARACTER MATERIALS','Character Materials')),english[0])
        name=row['label'];urls={r['page_url'] for r in portuguese+english};basis='appsample_selector_pt'
        folder='animals' if row['group'] in ('Animal','Peixe') else 'enemies' if row['group']=='Monstro' else 'materials'
        matches=[p for p in index.get(folded(eng['label']),[]) if p['English']['path'].startswith(folder+'/')]
        game_type='';game_id=None
        if matches and len({p['Portuguese']['name'] for p in matches})==1:
            match=sorted(matches,key=lambda p:p['English']['path'])[0]
            name=match['Portuguese']['name'];game_type=match['English'].get('type_text','')
            game_id=match['English']['id'];basis='matched_localized_game_name'
            urls.update((match['English']['url'],match['Portuguese']['url']))
        group,subgroup=classify(row['group'],eng['label'],game_type)
        if identity in KNOWN:
            _,name,original=KNOWN[identity]
            group={'Oculi':'Destaques','Desafios':'Enigmas','Seelies':'Enigmas','Santuários':'Exploração'}.get(original,original)
            subgroup=None;basis='reviewed_existing_game_term'
        if identity in ('o33','o160'):
            urls.add('https://wiki.hoyolab.com/pc/genshin/entry/14?lang=pt-pt')
        aliases=list(dict.fromkeys([name,*base['aliases'],*[r['label'] for r in portuguese+english],old.get('name',''),identity]))
        entries[identity]={**base,'status':'confirmed','name_pt':name,'group':group,'subgroup':subgroup,
            'source_group':row['group'],'source_name_en':eng['label'],'name_basis':basis,'game_id':game_id,
            'aliases':[a for a in aliases if a and not re.fullmatch(r'Tipo o\d+',a)],'source_urls':sorted(urls)}
    return {'schema':1,'version':1,'locale':'pt-BR','checked_at':checked,
        'source':'AppSample identity only; localization sources contribute names, never points.',
        'game_names_reference':{'repository':'https://github.com/theBowja/genshin-db','commit':game['commit'],
            'usage':'Matched item names and IDs only; no descriptions, images or coordinates copied.'},'entries':entries}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('userData/catalogs/appsample/SOURCE.json'))
    parser.add_argument('--pt',type=Path,default=Path('build/appsample-labels-pt-current.json'))
    parser.add_argument('--pt-maps',type=Path,default=Path('build/appsample-labels-pt-maps.json'))
    parser.add_argument('--en',type=Path,default=Path('build/appsample-labels-en-current.json'))
    parser.add_argument('--en-maps',type=Path,default=Path('build/appsample-labels-en-maps.json'))
    parser.add_argument('--game-names',type=Path,default=Path('build/localization-research/genshin-db-names.json'))
    parser.add_argument('--checked-at',default='2026-11-08')
    parser.add_argument('--output',type=Path,default=Path('data/localization/appsample-pt-BR.json'))
    args=parser.parse_args()
    data=build(load(args.source)['categories'],sources(args.pt,args.pt_maps),sources(args.en,args.en_maps),load(args.game_names),args.checked_at)
    data['input_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.source,args.pt,args.pt_maps,args.en,args.en_maps,args.game_names)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'categories':len(data['entries']),'statuses':dict(Counter(e['status'] for e in data['entries'].values())),
        'resources':dict(Counter(e['subgroup'] for e in data['entries'].values() if e['group']=='Recursos'))},ensure_ascii=False))


if __name__=='__main__':main()
