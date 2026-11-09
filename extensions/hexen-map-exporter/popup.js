'use strict';
const $=id=>document.getElementById(id);
const APP='https://genshin-impact-map.appsample.com/';
let tabId=null,current=null,connectingAt=Date.now(),delivering=false,deliveryNotice=null;
const isApp=url=>{try{return new URL(url).origin===new URL(APP).origin;}catch{return false;}};
function render(status){
  if(!status||!['waiting','detected','not-found','error'].includes(status.state))throw Error('A ponte não respondeu. Recarregue a extensão e a página do AppSample.');
  current=status;
  if(deliveryNotice===`${status.context}:${status.revision}`)return;
  const labels={waiting:'Aguardando',detected:'Progresso detectado','not-found':'Não encontrado',error:'Erro na leitura'};
  $('state').textContent=labels[status.state]??'Erro na leitura';
  $('detail').textContent=status.state==='detected'?`${status.count.toLocaleString('pt-BR')} IDs · ${new Date(status.at).toLocaleTimeString('pt-BR')}`:
    status.state==='waiting'?'Aguardando uma resposta. Se a aba já estava aberta ao instalar, clique em Atualizar leitura.':
    status.state==='not-found'?'Nenhum documento de progresso confirmado. Confira seu login no site.':'A resposta não pôde ser validada. Atualize a leitura.';
  $('export').disabled=status.state!=='detected';
  $('send').disabled=status.state!=='detected';
  if(status.phase==='failed')$('detail').textContent='O observador falhou ao iniciar. Atualize a extensão para 0.1.2 ou superior e recarregue o AppSample.';
  const elapsed=Date.now()-(status.phaseAt??status.startedAt??connectingAt);
  const busy=status.state==='waiting'&&elapsed<20000;
  $('loading').hidden=!busy;
  const phases={waiting:'Aguardando a leitura do site',request:'Consulta de progresso identificada',receiving:'Recebendo a resposta',validating:'Validando os IDs',ignored:'Aguardando o documento de progresso; backup ignorado'};
  $('stage').textContent=status.state==='waiting'?(status.connected?phases[status.phase]??phases.waiting:'Conectando o observador à página'):'';
  if(status.state==='waiting'&&!busy){
    $('state').textContent='Leitura não recebida';
    $('detail').textContent=status.connected?
      'O observador está conectado, mas não recebeu um progresso válido. Confira o login no AppSample; se já estiver conectado, saia e entre pelo próprio site com a extensão instalada.':
      'O observador não conectou. Recarregue a extensão em chrome://extensions e depois atualize a página do AppSample.';
    $('stage').textContent='Nenhum arquivo foi gerado. Você pode tentar novamente.';
  }
}
async function send(type){
  const [active]=await chrome.tabs.query({active:true,currentWindow:true});
  if(active?.id!==tabId||!isApp(active.url))throw Error('A aba ativa mudou. Reabra a extensão.');
  return chrome.tabs.sendMessage(tabId,{type,context:current?.context,revision:current?.revision});
}
async function activeTab(){
  const [active]=await chrome.tabs.query({active:true,currentWindow:true});
  if(active?.id!==tabId||!isApp(active.url))throw Error('A aba ativa mudou. Reabra a extensão.');
  return active;
}
function error(e){$('state').textContent='Erro na leitura';$('detail').textContent=e.message||'Atualize a aba do AppSample.';$('export').disabled=true;$('send').disabled=true;$('loading').hidden=true;$('stage').textContent='Nenhum arquivo foi gerado.';}
function disconnected(){
  if(Date.now()-connectingAt<5000){render({state:'waiting'});return;}
  error(new Error('A ponte não respondeu. Recarregue a extensão em chrome://extensions e depois atualize o AppSample.'));
}
$('open').addEventListener('click',()=>chrome.tabs.create({url:APP}));
$('refresh').addEventListener('click',async()=>{
  try{await activeTab();if(current?.context)await send('clear');deliveryNotice=null;connectingAt=Date.now();current=null;render({state:'waiting'});await chrome.tabs.reload(tabId);}catch(e){error(e);}
});
async function exportPayload(){
    const result=await send('export');
    if(result?.error||result?.context!==current.context||result?.revision!==current.revision)throw Error('A leitura mudou. Reabra a extensão antes de exportar.');
    const p=result.payload;
    if(p?.source!=='appsample'||p.version!==1||Object.keys(p).sort().join()!=='markerIds,source,version')throw Error('Arquivo inválido.');
    const payload={source:'appsample',version:1,markerIds:HexenAppSample.ids(p.markerIds)};
    return payload;
}
$('export').addEventListener('click',async()=>{
  try{
    const payload=await exportPayload();
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='appsample-coletados.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){error(e);}
});
$('send').addEventListener('click',async()=>{
  if(delivering)return;
  delivering=true;$('send').disabled=true;$('refresh').disabled=true;
  try{
    const payload=await exportPayload();
    $('state').textContent='Enviando ao Hexen Map';$('detail').textContent='Aguarde a abertura da prévia no aplicativo. O Windows pode pedir autorização para abri-lo.';
    $('loading').hidden=false;$('stage').textContent='Comunicação local · nenhum envio ao AppSample';
    const result=await chrome.runtime.sendNativeMessage('com.hexenmap.exporter',payload);
    if(result?.ok!==true)throw Error();
    $('state').textContent='Enviado para a prévia';$('detail').textContent=`${payload.markerIds.length.toLocaleString('pt-BR')} IDs encaminhados. Confira o Hexen Map e confirme a mesclagem.`;
    $('stage').textContent='O envio não confirma que o progresso foi importado.';
  }catch{
    $('state').textContent='Não foi possível enviar';$('detail').textContent='Abra o Hexen Map atualizado e use Ajustes → Ativar conexão com a extensão. Você também pode baixar o JSON e importar manualmente.';
    $('stage').textContent='Nenhuma confirmação de importação recebida.';
  }finally{
    $('loading').hidden=true;$('refresh').disabled=false;$('send').disabled=current?.state!=='detected';
    deliveryNotice=`${current?.context}:${current?.revision}`;
    delivering=false;
  }
});
(async()=>{
  try{
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!tab||!isApp(tab.url))throw Error('Abra o AppSample e use a extensão nessa aba.');
    tabId=tab.id;$('refresh').disabled=false;
    try{render(await chrome.tabs.sendMessage(tabId,{type:'status'}));}
    catch{disconnected();}
  }catch(e){error(e);}
})();
// Metadata only. Closing the popup naturally stops this timer.
setInterval(async()=>{
  if(tabId===null||delivering)return;
  try{render(await send('status'));}catch{disconnected();}
},1000);
