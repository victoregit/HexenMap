'use strict';
const $ = id => document.getElementById(id);
const versionLabel = $('extension-version');
if (versionLabel) versionLabel.textContent = `EXPORTAÇÃO LOCAL · v${chrome.runtime.getManifest().version}`;
const APP = 'https://genshin-impact-map.appsample.com/';
const HOYOLAB = 'https://act.hoyolab.com/ys/app/interactive-map/';

let tabId = null, current = null, connectingAt = Date.now(), delivering = false, deliveryNotice = null;
let activeSite = 'appsample', reading = false;

const isApp = url => {
  try { return new URL(url).origin === new URL(APP).origin; } catch { return false; }
};
const isHoYoLab = url => {
  try {
    const u = new URL(url);
    return u.origin === new URL(HOYOLAB).origin && u.pathname.includes('/ys/app/interactive-map');
  } catch { return false; }
};
const isSupportedSite = url => isApp(url) || isHoYoLab(url);

function render(status) {
  if (!status || !['waiting', 'detected', 'not-logged-in', 'not-found', 'error'].includes(status.state)) {
    throw Error('A ponte não respondeu. Recarregue a extensão e a página do mapa.');
  }
  current = status;
  if (deliveryNotice === `${status.context}:${status.revision}`) return;

  if (activeSite === 'hoyolab' || status.source === 'hoyolab') {
    renderHoYoLab(status);
  } else {
    renderAppSample(status);
  }
}

function renderAppSample(status) {
  const labels = { waiting: 'Aguardando', detected: 'Progresso detectado', 'not-found': 'Não encontrado', error: 'Erro na leitura' };
  $('state').textContent = labels[status.state] ?? 'Erro na leitura';
  $('detail').textContent = status.state === 'detected' ? `${status.count.toLocaleString('pt-BR')} IDs · ${new Date(status.at).toLocaleTimeString('pt-BR')}` :
    status.state === 'waiting' ? 'Aguardando uma resposta. Se a aba já estava aberta ao instalar, clique em Atualizar leitura.' :
    status.state === 'not-found' ? 'Nenhum documento de progresso confirmado. Confira seu login no site.' : 'A resposta não pôde ser validada. Atualize a leitura.';
  $('export').disabled = status.state !== 'detected';
  $('send').disabled = status.state !== 'detected';
  if ($('stats')) $('stats').hidden = true;
  if (status.phase === 'failed') $('detail').textContent = 'O observador falhou ao iniciar. Atualize a extensão para 0.1.2 ou superior e recarregue o AppSample.';
  const elapsed = Date.now() - (status.phaseAt ?? status.startedAt ?? connectingAt);
  const busy = status.state === 'waiting' && elapsed < 20000;
  $('loading').hidden = !busy;
  const phases = { waiting: 'Aguardando a leitura do site', request: 'Consulta de progresso identificada', receiving: 'Recebendo a resposta', validating: 'Validando os IDs', ignored: 'Aguardando o documento de progresso; backup ignorado' };
  $('stage').textContent = status.state === 'waiting' ? (status.connected ? phases[status.phase] ?? phases.waiting : 'Conectando o observador à página') : '';
  if (status.state === 'waiting' && !busy) {
    $('state').textContent = 'Leitura não recebida';
    $('detail').textContent = status.connected ?
      'O observador está conectado, mas não recebeu um progresso válido. Confira o login no AppSample; se já estiver conectado, saia e entre pelo próprio site com a extensão instalada.' :
      'O observador não conectou. Recarregue a extensão em chrome://extensions e depois atualize a página do AppSample.';
    $('stage').textContent = 'Nenhum arquivo foi gerado. Você pode tentar novamente.';
  }
}

function renderHoYoLab(status) {
  const s = status.stats;
  const statsEl = $('stats');
  const coverage = status.coverage;
  if (reading || status.refreshing) {
    $('state').textContent = 'Atualizando progresso HoYoLAB';
    $('detail').textContent = 'Consultando todos os mapas suportados…';
    $('stage').textContent = 'Aguarde a conclusão da leitura.';
    $('loading').hidden = false;
    $('export').disabled = true;
    $('send').disabled = true;
    if (statsEl) statsEl.hidden = true;
    return;
  }

  if (status.state === 'not-logged-in') {
    $('state').textContent = 'Sessão não autenticada';
    $('detail').textContent = 'Faça login no mapa oficial HoYoLAB na aba ativa para ler seu progresso.';
    $('export').disabled = true;
    $('send').disabled = true;
    $('loading').hidden = true;
    $('stage').textContent = 'Entre pelo próprio site; a extensão não pede sua senha.';
    if (statsEl) statsEl.hidden = true;
    return;
  }

  if (status.state === 'detected') {
    const safeCount = s?.matched_safe ?? status.count ?? 0;
    $('state').textContent = 'Progresso HoYoLAB detectado';
    $('detail').textContent = `${safeCount.toLocaleString('pt-BR')} marcadores convertidos · ${new Date(status.at).toLocaleTimeString('pt-BR')}`;
    $('export').disabled = safeCount === 0;
    $('send').disabled = safeCount === 0;
    $('loading').hidden = true;
    $('stage').textContent = coverage?.complete ?
      `${coverage.maps.length} de ${coverage.total} mapas suportados lidos · pronto para exportação` :
      'Leitura parcial · todos os mapas serão consultados antes de exportar ou enviar.';

    if (statsEl && s) {
      statsEl.hidden = false;
      statsEl.innerHTML =
        `<div class="stat-row"><span>Concluídos nos mapas lidos:</span><b>${s.total_found.toLocaleString('pt-BR')}</b></div>` +
        `<div class="stat-row"><span>Correspondentes AppSample:</span><b class="stat-ok">${s.matched_safe.toLocaleString('pt-BR')}</b></div>` +
        (s.ambiguous > 0 ? `<div class="stat-row"><span>Ambíguos rejeitados:</span><b class="stat-warn">${s.ambiguous.toLocaleString('pt-BR')}</b></div>` : '') +
        (s.unmatched > 0 ? `<div class="stat-row"><span>Sem correspondência:</span><b class="stat-warn">${s.unmatched.toLocaleString('pt-BR')}</b></div>` : '') +
        (s.unsupported_map > 0 ? `<div class="stat-row"><span>Mapas não suportados:</span><b>${s.unsupported_map.toLocaleString('pt-BR')}</b></div>` : '') +
        `<div class="stat-row stat-total"><span>Disponíveis para exportar:</span><b>${s.matched_safe.toLocaleString('pt-BR')}</b></div>`;
    }
    return;
  }

  if (statsEl) statsEl.hidden = true;

  if (status.state === 'not-found') {
    $('state').textContent = 'Nenhum marcador encontrado';
    $('detail').textContent = 'Nenhum ponto concluído foi retornado pelo mapa HoYoLAB nesta sessão.';
    $('export').disabled = true;
    $('send').disabled = true;
    $('loading').hidden = true;
    $('stage').textContent = 'Marque itens no mapa HoYoLAB e atualize a leitura.';
    return;
  }

  if (status.state === 'error') {
    $('state').textContent = 'Erro na leitura';
    $('detail').textContent = coverage && !coverage.complete ?
      `Leitura incompleta: ${coverage.maps.length} de ${coverage.total} mapas. Atualize para tentar novamente.` :
      'A resposta do HoYoLAB não pôde ser validada com segurança.';
    $('export').disabled = true;
    $('send').disabled = true;
    $('loading').hidden = true;
    $('stage').textContent = 'Recarregue a página do mapa e tente novamente.';
    return;
  }

  const elapsed = Date.now() - (status.phaseAt ?? status.startedAt ?? connectingAt);
  const busy = elapsed < 20000;
  $('loading').hidden = !busy;
  const phases = {
    waiting: 'Aguardando requisição de marcações do HoYoLAB',
    request: 'Requisição de progresso identificada',
    receiving: 'Recebendo marcações da conta',
    validating: 'Validando e convertendo IDs'
  };
  $('stage').textContent = status.connected ? (phases[status.phase] ?? phases.waiting) : 'Conectando observador à página';

  if (!busy) {
    $('state').textContent = 'Leitura não recebida';
    $('detail').textContent = status.connected ?
      'O observador está conectado, mas nenhuma requisição de progresso foi capturada. Navegue pelo mapa ou clique em Atualizar leitura.' :
      'O observador não conectou. Recarregue a extensão em chrome://extensions e depois atualize o HoYoLAB.';
    $('stage').textContent = 'Nenhum arquivo foi gerado. Você pode tentar novamente.';
  } else {
    $('state').textContent = 'Aguardando…';
    $('detail').textContent = 'Aguardando requisição do mapa interativo HoYoLAB.';
    $('export').disabled = true;
    $('send').disabled = true;
  }
}

async function send(type) {
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (active?.id !== tabId || !isSupportedSite(active.url)) throw Error('A aba ativa mudou. Reabra a extensão.');
  return chrome.tabs.sendMessage(tabId, { type, context: current?.context, revision: current?.revision });
}

async function activeTab() {
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (active?.id !== tabId || !isSupportedSite(active.url)) throw Error('A aba ativa mudou. Reabra a extensão.');
  return active;
}

function error(e) {
  $('state').textContent = 'Erro na leitura';
  $('detail').textContent = e.message || 'Atualize a aba do mapa.';
  $('export').disabled = true;
  $('send').disabled = true;
  $('loading').hidden = true;
  $('stage').textContent = 'Nenhum arquivo foi gerado.';
  if ($('stats')) $('stats').hidden = true;
}

function disconnected() {
  if (Date.now() - connectingAt < 5000) { render({ state: 'waiting' }); return; }
  error(new Error('A ponte não respondeu. Recarregue a extensão em chrome://extensions e depois atualize a página.'));
}

if ($('open-appsample')) {
  $('open-appsample').addEventListener('click', () => {
    chrome.tabs.create({ url: APP });
  });
}
if ($('open-hoyolab')) {
  $('open-hoyolab').addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://act.hoyolab.com/ys/app/interactive-map/index.html' });
  });
}
if ($('open')) {
  $('open').addEventListener('click', () => {
    const url = activeSite === 'hoyolab' ? 'https://act.hoyolab.com/ys/app/interactive-map/index.html' : APP;
    chrome.tabs.create({ url });
  });
}

$('refresh').addEventListener('click', async () => {
  if (reading || delivering) return;
  try {
    await activeTab();
    if (activeSite === 'hoyolab') {
      await refreshHoYoLab();
      return;
    }
    if (current?.context) await send('clear');
    deliveryNotice = null;
    connectingAt = Date.now();
    current = null;
    render({ state: 'waiting' });
    await chrome.tabs.reload(tabId);
  } catch (e) {
    error(e);
  }
});

async function refreshHoYoLab() {
  reading = true;
  deliveryNotice = null;
  $('refresh').disabled = true;
  renderHoYoLab(current ?? {});
  try {
    const result = await send('refresh');
    if (result?.error) throw Error('Não foi possível ler todos os mapas. Clique em Atualizar leitura para tentar novamente.');
    reading = false;
    render(await send('status'));
  } finally {
    reading = false;
    $('refresh').disabled = false;
  }
}

async function exportPayload() {
  const isHoyo = activeSite === 'hoyolab';
  const originalContext = current?.context;
  if (isHoyo) { reading = true; renderHoYoLab(current ?? {}); }
  let result;
  try { result = await send('export'); }
  finally { if (isHoyo) reading = false; }
  if (result?.error === 'global-read-failed') {
    throw Error('A leitura de todos os mapas não foi concluída. Atualize a leitura e tente novamente.');
  }
  if (result?.error === 'not-logged-in') throw Error('Faça login no HoYoLAB e atualize a leitura.');
  if (result?.error === 'index-unavailable') {
    throw Error('O índice HoYoLAB não pôde ser carregado ou é incompatível com o catálogo AppSample desta versão.');
  }
  if (result?.error || result?.context !== originalContext ||
      (!isHoyo && result?.revision !== current.revision) || (isHoyo && !result?.coverage?.complete)) {
    throw Error('A leitura mudou. Reabra a extensão antes de exportar.');
  }
  if (isHoyo) render(result);
  const p = result.payload;
  if (p?.source !== 'appsample' || p.version !== 1 || Object.keys(p).sort().join() !== 'markerIds,source,version') {
    throw Error('Arquivo inválido.');
  }
  const payload = { source: 'appsample', version: 1, markerIds: HexenAppSample.ids(p.markerIds) };
  return payload;
}

$('export').addEventListener('click', async () => {
  if (reading || delivering) return;
  try {
    const payload = await exportPayload();
    const isHoyo = activeSite === 'hoyolab' || current?.source === 'hoyolab';
    if (isHoyo) {
      const total = current?.stats?.total_found ?? payload.markerIds.length;
      const safe = payload.markerIds.length;
      const excluded = total - safe;
      const msg = `Confirmar exportação de ${safe} marcadores convertidos para AppSample?\n\n` +
        `• Concluídos nos mapas suportados: ${total}\n` +
        `• Correspondentes AppSample: ${safe}\n` +
        (excluded > 0 ? `• Desconsiderados (ambíguos/não mapeados): ${excluded}\n\n` : '\n') +
        `Deseja baixar o arquivo JSON?`;
      if (typeof window !== 'undefined' && typeof window.confirm === 'function' && !window.confirm(msg)) return;
    }
    const filename = isHoyo ? 'hoyolab-appsample-coletados.json' : 'appsample-coletados.json';
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }),
      url = URL.createObjectURL(blob),
      a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) {
    error(e);
  }
});

$('send').addEventListener('click', async () => {
  if (delivering || reading) return;
  delivering = true;
  $('send').disabled = true;
  $('refresh').disabled = true;
  let nativeStarted = false;
  try {
    const payload = await exportPayload();
    const isHoyo = activeSite === 'hoyolab' || current?.source === 'hoyolab';
    if (isHoyo) {
      const total = current?.stats?.total_found ?? payload.markerIds.length;
      const safe = payload.markerIds.length;
      const excluded = total - safe;
      const msg = `Confirmar envio de ${safe} marcadores ao Hexen Map?\n\n` +
        `• Concluídos nos mapas suportados: ${total}\n` +
        `• Correspondentes AppSample: ${safe}\n` +
        (excluded > 0 ? `• Desconsiderados (ambíguos/não mapeados): ${excluded}\n\n` : '\n') +
        `Deseja prosseguir com o envio?`;
      if (typeof window !== 'undefined' && typeof window.confirm === 'function' && !window.confirm(msg)) {
        delivering = false;
        $('send').disabled = false;
        $('refresh').disabled = false;
        return;
      }
    }
    $('state').textContent = 'Enviando ao Hexen Map';
    $('detail').textContent = 'Aguarde a abertura da prévia no aplicativo. O Windows pode pedir autorização para abri-lo.';
    $('loading').hidden = false;
    $('stage').textContent = 'Comunicação local · nenhum envio externo';
    nativeStarted = true;
    const result = await chrome.runtime.sendNativeMessage('com.hexenmap.exporter', payload);
    if (result?.ok !== true) throw Error();
    $('state').textContent = 'Enviado para a prévia';
    $('detail').textContent = `${payload.markerIds.length.toLocaleString('pt-BR')} IDs encaminhados. Confira o Hexen Map e confirme a mesclagem.`;
    $('stage').textContent = 'O envio não confirma que o progresso foi importado.';
  } catch (e) {
    if (!nativeStarted) {
      error(e);
      return;
    }
    $('state').textContent = 'Não foi possível enviar';
    $('detail').textContent = 'Abra o Hexen Map atualizado e use Ajustes → Ativar conexão com a extensão. Você também pode baixar o JSON e importar manualmente.';
    $('stage').textContent = 'Nenhuma confirmação de importação recebida.';
  } finally {
    $('loading').hidden = true;
    $('refresh').disabled = false;
    $('send').disabled = current?.state !== 'detected';
    deliveryNotice = `${current?.context}:${current?.revision}`;
    delivering = false;
    setTimeout(() => { deliveryNotice = null; }, 4000);
  }
});

(async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !isSupportedSite(tab.url)) throw Error('Abra o AppSample ou o mapa HoYoLAB e use a extensão nessa aba.');
    tabId = tab.id;
    activeSite = isHoYoLab(tab.url) ? 'hoyolab' : 'appsample';
    if ($('open')) {
      $('open').textContent = activeSite === 'hoyolab' ? 'Abrir HoYoLAB' : 'Abrir AppSample';
    }
    $('refresh').disabled = false;
    try {
      const initialStatus = await chrome.tabs.sendMessage(tabId, { type: 'status' });
      render(initialStatus);
      if (activeSite === 'hoyolab' && initialStatus?.connected && initialStatus.state !== 'not-logged-in') {
        try { await refreshHoYoLab(); } catch (e) { error(e); }
      } else if (activeSite !== 'hoyolab' && initialStatus?.state === 'waiting' && !initialStatus.at) {
        const autoKey = `hexen_autoreloaded_${tabId}_${initialStatus.context}`;
        if (!sessionStorage.getItem(autoKey)) {
          sessionStorage.setItem(autoKey, '1');
          $('stage').textContent = 'Recarregando página para captura automática…';
          await chrome.tabs.reload(tabId);
        }
      }
    } catch {
      const autoKey = `hexen_autoreloaded_disc_${tabId}`;
      if (!sessionStorage.getItem(autoKey)) {
        sessionStorage.setItem(autoKey, '1');
        $('state').textContent = 'Aguardando…';
        $('stage').textContent = 'Conectando observador e recarregando página…';
        try { await chrome.tabs.reload(tabId); } catch {}
      } else {
        disconnected();
      }
    }
  } catch (e) {
    error(e);
  }
})();

// Metadata only. Closing the popup naturally stops this timer.
setInterval(async () => {
  if (tabId === null || delivering || reading) return;
  try { render(await send('status')); } catch { disconnected(); }
}, 1000);
