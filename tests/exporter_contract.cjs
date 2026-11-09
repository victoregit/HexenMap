'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const root=process.argv[2];
const coreText=fs.readFileSync(root+'/data/import/appsample-core.js','utf8');
const endpoint='https://firestore.googleapis.com/v1/projects/genshin-impact/databases/(default)/documents:batchGet?key=public';
const origin='https://genshin-impact-map.appsample.com';
const doc=(ids=['002','1','002'],collection='users')=>({found:{name:`projects/genshin-impact/databases/(default)/documents/${collection}/redacted`,fields:{markerIds:{arrayValue:{values:ids.map(stringValue=>({stringValue}))}}}}});
function env(){
 class XHR{constructor(){this.events=new Map();this.status=200;this.responseType='';}open(){return 42;}addEventListener(e,f){if(!this.events.has(e))this.events.set(e,new Set());this.events.get(e).add(f);}removeEventListener(e,f){this.events.get(e)?.delete(f);}fire(type){for(const f of [...(this.events.get(type)||[])])f({type});}}
 const c={URL,TextEncoder,TextDecoder,Uint8Array,Response,location:{href:origin+'/'},XMLHttpRequest:XHR,fetch:()=>Promise.resolve(new Response(JSON.stringify([doc()])))};
 c.window=c;vm.createContext(c);vm.runInContext(coreText,c);return c;
}
const tick=()=>new Promise(r=>setTimeout(r,20));
(async()=>{
 const c=env(),k=c.HexenAppSample;
 assert.deepEqual(Array.from(k.extract([doc()]).markerIds),['002','1']);
 assert.equal(k.extract([doc([], 'users-backup')]).state,'ignored');
 assert.equal(k.extract([doc(),doc()]).state,'ignored');
 assert.equal(k.extract([{missing:'projects/genshin-impact/databases/(default)/documents/users/redacted'}]).state,'not-found');
 assert.equal(k.extract([doc([])]).markerIds.length,0);
 const empty=doc();empty.found.fields.markerIds={arrayValue:{}};assert.equal(k.extract([empty]).markerIds.length,0);
 for(const value of [null,{},'bad']){const malformed=doc();malformed.found.fields.markerIds.arrayValue.values=value;assert.throws(()=>k.extract([malformed]));}
 for(const invalid of [[1],['1e3'],['-1'],['１'],[''],['9'.repeat(33)]])assert.throws(()=>k.extract([doc(invalid)]));
 assert.equal(k.ids(Array(300000).fill('1')).length,1);
 assert.throws(()=>k.ids(Array(300001).fill('1')));
 assert.throws(()=>k.extract([{junk:'x'.repeat(k.MAX_BYTES)}]));
 assert(k.target(endpoint));assert(!k.target(endpoint.replace('genshin-impact/','other/')));assert(!k.target('https://evil.test/documents:batchGet'));
 let outputs=[];const original=c.fetch,promise=Promise.resolve(new Response(JSON.stringify([doc()])));c.fetch=()=>promise;
 const before=c.fetch,open=c.XMLHttpRequest.prototype.open,stop=k.observe(s=>outputs.push(s));
 assert.equal(c.fetch(endpoint),promise);assert.equal(await promise instanceof Response,true);await tick();assert.equal(outputs.at(-1).state,'detected');
 const x=new c.XMLHttpRequest();assert.equal(x.open('POST',endpoint),42);x.responseText=JSON.stringify([doc(['7'])]);x.fire('load');await tick();assert.equal(outputs.at(-1).markerIds[0],'7');
 assert.equal([...x.events.values()].reduce((s,v)=>s+v.size,0),0);
 x.open('POST',endpoint);x.open('POST','https://example.com/');assert.equal([...x.events.values()].reduce((s,v)=>s+v.size,0),0);
 x.open('POST',endpoint);x.fire('abort');assert.equal([...x.events.values()].reduce((s,v)=>s+v.size,0),0);
 x.open('POST',endpoint);x.responseType='json';x.response=doc(['8']);x.fire('load');await tick();assert.equal(outputs.at(-1).markerIds[0],'8');
 x.open('POST',endpoint);x.responseType='';x.responseText='{bad';x.fire('load');await tick();assert.equal(outputs.at(-1).state,'error');
 x.open('POST',endpoint);x.responseText='x'.repeat(k.MAX_BYTES+1);x.fire('load');await tick();assert.equal(outputs.at(-1).state,'error');
 stop();assert.equal(c.fetch,before);assert.equal(c.XMLHttpRequest.prototype.open,open);
 // Regression: starting a backup read must not invalidate users still in flight.
 const concurrent=env();let resolveUsers,resolveBackup;
 const userPromise=new Promise(r=>resolveUsers=r),backupPromise=new Promise(r=>resolveBackup=r);
 let calls=0;concurrent.fetch=()=>++calls===1?userPromise:backupPromise;
 const captured=[];const stopConcurrent=concurrent.HexenAppSample.observe(s=>captured.push(s));
 assert.equal(concurrent.fetch(endpoint),userPromise);assert.equal(concurrent.fetch(endpoint),backupPromise);
 resolveBackup(new Response(JSON.stringify([doc([], 'users-backup')])));await tick();
 resolveUsers(new Response(JSON.stringify([doc(['003'])])));await tick();
 assert.equal(captured.length,1);assert.equal(captured[0].markerIds[0],'003');stopConcurrent();
 // A newer accepted users snapshot still wins over an older delayed response.
 const ordered=env();let oldResolve;const old=new Promise(r=>oldResolve=r);let orderCalls=0;
 ordered.fetch=()=>++orderCalls===1?old:Promise.resolve(new Response(JSON.stringify([doc(['new'.length.toString()])])));
 const orderedSnapshots=[];const stopOrdered=ordered.HexenAppSample.observe(s=>orderedSnapshots.push(s));
 ordered.fetch(endpoint);await ordered.fetch(endpoint);await tick();oldResolve(new Response(JSON.stringify([doc(['1'])])));await tick();
 assert.equal(orderedSnapshots.length,1);assert.equal(orderedSnapshots[0].markerIds[0],'3');stopOrdered();
 // Oversized stream is canceled without consuming/replacing the original response.
 const big=env();big.fetch=()=>Promise.resolve(new Response('x'.repeat(k.MAX_BYTES+1)));let state;
 const end=big.HexenAppSample.observe(s=>state=s.state);const response=await big.fetch(endpoint);await tick();assert.equal(state,'error');assert.equal((await response.text()).length,k.MAX_BYTES+1);end();
 // Per-document bridge state, bootstrap before bridge, stale contexts, repeated exports.
 function page(early=false){
   const p=env(),listeners=[],handlers=[];let sender;
   const windowProxy=vm.runInContext("window",p);
   p.crypto=require('node:crypto').webcrypto;
   p.addEventListener=(type,f)=>{if(type==='message')listeners.push(f);};
   p.postMessage=(data,originValue)=>{setImmediate(()=>{for(const f of listeners)f({source:windowProxy,origin:originValue,data});});};
   p.chrome={runtime:{id:'local',getURL:s=>'chrome-extension://local/'+s,onMessage:{addListener:f=>handlers.push(f)}}};
   const run=name=>vm.runInContext(fs.readFileSync(root+'/extensions/hexen-map-exporter/'+name,'utf8'),p);
   const request=m=>{let answer;for(const h of handlers)h(m,sender??{id:'local',url:'chrome-extension://local/popup.html'},r=>answer=r);return answer;};
   const inject=(m,source=windowProxy,where=origin)=>{for(const f of listeners)f({source,origin:where,data:m});};
   return {p,run,request,inject,setSender:s=>sender=s};
 }
 const a=page();a.run('capture.js');await a.p.fetch(endpoint);await tick();a.run('bridge.js');await tick();
 let status=a.request({type:'status'});assert.equal(status.state,'detected');assert.equal(status.count,2);
 assert.equal(status.connected,true);
 const backup=new a.p.XMLHttpRequest();backup.open('POST',endpoint);backup.responseText=JSON.stringify([doc([], 'users-backup')]);backup.fire('load');await tick();assert.equal(a.request({type:'status'}).revision,status.revision);
 const q={type:'export',context:status.context,revision:status.revision};
 assert.deepEqual(JSON.parse(JSON.stringify(a.request(q).payload)),{source:'appsample',version:1,markerIds:['002','1']});
 assert.equal(a.request(q).payload.markerIds.length,2);
 a.run('bridge.js');a.run('capture.js');assert.equal(a.request({type:'status'}).revision,status.revision);
 const b=page();b.run('bridge.js');b.run('capture.js');await tick();assert.equal(b.request({type:'status'}).state,'waiting');
 assert.equal(b.request(q).error,'context-changed');
 a.inject({hexen:1,type:'snapshot',context:status.context,state:'detected',markerIds:['9']},{},origin);assert.equal(a.request(q).payload.markerIds.length,2);
 a.inject({hexen:1,type:'snapshot',context:status.context,state:'detected',markerIds:['9']},vm.runInContext('window',a.p),'https://evil.test');assert.equal(a.request(q).payload.markerIds.length,2);
 a.inject({hexen:1,type:'snapshot',context:status.context,state:'detected',markerIds:['9']});status=a.request({type:'status'});assert.equal(status.count,1);assert.equal(a.request(q).error,'context-changed');
 a.setSender({id:'foreign',url:'chrome-extension://foreign/popup.html'});assert.equal(a.request({type:'status'}),undefined);
 a.setSender({id:'local'});assert.equal(a.request({type:'status'}).state,'detected');
 a.setSender({id:'local',tab:{id:7}});assert.equal(a.request({type:'status'}),undefined);
 const failed=page();failed.p.HexenAppSample=undefined;failed.run('capture.js');failed.p.HexenAppSample=k;failed.run('bridge.js');await tick();
 const failedStatus=failed.request({type:'status'});assert.equal(failedStatus.connected,false);assert.equal(failedStatus.state,'error');assert.equal(failedStatus.phase,'failed');
 console.log('Core, fetch/XHR, bridge and context contracts passed');
})().catch(e=>{console.error(e);process.exitCode=1});
