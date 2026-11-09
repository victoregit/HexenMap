/* ISOLATED world: per-document memory, validation, active-tab popup bridge. */
(() => {
  'use strict';
  if(globalThis.__hexenBridgeV1)return;
  globalThis.__hexenBridgeV1=true;
  const origin='https://genshin-impact-map.appsample.com',core=HexenAppSample;
  const context=Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
  const startedAt=Date.now();
  let snapshot={state:'waiting',at:null},revision=0,connected=false,phase='waiting',phaseAt=startedAt;
  const hello=()=>window.postMessage({hexen:1,type:'hello',context},origin);
  const meta=()=>({state:snapshot.state,at:snapshot.at,count:snapshot.markerIds?.length??null,context,revision,connected,phase,startedAt,phaseAt});
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==origin)return;
    const m=event.data;
    if(m?.hexen!==1)return;
    if(m.type==='ready'){hello();return;}
    if(m.context!==context)return;
    if(m.type==='startup-error'&&Object.keys(m).length===3){
      connected=false;phase='failed';snapshot={state:'error',at:Date.now()};revision++;return;
    }
    if(m.type==='attached'&&Object.keys(m).length===3){connected=true;return;}
    if(m.type==='progress'&&Object.keys(m).length===4&&['waiting','request','receiving','validating','ignored'].includes(m.phase)){
      connected=true;if(phase!==m.phase){phase=m.phase;phaseAt=Date.now();}return;
    }
    if(m.type!=='snapshot'||m.context!==context)return;
    try{
      if(core.bytes(JSON.stringify(m))>core.MAX_BYTES)throw Error();
      if(!['detected','not-found','error'].includes(m.state))throw Error();
      const allowed=['hexen','type','context','state',...(m.state==='detected'?['markerIds']:[])];
      if(Object.keys(m).some(k=>!allowed.includes(k)))throw Error();
      snapshot=m.state==='detected'?{state:m.state,markerIds:core.ids(m.markerIds),at:Date.now()}:{state:m.state,at:Date.now()};
    }catch{snapshot={state:'error',at:Date.now()};}
    revision++;
  });
  chrome.runtime.onMessage.addListener((m,sender,reply)=>{
    // MessageSender.url is optional. Own-extension pages only, never content scripts.
    if(sender.id!==chrome.runtime.id||sender.tab||(sender.url&&sender.url!==chrome.runtime.getURL('popup.html')))return;
    if(m?.type==='status'){reply(meta());return;}
    if(m?.context!==context||m.revision!==revision){reply({error:'context-changed'});return;}
    if(m.type==='export'&&snapshot.state==='detected'){
      reply({...meta(),payload:{source:'appsample',version:1,markerIds:core.ids(snapshot.markerIds)}});
    }else if(m.type==='clear'){
      snapshot={state:'waiting',at:null};phase='waiting';phaseAt=Date.now();revision++;reply(meta());
    }
  });
  hello();
})();
