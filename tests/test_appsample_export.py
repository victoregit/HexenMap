"""Execute the browser helper in a fake browser: no live account or credentials."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from src.live.appsample_import import parse_marker_ids
from src.live.appsample_export import script_text


@pytest.mark.parametrize('transport,case', [('fetch','valid'),('xhr','valid'),('fetch','empty'),
    ('fetch','invalid'),('fetch','foreign'),('fetch','cancel'),('fetch','timeout')])
def test_export_only_ids_and_restore_browser(tmp_path,transport,case):
    node=shutil.which('node')
    if not node:pytest.skip('Node required for browser-helper contract tests')
    helper=tmp_path/'helper.js';helper.write_text(script_text(),encoding='utf-8')
    harness=tmp_path/'run.cjs'
    harness.write_text(r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const [file,transport,kind]=process.argv.slice(2);
let downloads=[],blob,clicked=0,confirmed=0,timeout;
const payload=[{found:{name:'projects/genshin-impact/databases/(default)/documents/users/private-account',fields:{email:{stringValue:'private'},markerIds:{arrayValue:{values:kind==='empty'?[]:[{stringValue:'20'},{stringValue:'10'},{stringValue:'20'}]}}}}}];
if(kind==='invalid')payload[0].found.fields.markerIds.arrayValue.values=[{stringValue:'not-an-id'}];
const response={ok:true,clone:()=>({text:async()=>JSON.stringify(payload)})};
const fetch=async()=>response;
class XHR {constructor(){this.listeners=new Set();this.status=200;this.responseType='';this.responseText=JSON.stringify(payload)}open(){}addEventListener(_,f){this.listeners.add(f)}removeEventListener(_,f){this.listeners.delete(f)}load(){for(const f of [...this.listeners])f()}}
const open=XHR.prototype.open;
const url='https://firestore.googleapis.com/v1/projects/genshin-impact/databases/(default)/documents:batchGet?key=public';
const URLClass=class extends URL {};
URLClass.createObjectURL=b=>{blob=b;return 'blob:local'};URLClass.revokeObjectURL=()=>{};
const context={location:{protocol:'https:',hostname:'genshin-impact-map.appsample.com',href:'https://genshin-impact-map.appsample.com/pt/'},
URL:URLClass,Blob,TextEncoder,TextDecoder,XMLHttpRequest:XHR,fetch,console:{info:()=>{}},alert:()=>{},confirm:()=>{confirmed++;return kind!=='cancel'},
setTimeout:(f,ms)=>{if(ms===180000)timeout=f;return 1},clearTimeout:()=>{},
document:{body:{appendChild:()=>{}},createElement:()=>({click(){clicked++},remove(){}})}};
context.window=context;vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8'),context);
(async()=>{
 if(kind==='timeout')timeout();
 else if(transport==='xhr'){const x=new XHR();x.open('POST',url);x.load()}
 else assert.strictEqual(await context.fetch(kind==='foreign'?'https://example.com/documents:batchGet':url),response);
 await new Promise(resolve=>setImmediate(resolve));
 if(['valid','empty','cancel','timeout'].includes(kind)){
   assert.strictEqual(context.fetch,fetch);assert.strictEqual(XHR.prototype.open,open);assert(!context.__hexenExportV1);
 }else {assert(context.__hexenExportV1);timeout()}
 if(['valid','empty'].includes(kind)){
  assert.strictEqual(clicked,1);const text=await blob.text();const p=JSON.parse(text);
  assert.deepStrictEqual(Object.keys(p).sort(),['markerIds','source','version']);
  assert(!text.includes('private'));console.log(text);
 }else {assert.strictEqual(clicked,0);console.log('null')}
})().catch(e=>{console.error(e);process.exitCode=1});
''',encoding='utf-8')
    result=subprocess.run([node,str(harness),str(helper),transport,case],capture_output=True,text=True,check=True)
    payload=json.loads(result.stdout)
    if payload is not None:
        ids,duplicates=parse_marker_ids(payload)
        assert ids==(() if case=='empty' else ('10','20')) and duplicates==0
