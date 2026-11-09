/* MAIN world: passive observation, no credentials, storage or requests. */
(() => {
  'use strict';
  if(window.__hexenMapCaptureV1)return;
  const origin='https://genshin-impact-map.appsample.com';
  let context=null,early=null,phase='waiting',running=false;
  function progress(next){
    phase=next;
    if(context)window.postMessage({hexen:1,type:'progress',context,phase},origin);
  }
  function publish(snapshot){
    if(snapshot.state==='ignored')return;
    // Only a bootstrap hand-off may temporarily retain a response here.
    if(!context){early=snapshot;return;}
    window.postMessage({hexen:1,type:'snapshot',context,...snapshot},origin);
    early=null;
  }
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==origin)return;
    const m=event.data;
    if(m?.hexen!==1||m.type!=='hello'||typeof m.context!=='string'||!/^[a-f0-9]{32}$/.test(m.context))return;
    if(context&&context!==m.context)return;
    context=m.context;
    if(!running){
      window.postMessage({hexen:1,type:'startup-error',context},origin);
      return;
    }
    window.postMessage({hexen:1,type:'attached',context},origin);
    progress(phase);
    if(early)publish(early);
  });
  try{
    HexenAppSample.observe(publish,progress);
    running=true;
    window.__hexenMapCaptureV1=true;
  }catch{
    // A working message listener alone is not a working transport observer.
    phase='failed';
  }
  window.postMessage({hexen:1,type:'ready'},origin);
})();
