import copy
import json
from pathlib import Path
from types import SimpleNamespace

from src.live.localization import (parse_selector,localized_metadata,presentation_catalog,
                                   RESOURCE_SUBGROUPS,PENDING)
from src.live.category_browser import CategoryModel,CategoryBrowser
from src.live.catalog import Item,CATEGORIES,CATEGORY_GROUPS
from src.live.labels import register_presentation,normalized
from src.live.appsample_catalog import normalized_package
from src.live.appsample_import import AppSamplePoint
from src.live.session import Session
from src.progress.progress_manager import ProgressManager


def test_empty_alt_uses_accessible_label_and_keeps_group_even_without_a_name():
    html='''<section><h2>Material</h2><button title="Menta (502)"><img src="https://example/o161.png?v=3" alt=""><span class="sr-only">Menta</span></button>
    <button><img src="https://example/o99999.png" alt=""></button></section>'''
    rows=parse_selector(html)
    assert rows[0]['label']=='Menta' and rows[0]['source_type']=='o161'
    assert rows[1]['label']=='' and rows[1]['group']=='Material'
    items,categories=normalized_package([AppSamplePoint('1','o99999',2,1,0,0,'')],rows)
    assert categories['as-o99999']['group']=='Recursos'
    assert categories['as-o99999']['translation_reviewed'] is False
    assert items[0]['rule_id']=='unknown'


def test_offline_review_overrides_old_false_flag_without_mutating_source_metadata():
    raw={'as-o161':{'name':'Tipo o161','source_name':'o161','source_type':'o161','group':'Exploração','translation_reviewed':False}}
    before=copy.deepcopy(raw);meta=localized_metadata(raw)
    assert raw==before
    assert meta['as-o161']['name']=='Menta' and meta['as-o161']['translation_reviewed']
    assert meta['as-o161']['subgroup']=='Plantas e ingredientes'
    model=CategoryModel([Item('point','Original','as-o161',10,20)],meta)
    entry=model.entries[0]
    assert entry.group=='Recursos' and entry.members=={'as-o161'}
    assert 'mint' in entry.search and 'menta' in entry.search and 'as-o161' in entry.search


def test_all_inventory_records_have_review_status_and_confirmed_names_have_sources():
    entries=presentation_catalog()
    assert len(entries)==757
    assert sum(e['status']=='pending' for e in entries.values())==40
    for identity,entry in entries.items():
        assert entry['source_type']==identity and entry['checked_at']
        if entry['status']=='confirmed':
            assert entry['name_pt'] and entry['source_urls']
            assert entry['group']!=PENDING
            if entry['group']=='Recursos':assert entry['subgroup'] in RESOURCE_SUBGROUPS
        else:assert entry['reason'] and entry['name_pt'] is None


def test_specialties_take_precedence_over_botanical_or_mining_form():
    entries=presentation_catalog()
    for identity in ('o40','o33','o38','o196'):
        assert entries[identity]['subgroup']=='Especialidades locais'
    assert entries['o161']['subgroup']=='Plantas e ingredientes'
    assert entries['o15']['subgroup']=='Minérios'
    assert entries['o175']['subgroup']=='Madeiras'


def test_pending_types_keep_their_identifier_and_searchable_icon_category():
    raw={'as-o132':{'source_type':'o132','source_name':'o132','name':'Tipo o132','group':'Exploração'}}
    meta=localized_metadata(raw);model=CategoryModel([Item('x','Original','as-o132',0,0)],meta)
    entry=model.entries[0]
    assert entry.group==PENDING and 'o132' in entry.label and entry.icon=='as-o132'


def test_translated_homonyms_keep_independent_source_types_and_selection_ids():
    raw={key:{'source_type':identity,'source_name':'Shared source label','name':'Mesmo nome','group':'Recursos',
        'subgroup':'Outros materiais','presentation_reviewed':True} for key,identity in [('a','o9000'),('b','o9001')]}
    model=CategoryModel([Item('one','Original','a',0,0),Item('two','Original','b',0,0)],raw)
    assert len(model.entries)==2 and {e.key[1] for e in model.entries}=={'o9000','o9001'}


def browser_model():
    raw={'as-o161':{'source_type':'o161','source_name':'o161','name':'Tipo o161','group':'Exploração'},
         'as-o160':{'source_type':'o160','source_name':'o160','name':'Tipo o160','group':'Exploração'},
         'as-o33':{'source_type':'o33','source_name':'o33','name':'Tipo o33','group':'Exploração'}}
    items=[Item('one','Old','as-o161',0,0,category_ids=('as-o161','as-o160')),Item('two','Old','as-o33',0,0)]
    return items,CategoryModel(items,localized_metadata(raw))


def test_subgroups_search_expands_results_without_overwriting_collapsed_state():
    items,model=browser_model();actions=[]
    browser=SimpleNamespace(HEIGHT=36,ui_scale=1.,model=model,rows=[],query='',collapsed=set(),collapsed_subgroups=set(RESOURCE_SUBGROUPS),
        configure=lambda **k:None,winfo_width=lambda:320,yview_moveto=lambda v:None,schedule_paint=lambda:None,
        changed=lambda members,chosen:actions.append((members,chosen)),selected=set())
    browser.rebuild=lambda:CategoryBrowser.rebuild(browser)
    browser.rebuild()
    assert [r[0] for r in browser.rows]==['group','subgroup','subgroup']
    folded=set(browser.collapsed_subgroups)
    browser.query='mint';browser.rebuild()
    assert [r[0] for r in browser.rows]==['group','subgroup','entry']
    assert browser.rows[-1][1].label=='Menta'
    assert browser.collapsed_subgroups==folded
    browser.query='';browser.rebuild()
    CategoryBrowser.activate(browser,2,270)
    assert actions==[({'as-o160','as-o161'},True)]
    assert browser.collapsed_subgroups==folded


def test_counts_deduplicate_markers_and_progress_is_unchanged_by_translation(tmp_path):
    items,model=browser_model();path=tmp_path/'progress.json'
    session=Session(items,ProgressManager(str(path)));session.set_collected('one',True)
    before=path.read_bytes();selected={'as-o161'};session.selected=set(selected)
    counts=model.counts(session)
    assert counts[next(e.key for e in model.entries if e.icon=='as-o161')]==(1,1)
    assert path.read_bytes()==before and session.selected==selected
    original=dict(CATEGORIES);groups=dict(CATEGORY_GROUPS)
    try:
        register_presentation(localized_metadata({'as-o161':{'source_type':'o161','source_name':'o161','name':'Tipo o161','group':'Exploração'}}))
        assert CATEGORIES['as-o161'][0]=='Menta'
    finally:
        CATEGORIES.clear();CATEGORIES.update(original)
        CATEGORY_GROUPS.clear();CATEGORY_GROUPS.update(groups)
