import json
from pathlib import Path

import pytest

from src.live.appsample_import import (parse_marker_ids,explicit_aliases,audit,archive_progress,
    parse_catalog,resolve_catalog_progress,archive_catalog_progress)


def firestore(ids):
    return [{'found':{'name':'private-account-path','fields':{'markerIds':{'arrayValue':{
        'values':[{'stringValue':i} for i in ids]}}}},'readTime':'not-a-collection-date'}]


def test_firestore_export_retains_only_unique_marker_ids(tmp_path):
    ids,duplicates=parse_marker_ids(firestore(['123','17','123']))
    assert ids==('123','17') and duplicates==1
    output=archive_progress(ids,audit(ids,{}),tmp_path)
    payload=json.loads((output/'progress.json').read_text())
    assert payload=={'source':'appsample','version':1,'markerIds':['123','17']}
    assert 'private-account-path' not in (output/'progress.json').read_text()
    assert archive_progress(ids,audit(ids,{}),tmp_path)==output


@pytest.mark.parametrize('value',[{},[{'missing':'document'}],[{'found':None}],[{'found':{'fields':None}}],firestore(['1'])+firestore(['2']),
    {'markerIds':[123]},{'markerIds':['1.2']},{'markerIds':['1','token.value']},{'markerIds':'123'}])
def test_invalid_or_multiple_account_documents_rejected(value):
    with pytest.raises(ValueError):parse_marker_ids(value)


def test_empty_confirmed_export_and_normalized_export():
    assert parse_marker_ids(firestore([]))==((),0)
    assert parse_marker_ids({'markerIds':['001','1']})==(('001','1'),0)


def test_numeric_collision_and_ambiguous_matches_never_transfer():
    aliases={'1':{'one':{'id':'one'}},'2':{'two':{'id':'two'},'other':{'id':'other'}}}
    report=audit(('1','2','999'),aliases)
    assert report['matched_explicitly']==1 and report['ambiguous_ids']==['2']
    assert report['unmatched_ids']==['999'] and report['applied'] is False


def test_retired_provider_aliases_are_never_loaded_or_transferred():
    assert explicit_aliases(Path('missing-community'))=={}


def catalog():
    return {'code':0,'compressionVersion':1,'headers':['id','type','mid','level','lng','lat','meta'],
            'encoding':{'delta':['id'],'sort':['type','id']},
            'data':{'id':[100,2,-101],'type':['o17','o17','o44'],'mid':[2,7,2],'level':[6,6,5],
                    'lng':[.4,-.2,.7],'lat':[.1,.5,-.1],'meta':['','l=123_456|82|5','']}}


def test_signed_deltas_continue_across_category_and_map_changes():
    points=parse_catalog(catalog())
    assert [p.external_id for p in points]==['100','102','1']
    assert points[1].map_id==7 and points[1].x==-.2
    assert points[1].layer_meta=='l=123_456|82|5'
    assert points[2].id=='appsample:marker:1'
    report=resolve_catalog_progress(('1','100','102','999'),points)
    assert report['resolved']==3 and report['missing_ids']==['999']
    assert report['resolved_chests']==3
    assert report['resolved_by_map']=={'2':2,'7':1}
    assert report['collection_timestamp'] is None and report['applied'] is False
    assert report['coordinate_system']=='appsample-normalized-v5' and report['runtime_ready'] is False


@pytest.mark.parametrize('fault',['coded','version','duplicate','columns','nonfinite','delta','encoding'])
def test_incompatible_catalog_is_rejected_instead_of_misplacing_items(fault):
    data=catalog()
    if fault=='coded':data['code']=1
    if fault=='version':data['compressionVersion']=2
    if fault=='duplicate':data['data']['id'][1]=0
    if fault=='columns':data['data']['lat'].pop()
    if fault=='nonfinite':data['data']['lng'][0]=float('inf')
    if fault=='delta':data['data']['id'][0]=1.5
    if fault=='encoding':data['encoding']['delta']=['id','lng']
    with pytest.raises(ValueError):parse_catalog(data)


def test_catalog_archive_preserves_prior_report_progress_and_raw_source(tmp_path):
    ids=('1','100','102','999')
    source=tmp_path/'catalog.json';source.write_text(json.dumps(catalog()))
    directory=tmp_path/'imports'
    original=audit(ids,{'1':{'target':{'id':'target'}}})
    output=archive_progress(ids,original,directory)
    before=(output/'report.json').read_bytes()
    points=parse_catalog(catalog());report=resolve_catalog_progress(ids,points)
    assert archive_catalog_progress(ids,report,source,directory,'https://example.test/catalog')==output
    assert (output/'report.json').read_bytes()==before
    meta=json.loads((output/'SOURCE.json').read_text())
    assert (output/meta['catalog_file']).read_bytes()==source.read_bytes()
    assert json.loads((output/'progress.json').read_text())['markerIds']==list(ids)
    assert json.loads((output/'source-progress.json').read_text())['missing_ids']==['999']
