"""Offline, versioned presentation overrides; never changes marker identity or rules."""
from functools import lru_cache
from html.parser import HTMLParser
import copy
import json
from pathlib import Path
import re

from src.live.storage import bundle_dir

PENDING='Identificação pendente'
RESOURCE_SUBGROUPS=('Especialidades locais','Plantas e ingredientes','Minérios','Madeiras','Pesca e animais','Outros materiais')


class SelectorParser(HTMLParser):
    """Read accessible text next to icons, including compact buttons with empty alt."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.group='';self.heading=None;self.button=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('h2','h3'):self.heading=[]
        if tag=='button':self.button={'text':[],'title':attrs.get('title',''),'icon':None}
        if tag=='img' and self.button is not None:
            url=attrs.get('src',attrs.get('data-src',''))
            match=re.search(r'/(o\d+)\.(?:png|webp)',url)
            if match:self.button['icon']=(match[1],url,attrs.get('alt',''))

    def handle_data(self,text):
        if self.heading is not None:self.heading.append(text)
        if self.button is not None:self.button['text'].append(text)

    def handle_endtag(self,tag):
        if tag in ('h2','h3') and self.heading is not None:
            self.group=' '.join(''.join(self.heading).split());self.heading=None
        if tag=='button' and self.button is not None:
            button=self.button;self.button=None
            if button['icon']:
                identity,url,alt=button['icon']
                title=re.sub(r'\s*\(\d+\)\s*$','',button['title'])
                text=' '.join(''.join(button['text']).split())
                label=alt.strip() or title.strip() or re.sub(r'\s+\d+(?:\s*/\s*\d+)?\s*$','',text)
                self.rows.append({'source_type':identity,'label':label,'group':self.group,'icon_url':url})


def parse_selector(html):
    parser=SelectorParser();parser.feed(html);parser.close();return parser.rows


@lru_cache(maxsize=1)
def presentation_catalog():
    path=bundle_dir()/'data/localization/appsample-pt-BR.json'
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema')!=1 or data.get('locale')!='pt-BR' or not isinstance(data.get('entries'),dict):return {}
        return data['entries']
    except (OSError,ValueError):return {}


def localized_metadata(metadata,entries=None):
    """Pure enrichment is safe in catalog workers; registration stays on UI thread."""
    entries=presentation_catalog() if entries is None else entries
    result=copy.deepcopy(metadata)
    for category,meta in result.items():
        source_type=meta.get('source_type')
        if not source_type and re.fullmatch(r'as-o\d+',category):source_type=category[3:]
        entry=entries.get(source_type)
        if not isinstance(entry,dict):continue
        aliases=[meta.get('name',''),meta.get('source_name',''),*entry.get('aliases',[])]
        meta['aliases']=list(dict.fromkeys(s for s in aliases if isinstance(s,str) and s))
        meta['presentation_status']=entry.get('status','pending')
        meta['subgroup']=entry.get('subgroup')
        # Keep source_name intact: a translated label must not merge source types.
        meta['source_group']=meta.get('source_group',meta.get('group'))
        if entry.get('status')=='confirmed' and entry.get('name_pt'):
            meta.update(name=entry['name_pt'],group=entry['group'],translation_reviewed=True,
                        presentation_reviewed=True)
        else:
            meta.update(name=f'Tipo não identificado ({source_type})',group=PENDING,
                        translation_reviewed=False,presentation_reviewed=False)
    return result
