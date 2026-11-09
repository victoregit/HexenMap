/* Manual alternative. The saved script includes the shared validator above. */
(() => {
  'use strict';
  if(location.protocol!=='https:'||location.hostname!=='genshin-impact-map.appsample.com'){
    alert('Execute somente na página HTTPS do AppSample.');return;
  }
  const flag='__hexenExportV1';
  if(window[flag]){alert('O exportador já está aguardando.');return;}
  let timer;
  const restore=()=>{stop();clearTimeout(timer);delete window[flag];};
  const stop=HexenAppSample.observe(snapshot=>{
    if(snapshot.state!=='detected')return;
    restore();
    if(!confirm(`Hexen Map: ${snapshot.markerIds.length} itens coletados encontrados.\nSalvar somente os IDs em um JSON local?`))return;
    const blob=new Blob([JSON.stringify({source:'appsample',version:1,markerIds:snapshot.markerIds},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download='appsample-coletados.json';document.body.appendChild(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
  });
  window[flag]=true;
  timer=setTimeout(()=>{restore();alert('Hexen Map: prazo encerrado sem exportar. Nada foi alterado.');},180000);
  console.info('Hexen Map: aguardando a leitura do progresso por até três minutos.');
})();
