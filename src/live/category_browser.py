"""A virtual marker list: row count does not translate into Tk widget count."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
import tkinter as tk

from src.live.catalog import CATEGORIES, CATEGORY_GROUPS
from src.live.icons import draw_marker
from src.live.labels import SOURCE_PT, INTERNAL, GROUP_ORDER, normalized, portuguese_label
from src.live.oculus_art import ORDER,category_for,draw_oculus
from src.live.category_art import draw_category_art

BG='#111923';ROW='#1b2734';TEXT='#edf1f5';GOLD='#dfc48d';MUTED='#91a0b2'


@dataclass(frozen=True)
class CategoryEntry:
    key: tuple
    label: str
    group: str
    members: frozenset
    icon: str
    search: str


class CategoryModel:
    def __init__(self, items, metadata):
        available={c for item in items for c in (item.category_ids or (item.category,))}
        buckets={}
        for category in sorted(available):
            fallback=CATEGORIES.get(category,(category,''))[0]
            meta=metadata.get(category,{})
            source=meta.get('source_name',meta.get('name',fallback))
            name=meta.get('name',fallback)
            original_group=meta.get('group',CATEGORY_GROUPS.get(category,'Exploração'))
            label=portuguese_label(name,source)
            group={'Oculi':'Destaques','Seelies':'Enigmas','Desafios':'Enigmas',
                   'Puzzles':'Enigmas','Santuários':'Exploração'}.get(original_group,original_group)
            if source in INTERNAL: group='Etiquetas da fonte'
            if label is None or meta.get('translation_reviewed') is False:
                group='Sem tradução revisada'
                label=source  # Explicit secondary section, never fabricated Portuguese.
            key=(original_group,source)
            if key not in buckets: buckets[key]=[label,group,set(),category]
            buckets[key][2].add(category)
        order={g:i for i,g in enumerate(GROUP_ORDER)}
        self.entries=[CategoryEntry(key,label,group,frozenset(members),icon,
                      normalized(label+' '+key[1]+' '+group))
                      for key,(label,group,members,icon) in buckets.items()]
        self.entries.sort(key=lambda e:(order.get(e.group,99),normalized(e.label)))
        self.by_key={entry.key:entry for entry in self.entries}
        self.membership={c:e.key for e in self.entries for c in e.members}
        self.items=items
        self.scope_key=None

    def counts(self, session):
        scoped=session.scoped_items()
        if self.scope_key!=session._scope_key:
            self.totals=Counter();self.item_entries={}
            for item in scoped:
                keys={self.membership[c] for c in (item.category_ids or (item.category,)) if c in self.membership}
                self.item_entries[item.id]=keys
                self.totals.update(keys)
            self.scope_key=session._scope_key
        collected=Counter()
        for identifier in session.progress.get_collected_ids():
            if identifier in self.item_entries and session.is_collected(identifier):
                collected.update(self.item_entries[identifier])
        return {e.key:(collected[e.key],self.totals[e.key]) for e in self.entries}


def build_count_index(items, membership, rules):
    totals=Counter();entries={};permanent=set();other=set()
    for item in items:
        keys={membership[c] for c in (item.category_ids or (item.category,)) if c in membership}
        entries[item.id]=keys;totals.update(keys)
        rule=rules.get(item.rule_id)
        (permanent if rule and rule.kind=='permanent' else other).add(item.id)
    return totals,entries,permanent,other


class CountIndices:
    """Build static counters without holding the UI; current progress is read on UI."""
    def __init__(self):
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='CategoryCounts')
        self.future=None;self.key=None;self.cache=OrderedDict()

    def get(self, session, model):
        items=session.scoped_items();key=(model,session._scope_key)
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        if key!=self.key:
            if self.future:self.future.cancel()
            self.key=key
            self.future=self.pool.submit(build_count_index,items,model.membership,session.rules)
        if self.future.done():
            result=self.future.result();self.cache[key]=result
            while len(self.cache)>2:self.cache.popitem(last=False)
            return result
        return None

    def close(self):self.pool.shutdown(wait=False,cancel_futures=True)


class CategoryBrowser(tk.Canvas):
    HEIGHT=36

    def __init__(self, parent, changed, **kwargs):
        super().__init__(parent,bg=BG,highlightthickness=0,yscrollincrement=36,**kwargs)
        self.changed=changed;self.model=None;self.rows=[];self.selected=set();self.counts={}
        self.collapsed=set(GROUP_ORDER)-{'Destaques','Baús'}
        self.query='';self.paint_job=None;self.last_range=None
        self.bind('<Configure>',lambda e:self.schedule_paint())
        self.bind('<MouseWheel>',lambda e:self.yview_scroll(-int(e.delta/120),'units'))
        self.bind('<Button-1>',self.click)
        self.bind('<Key-space>',self.activate_focused)
        self.bind('<Return>',self.activate_focused)
        self.bind('<Down>',lambda e:self.move_focus(1))
        self.bind('<Up>',lambda e:self.move_focus(-1))
        self.configure(takefocus=1)
        self.focused=0
        self.tile_column=0
        self.bind('<Left>',lambda e:self.move_tile(-1))
        self.bind('<Right>',lambda e:self.move_tile(1))

    def connect_scrollbar(self, scrollbar):
        def changed(first,last):
            scrollbar.set(first,last)
            value=(first,last)
            if value!=self.last_range: self.last_range=value;self.schedule_paint()
        self.configure(yscrollcommand=changed)

    def set_model(self, model, selected):
        self.model=model;self.selected=set(selected);self.counts={};self.focused=0
        self.rebuild(reset=True)

    def filter(self, query):
        self.query=normalized(query.strip());self.rebuild(reset=True)

    def rebuild(self, reset=False):
        self.rows=[]
        if self.model:
            groups=defaultdict(list)
            for entry in self.model.entries:
                if not self.query or self.query in entry.search: groups[entry.group].append(entry)
            for group,entries in groups.items():
                self.rows.append(('group',group,entries))
                # Existing selections remain discoverable even in secondary sections.
                if group not in self.collapsed or self.query:
                    tiles=sorted((e for e in entries if group=='Destaques' and category_for(e)),key=lambda e:ORDER.index(category_for(e)))
                    for offset in range(0,len(tiles),4):
                        chunk=tiles[offset:offset+4]
                        self.rows.extend((('tiles',chunk,None),('tile-tail',chunk,None)))
                    self.rows.extend(('entry',e,None) for e in entries if e not in tiles)
        self.configure(scrollregion=(0,0,max(1,self.winfo_width()),max(1,len(self.rows)*self.HEIGHT)))
        if reset:self.yview_moveto(0)
        self.schedule_paint()

    def schedule_paint(self):
        # Capture/input timers can keep Tk permanently non-idle during gameplay.
        if self.paint_job is None:self.paint_job=self.after(16,self.paint)

    def paint(self):
        self.paint_job=None;self.delete('all')
        width=max(1,self.winfo_width());top=self.canvasy(0)
        start=max(0,int(top/self.HEIGHT)-1)
        end=min(len(self.rows),int((top+self.winfo_height())/self.HEIGHT)+2)
        for index in range(start,end):
            kind,value,entries=self.rows[index];y=index*self.HEIGHT
            if kind=='tile-tail':continue
            if kind=='tiles':
                cell=width/4
                for column,entry in enumerate(value):
                    left=column*cell+2;right=(column+1)*cell-3;center=(left+right)/2
                    chosen=bool(entry.members & self.selected)
                    focused=index==self.focused and column==self.tile_column and self.focus_get()==self
                    self.create_rectangle(left,y+2,right,y+69,fill='#243344' if chosen else ROW,outline=GOLD if chosen or focused else '#2a3949')
                    draw_oculus(self,entry,center,y+22)
                    self.create_text(center,y+44,text=entry.label,fill=TEXT,font=('Segoe UI',8))
                    count=self.counts.get(entry.key);counter=f'{count[0]}/{count[1]}' if count is not None else '—'
                    self.create_text(center,y+59,text=counter,fill=GOLD if chosen else MUTED,font=('Segoe UI',8))
                    if chosen:self.create_text(right-7,y+10,text='✓',fill=GOLD,font=('Segoe UI',8,'bold'))
                continue
            if kind=='group':
                if value in self.collapsed and not self.query:
                    self.create_polygon(8,y+14,13,y+18,8,y+22,fill=GOLD,outline='')
                else:self.create_polygon(7,y+15,15,y+15,11,y+21,fill=GOLD,outline='')
                active=sum(bool(e.members & self.selected) for e in entries)
                self.create_text(22,y+18,text=value+(f' · {active}' if active else ''),
                                 anchor='w',fill=TEXT,font=('Segoe UI',9,'bold'))
                self.create_text(width-53,y+18,text='Todos',fill=MUTED,font=('Segoe UI',8))
                self.create_text(width-14,y+18,text='×',fill=MUTED,font=('Segoe UI',12))
                continue
            entry=value;chosen=bool(entry.members & self.selected)
            self.create_rectangle(1,y+1,width-2,y+34,fill='#202f3e' if chosen else BG,
                                  outline=GOLD if index==self.focused and self.focus_get()==self else '')
            if not draw_category_art(self,entry.icon,17,y+18):draw_marker(self,entry.icon,17,y+18,scale=.95)
            label=entry.label
            # Ellipsis keeps counters in their own column; full label remains searchable.
            max_chars=max(12,int((width-126)/6.3))
            if len(label)>max_chars:label=label[:max_chars-1]+'…'
            self.create_text(36,y+17,text=label,anchor='w',fill=TEXT,font=('Segoe UI',9))
            count=self.counts.get(entry.key)
            counter=f'{count[0]}/{count[1]}' if count is not None else '—'
            self.create_text(width-34,y+17,text=counter,anchor='e',
                             fill=MUTED,font=('Segoe UI',8))
            self.create_rectangle(width-23,y+11,width-11,y+23,fill=GOLD if chosen else BG,outline=GOLD if chosen else '#465669')
            if chosen:self.create_text(width-17,y+17,text='✓',fill=BG,font=('Segoe UI',9,'bold'))

        if not self.rows:
            self.create_text(width/2,25,text='Carregando catálogo…' if self.model is None else 'Nenhum item encontrado',fill=MUTED,font=('Segoe UI',9))

    def click(self, event):
        self.focus_set()
        index=int(self.canvasy(event.y)/self.HEIGHT)
        if 0<=index<len(self.rows) and self.rows[index][0]=='tile-tail':index-=1
        self.focused=index
        self.tile_column=min(3,max(0,int(event.x*4/max(1,self.winfo_width()))))
        self.activate(index,event.x)

    def activate(self, index, x=0):
        if not 0<=index<len(self.rows):return
        kind,value,entries=self.rows[index]
        if kind in {'tiles','tile-tail'}:
            column=min(3,max(0,int(x*4/max(1,self.winfo_width()))))
            if column<len(value):
                entry=value[column];self.changed(entry.members,not bool(entry.members & self.selected))
            return
        if kind=='group':
            if x>self.winfo_width()-32:
                self.changed(set().union(*(e.members for e in entries)),False)
            elif x>self.winfo_width()-80:
                self.changed(set().union(*(e.members for e in entries)),True)
            else:
                if value in self.collapsed:self.collapsed.remove(value)
                else:self.collapsed.add(value)
                self.rebuild()
        else:self.changed(value.members,not bool(value.members & self.selected))

    def activate_focused(self,event=None):
        tiled=0<=self.focused<len(self.rows) and self.rows[self.focused][0]=='tiles'
        self.activate(self.focused,(self.tile_column+.5)*self.winfo_width()/4 if tiled else 0)

    def move_tile(self,delta):
        if 0<=self.focused<len(self.rows) and self.rows[self.focused][0]=='tiles':
            self.tile_column=max(0,min(len(self.rows[self.focused][1])-1,self.tile_column+delta))
            self.schedule_paint()
        return 'break'

    def move_focus(self, delta):
        self.focused=max(0,min(len(self.rows)-1,self.focused+delta))
        if self.rows and self.rows[self.focused][0]=='tile-tail':self.focused+=1 if delta>0 and self.focused+1<len(self.rows) else -1
        if self.rows and self.rows[self.focused][0]=='tiles':self.tile_column=min(self.tile_column,len(self.rows[self.focused][1])-1)
        if self.rows:
            top=self.canvasy(0);y=self.focused*self.HEIGHT
            if y<top or y+self.HEIGHT>top+self.winfo_height():
                self.yview_moveto(max(0,y-self.winfo_height()/2)/(len(self.rows)*self.HEIGHT))
        self.schedule_paint();return 'break'
