import hashlib
import json

from src.live.catalog import Item,load_catalog
from src.live.session import CollectionCount,Session
from src.progress.progress_manager import ProgressManager


def test_counts_increase_and_decrease_without_filter_or_legacy_interference(tmp_path):
    progress=ProgressManager(str(tmp_path/"progress.json"))
    progress.mark_collected("demo:old")
    session=Session([Item("a","Chest","common-chest",0,0),
                     Item("b","Chest","common-chest",0,0),
                     Item("c","Oculus","anemoculus",0,0)],progress)
    assert session.collection_counts()["common-chest"]==CollectionCount(0,2)
    session.set_collected("a",True)
    assert session.collection_counts()["common-chest"]==CollectionCount(1,2)
    session.selected=set()
    assert session.collection_counts()["common-chest"].collected==1
    session.selected={"anemoculus"}
    assert session.collection_counts()["common-chest"].remaining==1
    session.undo()
    assert session.collection_counts()["common-chest"].collected==0
    session.set_collected("b",True)
    reloaded=Session(session.items,ProgressManager(progress.filepath))
    assert reloaded.collection_counts()["common-chest"]==CollectionCount(1,2)
    reloaded.set_collected("b",False)
    assert reloaded.collection_counts()["common-chest"]==CollectionCount(0,2)


def test_region_namespaces_keep_identical_source_ids_separate(tmp_path):
    items=[]
    for region in ("mondstadt","liyue"):
        directory=tmp_path/region;directory.mkdir()
        raw=json.dumps({"data":[{"id":"same-source-id","coordinates":[-20,40]}]}).encode()
        (directory/"common-chest.json").write_bytes(raw)
        (directory/"SOURCE.json").write_text(json.dumps({"region_id":region,"files":[
            {"file":"common-chest.json","sha256":hashlib.sha256(raw).hexdigest()}]}))
        items.extend(load_catalog(directory))
    assert items[0].id=="teyvat.moe:mondstadt:common-chest:same-source-id"
    assert items[1].id=="teyvat.moe:liyue:common-chest:same-source-id"
    progress=ProgressManager(str(tmp_path/"progress.json"))
    progress.mark_collected(items[0].id)
    assert not progress.is_collected(items[1].id)
    assert items[1].region_id=="liyue"
