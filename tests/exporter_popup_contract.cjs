// Popup contract in a separate fake extension page (no real browser account).
// Run after the transport/bridge harness; validates user-triggered downloads only.
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const root=process.argv[2],elements=new Map();let interval,blob,downloads=0,reloads=0,created=0;
for(const id of ['state','detail','export','refresh','open','loading','stage','send'])elements.set(id,{disabled:false,textContent:'',handlers:{},addEventListener(e,f){this.handlers[e]=f;}});
let snapshot={state:'detected',at:1000,count:2,context:'a'.repeat(32),revision:1},active=7;
const U=class extends URL{};U.createObjectURL=b=>{blob=b;return 'blob:local';};U.revokeObjectURL=()=>{};
const c={URL:U,TextEncoder,TextDecoder,Blob,console,setTimeout:()=>{},setInterval:f=>{interval=f;},document:{getElementById:id=>elements.get(id),createElement:()=>({click:()=>downloads++})},chrome:{runtime:{sendNativeMessage:async(host,payload)=>{assert.equal(host,'com.hexenmap.exporter');assert.deepEqual(Object.keys(payload).sort(),['markerIds','source','version']);return {ok:true,count:payload.markerIds.length,status:'queued'};}},tabs:{
 query:async()=>[{id:active,url:'https://genshin-impact-map.appsample.com/'}],
 sendMessage:async(id,m)=>{assert.equal(id,7);if(m.type==='status')return {...snapshot};if(m.type==='clear'){snapshot={...snapshot,state:'waiting',count:null,revision:2};return snapshot;}
 return {...snapshot,payload:{source:'appsample',version:1,markerIds:['002','1']}};},
 reload:async()=>reloads++,create:async()=>created++}}};
vm.createContext(c);vm.runInContext(fs.readFileSync(root+'/data/import/appsample-core.js','utf8'),c);vm.runInContext(fs.readFileSync(root+'/extensions/hexen-map-exporter/popup.js','utf8'),c);
(async()=>{
 await new Promise(r=>setImmediate(r));assert.equal(downloads,0);assert.equal(elements.get('export').disabled,false);
 await elements.get('export').handlers.click();await elements.get('export').handlers.click();assert.equal(downloads,2);
 assert.deepEqual(JSON.parse(await blob.text()),{source:'appsample',version:1,markerIds:['002','1']});
 active=8;await elements.get('export').handlers.click();assert.equal(downloads,2);
 await elements.get('refresh').handlers.click();assert.equal(reloads,0);
 active=7;await interval();await elements.get('refresh').handlers.click();assert.equal(reloads,1);assert.equal(elements.get('export').disabled,true);
 snapshot={...snapshot,state:'detected',count:0};await interval();assert.equal(elements.get('export').disabled,false);assert(elements.get('detail').textContent.includes('0 IDs'));
 await elements.get('send').handlers.click();assert.equal(elements.get('state').textContent,'Enviado para a prévia');
 assert.equal(elements.get('loading').hidden,true);
 snapshot={...snapshot,revision:3,state:'waiting',connected:true,phase:'receiving',phaseAt:Date.now()};await interval();assert.equal(elements.get('loading').hidden,false);assert(elements.get('stage').textContent.includes('Recebendo'));
 snapshot={...snapshot,phaseAt:Date.now()-21000};await interval();assert.equal(elements.get('loading').hidden,true);assert.equal(elements.get('state').textContent,'Leitura não recebida');assert(elements.get('detail').textContent.includes('login'));
 snapshot={...snapshot,connected:false};await interval();assert(elements.get('detail').textContent.includes('não conectou'));
 await elements.get('open').handlers.click();assert.equal(created,1);
 console.log('Popup export, refresh and active-tab contracts passed');
})().catch(e=>{console.error(e);process.exitCode=1});
