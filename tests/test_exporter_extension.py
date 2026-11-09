"""Exporter contracts: browser simulations and end-to-end local progress import."""
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('harness', ['exporter_contract.cjs', 'exporter_popup_contract.cjs'])
def test_extension_browser_contracts(harness):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for extension simulation')
    subprocess.run([node, str(ROOT / 'tests' / harness), str(ROOT)], check=True, capture_output=True, text=True)


def test_extension_package_is_self_contained_and_restricted(tmp_path):
    from scripts.package_exporter import package
    target = package(tmp_path)
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read('HexenMapExporter/manifest.json').decode('utf-8-sig'))
        assert manifest['manifest_version'] == 3 and 'background' not in manifest
        assert manifest['permissions'] == ['nativeMessaging']
        assert manifest['host_permissions'] == ['https://genshin-impact-map.appsample.com/*']
        for script in manifest['content_scripts']:
            assert script['matches'] == manifest['host_permissions']
            assert script['run_at'] == 'document_start'
            for name in script['js']:
                assert 'HexenMapExporter/' + name in names
        assert archive.read('HexenMapExporter/appsample-core.js') == (ROOT / 'data/import/appsample-core.js').read_bytes()
        for world in manifest['content_scripts']:
            assert len(world['js']) == 1
            entry = archive.read('HexenMapExporter/' + world['js'][0]).decode('utf-8').replace('\r\n', '\n')
            assert (ROOT / 'data/import/appsample-core.js').read_text(encoding='utf-8') in entry
        assert len(names) == 8
        assert not any('progress' in n or 'userData' in n for n in names)


@pytest.mark.parametrize('entry', ['capture.js', 'bridge.js'])
def test_packaged_entry_boots_without_preloaded_core(tmp_path, entry):
    from scripts.package_exporter import package
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for packaged entry bootstrap')
    package(tmp_path)
    harness = r'''
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const listeners=[],messages=[];class XHR{open(){}}
const c={URL,TextEncoder,TextDecoder,Uint8Array,crypto:require('node:crypto').webcrypto,
 location:{href:'https://genshin-impact-map.appsample.com/'},fetch:()=>Promise.resolve(new Response('[]')),XMLHttpRequest:XHR,
 addEventListener:(_,f)=>listeners.push(f),postMessage:m=>messages.push(m),
 chrome:{runtime:{id:'local',getURL:s=>'chrome-extension://local/'+s,onMessage:{addListener:()=>{}}}}};
c.window=c;vm.createContext(c);
assert.equal(c.HexenAppSample,undefined);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
delete c.HexenAppSample; // entry keeps its lexical dependency after startup
if(process.argv[1].endsWith('capture.js')){
 assert.equal(c.__hexenMapCaptureV1,true);
 const win=vm.runInContext('window',c);
 for(const f of listeners)f({source:win,origin:'https://genshin-impact-map.appsample.com',data:{hexen:1,type:'hello',context:'a'.repeat(32)}});
 assert(messages.some(m=>m.type==='attached'));
}else assert.equal(c.__hexenBridgeV1,true);
'''
    subprocess.run([node, '-e', harness, str(tmp_path / 'HexenMapExporter' / entry)], check=True, capture_output=True, text=True)


def test_js_export_import_preview_merge_backup_and_repeat(tmp_path):
    from src.live.appsample_import import parse_marker_ids
    from src.live.appsample_runtime import import_records
    from src.live.catalog import Item
    from src.progress.progress_manager import ProgressManager
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for shared-core export')
    harness = """
const fs=require('fs'),vm=require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const s=HexenAppSample.extract([{found:{name:'projects/genshin-impact/databases/(default)/documents/users/test',fields:{markerIds:{arrayValue:{values:[{stringValue:'001'},{stringValue:'1'},{stringValue:'001'},{stringValue:'999'}]}}}}}]);
console.log(JSON.stringify({source:'appsample',version:1,markerIds:s.markerIds}));
"""
    result = subprocess.run([node, '-e', harness, str(ROOT / 'data/import/appsample-core.js')], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert set(payload) == {'source', 'version', 'markerIds'}
    ids, duplicates = parse_marker_ids(payload)
    assert ids == ('001', '1', '999') and duplicates == 0
    items = [Item('appsample:marker:' + i, 'Baú', 'common-chest', 0, 0, rule_id='permanent') for i in ('001', '1')]
    records, missing, key = import_records(ids, items)
    assert len(records) == 2 and missing == ['999']  # preview, before applying
    manager = ProgressManager(str(tmp_path / 'progress.json'))
    manager.mark_collected('existing');manager.save()
    before = Path(manager.filepath).read_bytes()
    result = manager.merge_imported_records(records, key, 'appsample')
    assert result['added'] == 2 and Path(result['backup']).read_bytes() == before
    assert manager.merge_imported_records(records, key, 'appsample')['repeated']
    assert ProgressManager(manager.filepath).get_collected_ids() == {'existing', 'appsample:marker:001', 'appsample:marker:1'}
