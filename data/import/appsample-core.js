/* Shared dependency-free validation and passive transport observer. */
(() => {
  'use strict';
  const MAX_BYTES=16*1024*1024, MAX_IDS=300000;
  const bytes=text=>new TextEncoder().encode(text).byteLength;
  function ids(values) {
    if (!Array.isArray(values)||values.length>MAX_IDS||values.some(v=>typeof v!=='string'||!/^[0-9]{1,32}$/.test(v))) throw Error('IDs inválidos.');
    return [...new Set(values)].sort();
  }
  function extract(payload) {
    if (bytes(JSON.stringify(payload))>MAX_BYTES) throw Error('Resposta acima de 16 MiB.');
    const entries=Array.isArray(payload)?payload:[payload];
    const pattern=/^projects\/genshin-impact\/databases\/\(default\)\/documents\/users\/[^/]+$/;
    const docs=entries.filter(e=>e?.found&&pattern.test(e.found.name));
    if(docs.length>1)return {state:'ignored'};
    if(docs.length===0)return {state:entries.some(e=>pattern.test(e?.missing))?'not-found':'ignored'};
    const field=docs[0].found.fields?.markerIds;
    if(!field)return {state:'not-found'};
    if(Object.keys(field).length!==1||!field.arrayValue||typeof field.arrayValue!=='object'||Array.isArray(field.arrayValue))throw Error('Formato inválido.');
    const values=Object.hasOwn(field.arrayValue,'values')?field.arrayValue.values:[];
    if(!Array.isArray(values)||values.length>MAX_IDS)throw Error('Lista acima do limite.');
    return {state:'detected',markerIds:ids(values.map(v=>{
      if(!v||Object.keys(v).length!==1||!Object.hasOwn(v,'stringValue'))throw Error('ID inválido.');
      return v.stringValue;
    }))};
  }
  function target(value){try{const u=new URL(value,location.href);return u.origin==='https://firestore.googleapis.com'&&u.pathname==='/v1/projects/genshin-impact/databases/(default)/documents:batchGet';}catch{return false;}}
  async function read(response,progress){
    const copy=response.clone();
    if(!copy.body?.getReader){const text=await copy.text();if(bytes(text)>MAX_BYTES)throw Error();progress('validating');return JSON.parse(text);}
    const reader=copy.body.getReader(),chunks=[];let size=0;
    try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
      if(size>MAX_BYTES){void reader.cancel().catch(()=>{});throw Error();}chunks.push(value);
    }}finally{reader.releaseLock();}
    const data=new Uint8Array(size);let offset=0;
    for(const chunk of chunks){data.set(chunk,offset);offset+=chunk.byteLength;}
    progress('validating');
    return JSON.parse(new TextDecoder().decode(data));
  }
  function observe(emit,progress=()=>{}){
    const originalFetch=window.fetch,proto=XMLHttpRequest.prototype,originalOpen=proto.open,pending=new Map();
    let stopped=false,sequence=0,accepted=0;
    function failure(serial){if(!stopped&&serial>=accepted)emit({state:'error'});}
    function deliver(payload,serial){
      if(stopped||serial<accepted)return;
      try{
        const snapshot=extract(payload);
        // Backup/unrelated requests must not cancel an in-flight users read.
        if(snapshot.state==='ignored'){progress('ignored');return;}
        accepted=serial;emit(snapshot);
      }catch{failure(serial);}
    }
    function wrappedFetch(...args){
      const promise=originalFetch.apply(this,args),input=args[0];
      if(target(typeof input==='string'||input instanceof URL?input:input?.url)){
        const serial=++sequence;
        progress('request');
        void promise.then(response=>{
          if(stopped)return;
          if(!response.ok){failure(serial);return;}
          progress('receiving');
          void read(response,progress).then(p=>deliver(p,serial),()=>failure(serial));
        },()=>failure(serial)).catch(()=>{});
      }
      return promise;
    }
    function wrappedOpen(method,url,...rest){
      pending.get(this)?.();
      const result=originalOpen.call(this,method,url,...rest);
      if(!stopped&&target(url)){
        const xhr=this;
        const cleanup=()=>{for(const e of ['load','error','abort','timeout','loadend'])xhr.removeEventListener(e,listener);pending.delete(xhr);};
        const listener=event=>{
          cleanup();if(stopped)return;const serial=++sequence;
          if(event?.type&&event.type!=='load'){if(event.type!=='loadend')failure(serial);return;}
          // Copy at load, before the site can reuse this XHR with another open.
          let status,type,payload;
          try{status=xhr.status;type=xhr.responseType;payload=type==='json'?xhr.response:xhr.responseText;}catch{failure(serial);return;}
          progress('receiving');
          Promise.resolve().then(()=>{
            if(status!==200){failure(serial);return;}
            progress('validating');
            try{if(type==='json')deliver(payload,serial);
              else if(!type||type==='text'){
                if(bytes(payload)>MAX_BYTES)throw Error();deliver(JSON.parse(payload),serial);
              }
            }catch{failure(serial);}
          });
        };
        pending.set(xhr,cleanup);for(const e of ['load','error','abort','timeout','loadend'])xhr.addEventListener(e,listener);
      }return result;
    }
    window.fetch=wrappedFetch;proto.open=wrappedOpen;
    return ()=>{stopped=true;if(window.fetch===wrappedFetch)window.fetch=originalFetch;if(proto.open===wrappedOpen)proto.open=originalOpen;for(const cleanup of [...pending.values()])cleanup();};
  }
  globalThis.HexenAppSample=Object.freeze({MAX_BYTES,MAX_IDS,ids,extract,target,observe,bytes});
})();
