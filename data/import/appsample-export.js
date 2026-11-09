/* Hexen Map — exportador local v1. Código completo, sem dependências.
 * Execute como Snippet no DevTools do AppSample. Não recarregue a página.
 * Em seguida, saia e entre na conta pelo próprio site para reler o progresso.
 * Não lê headers, cookies, armazenamento ou credenciais; não faz requisições.
 * Observa somente a resposta batchGet do projeto genshin-impact.
 * Restaura fetch/XHR ao terminar ou após 3 minutos. Recarregar também cancela.
 */
(() => {
  'use strict';
  if (location.protocol !== 'https:' || location.hostname !== 'genshin-impact-map.appsample.com') {
    alert('Execute somente na página HTTPS do AppSample.'); return;
  }
  const flag = '__hexenExportV1';
  if (window[flag]) { alert('O exportador já está aguardando o progresso.'); return; }
  const originalFetch = window.fetch;
  const originalOpen = XMLHttpRequest.prototype.open;
  const pending = new Set();
  let done = false, timer;
  const target = value => {
    try {
      const u = new URL(value, location.href);
      return u.protocol === 'https:' && u.hostname === 'firestore.googleapis.com' &&
        u.pathname === '/v1/projects/genshin-impact/databases/(default)/documents:batchGet';
    } catch { return false; }
  };
  function restore() {
    done = true; clearTimeout(timer);
    if (window.fetch === wrappedFetch) window.fetch = originalFetch;
    if (XMLHttpRequest.prototype.open === wrappedOpen) XMLHttpRequest.prototype.open = originalOpen;
    for (const [xhr, listener] of pending) xhr.removeEventListener('load', listener);
    pending.clear(); delete window[flag];
  }
  function consume(payload) {
    if (done) return;
    const docs = (Array.isArray(payload) ? payload : [payload]).filter(
      entry => entry && entry.found && entry.found.fields && 'markerIds' in entry.found.fields);
    if (docs.length !== 1) return;
    const field = docs[0].found.fields.markerIds;
    if (!field || !field.arrayValue) return;
    const values = field.arrayValue.values || [];
    if (!Array.isArray(values) || values.length > 300000 || values.some(
      v => !v || Object.keys(v).length !== 1 || typeof v.stringValue !== 'string' || !/^[0-9]{1,32}$/.test(v.stringValue))) return;
    const ids = [...new Set(values.map(v => v.stringValue))].sort();
    restore();
    if (!confirm(`Hexen Map: ${ids.length} itens coletados encontrados.\nSalvar somente os IDs em um JSON local?\nNenhum dado será enviado pelo exportador.`)) return;
    const blob = new Blob([JSON.stringify({source: 'appsample', version: 1, markerIds: ids}, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = 'appsample-coletados.json';
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    console.info('Hexen Map: exportação encerrada. Importe appsample-coletados.json no aplicativo.');
  }
  async function wrappedFetch(...args) {
    const response = await originalFetch.apply(this, args);
    const input = args[0];
    if (!done && target(typeof input === 'string' || input instanceof URL ? input : input && input.url) && response.ok) {
      try { const text = await response.clone().text(); if (text.length <= 16*1024*1024) consume(JSON.parse(text)); } catch { /* resposta original preservada */ }
    }
    return response;
  }
  function wrappedOpen(method, url, ...rest) {
    const result = originalOpen.call(this, method, url, ...rest);
    if (!done && target(url)) {
      const xhr = this;
      const pair = [xhr, null];
      const listener = () => {
        xhr.removeEventListener('load', listener); pending.delete(pair);
        if (done || xhr.status !== 200) return;
        try {
          if (xhr.responseType === 'json') consume(xhr.response);
          else if ((!xhr.responseType || xhr.responseType === 'text') && xhr.responseText.length <= 16*1024*1024) consume(JSON.parse(xhr.responseText));
        } catch { /* sem modificar a resposta do site */ }
      };
      pair[1] = listener; pending.add(pair); xhr.addEventListener('load', listener);
    }
    return result;
  }
  window[flag] = true; window.fetch = wrappedFetch; XMLHttpRequest.prototype.open = wrappedOpen;
  timer = setTimeout(() => { restore(); alert('Hexen Map: prazo encerrado sem exportar. Nada foi alterado. Execute novamente se necessário.'); }, 180000);
  console.info('Hexen Map: aguardando a leitura do progresso. Sem recarregar, saia e entre na conta pelo site. Só os IDs serão salvos, após sua confirmação.');
})();
