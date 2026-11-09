from pathlib import Path
from types import SimpleNamespace

from src.live.category_browser import CategoryModel
from src.live.catalog import Item, CATEGORIES
from src.live.regions import RegionalCatalog
from src.live.session import Session
from src.live.labels import normalized, portuguese_label
from src.progress.progress_manager import ProgressManager
from src.live.desktop import DesktopApp


def test_exact_source_aliases_merge_without_double_counting_or_changing_ids(tmp_path):
    metadata={key:{'name':'甜甜花','source_name':'甜甜花','group':'Recursos'} for key in ('source:a','source:b')}
    items=[Item('one','Original','source:a',0,0,category_ids=('source:a','source:b')),
           Item('two','Original','source:b',0,0)]
    session=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    model=CategoryModel(items,metadata)
    assert len(model.entries)==1
    entry=model.entries[0]
    assert entry.label=='Flor Doce' and entry.members=={'source:a','source:b'}
    assert model.counts(session)[entry.key]==(0,2)
    session.set_collected('one',True)
    assert model.counts(session)[entry.key]==(1,2)
    assert session.progress.get_collected_ids()=={'one'}
    session.undo()
    assert model.counts(session)[entry.key]==(0,2)


def test_different_source_meanings_are_not_merged_by_translated_label():
    items=[Item('one','Original','a',0,0),Item('two','Original','b',0,0)]
    metadata={key:{'name':'Mesmo texto','source_name':name,'group':'Recursos'} for key,name in [('a','甲'),('b','乙')]}
    assert len(CategoryModel(items,metadata).entries)==2


def test_unreviewed_labels_and_internal_tags_remain_explicit_and_available():
    metadata={'a':{'name':'未知的新条目','source_name':'未知的新条目','group':'Exploração'},
              'b':{'name':'宝箱相关','source_name':'宝箱相关','group':'Baús'}}
    items=[Item('one','Original','a',0,0),Item('two','Original','b',0,0)]
    entries={e.icon:e for e in CategoryModel(items,metadata).entries}
    assert entries['a'].group=='Identificação pendente'
    assert entries['b'].group=='Etiquetas da fonte' and entries['b'].label=='Etiquetas de baús'
    assert normalized('MINÉRIO')=='minerio'


def test_background_package_load_never_registers_or_overwrites_presentation_metadata(tmp_path):
    from tests.appsample_fixture import make_catalog
    catalogs=make_catalog(tmp_path);before=dict(CATEGORIES)
    package=catalogs.load_package('appsample')
    assert CATEGORIES==before and len(package.items)==3
    assert portuguese_label('清水玉','清水玉')=='Jade de Água Pura'


def test_clear_removes_even_selected_hidden_source_tags():
    app=DesktopApp.__new__(DesktopApp)
    app.region_loading=False
    app.session=SimpleNamespace(selected={'a','hidden:tag'})
    calls=[];app.choose_categories=lambda members,value:calls.append((members,value))
    app.set_categories(False)
    assert calls==[({'a','hidden:tag'},False)]


def test_progress_summary_respects_scope_and_immediate_changes(tmp_path):
    items=[Item('a','One','common-chest',0,0),Item('b','Two','common-chest',0,0,region_id='liyue')]
    s=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    s.region_id='mondstadt'
    assert s.progress_summary()==(0,1,0)
    s.set_collected('a',True)
    assert s.progress_summary()==(1,1,0)
    s.region_id='liyue'
    assert s.progress_summary()==(0,1,0)
