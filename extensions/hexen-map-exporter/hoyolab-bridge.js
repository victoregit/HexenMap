/* ISOLATED world: HoYoLAB per-document memory, validation, and active-tab popup bridge. */
(() => {
  'use strict';
  if (globalThis.__hexenHoYoLabBridgeV1) return;
  globalThis.__hexenHoYoLabBridgeV1 = true;

  const origin = 'https://act.hoyolab.com';
  const core = HexenHoYoLAB;
  const context = Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, '0')).join('');
  const startedAt = Date.now();

  let snapshot = { state: 'waiting', at: null };
  let revision = 0;
  let connected = false;
  let phase = 'waiting';
  let phaseAt = startedAt;
  let refreshing = null;
  const pendingReads = new Map();

  function refreshAll() {
    if (refreshing) return refreshing;
    refreshing = new Promise((resolve, reject) => {
      const request = Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, '0')).join('');
      const timer = setTimeout(() => {
        pendingReads.delete(request);
        reject(Error('global-read-failed'));
      }, 115000);
      pendingReads.set(request, { resolve, reject, timer });
      window.postMessage({ hexen: 1, type: 'refresh', context, request }, origin);
    }).finally(() => { refreshing = null; });
    return refreshing;
  }
  const EXPECTED_CATALOG_SHA256 = '0d57491936253a8c0546f16c13b1bb0f7ac4c1f90754d06fd4c2f83d5e49f5cc';
  let cachedIndex = globalThis.HexenHoYoLabIndex ?? null;

  async function ensureIndex() {
    if (cachedIndex) {
      if (cachedIndex.source_catalog_sha256 !== EXPECTED_CATALOG_SHA256) return null;
      return cachedIndex;
    }
    if (typeof chrome !== 'undefined' && chrome.runtime?.getURL) {
      try {
        const res = await fetch(chrome.runtime.getURL('hoyolab-index.json'));
        if (res.ok) {
          const idx = await res.json();
          if (idx?.source_catalog_sha256 === EXPECTED_CATALOG_SHA256) {
            cachedIndex = idx;
            return cachedIndex;
          }
        }
      } catch {}
    }
    return null;
  }

  const hello = () => window.postMessage({ hexen: 1, type: 'hello', context }, origin);
  const meta = () => ({
    source: 'hoyolab',
    state: snapshot.state,
    at: snapshot.at,
    count: snapshot.points?.length ?? null,
    context,
    revision,
    connected,
    phase,
    startedAt,
    phaseAt,
    refreshing: refreshing !== null,
    coverage: snapshot.coverage ?? null
  });

  window.addEventListener('message', event => {
    if (event.source !== window || event.origin !== origin) return;
    const m = event.data;
    if (m?.hexen !== 1) return;
    if (m.type === 'ready') { hello(); return; }
    if (m.context !== context) return;
    if (m.type === 'refresh-result') {
      const pending = pendingReads.get(m.request);
      if (!pending) return;
      pendingReads.delete(m.request);
      clearTimeout(pending.timer);
      if (m.error) pending.reject(Error('global-read-failed'));
      else pending.resolve();
      return;
    }

    if (m.type === 'startup-error' && Object.keys(m).length === 3) {
      connected = false;
      phase = 'failed';
      snapshot = { state: 'error', at: Date.now(), points: [] };
      revision++;
      return;
    }

    if (m.type === 'attached' && Object.keys(m).length === 3) {
      connected = true;
      return;
    }

    if (m.type === 'progress' && Object.keys(m).length === 4 &&
        ['waiting', 'request', 'receiving', 'validating', 'ignored'].includes(m.phase)) {
      connected = true;
      if (phase !== m.phase) {
        phase = m.phase;
        phaseAt = Date.now();
      }
      return;
    }

    if (m.type !== 'snapshot' || m.context !== context) return;

    // Defense-in-depth security validation: do not trust context alone
    try {
      if (core.bytes(JSON.stringify(m)) > core.MAX_BYTES) throw Error('Tamanho excessivo');
      if (!['waiting', 'detected', 'not-logged-in', 'not-found', 'error'].includes(m.state)) throw Error('Estado desconhecido');

      const allowedKeys = ['hexen', 'type', 'context', 'state', 'at', 'points', 'coverage'];
      if (Object.keys(m).some(k => !allowedKeys.includes(k))) throw Error('Campos inesperados');
      let coverage = null;
      if (m.coverage !== undefined) {
        const c = m.coverage;
        if (!c || typeof c.complete !== 'boolean' || c.total !== core.SUPPORTED_MAPS.length ||
            !Array.isArray(c.maps) || new Set(c.maps).size !== c.maps.length ||
            c.maps.some(id => !core.SUPPORTED_MAPS.includes(id)) ||
            (c.complete && c.maps.length !== c.total)) throw Error('Cobertura inválida');
        coverage = { complete: c.complete, maps: [...c.maps], total: c.total };
      }

      if (m.state === 'detected') {
        if (!Array.isArray(m.points) || m.points.length > core.MAX_POINTS) throw Error('Lista inválida');
        // Rigorous point schema check
        const sanitized = [];
        for (const pt of m.points) {
          if (!pt || typeof pt !== 'object') throw Error('Item não-objeto');
          const mapId = String(pt.map_id ?? '');
          const pointId = String(pt.point_id ?? '');
          if (!/^[0-9]{1,16}$/.test(mapId) || !/^[0-9]{1,32}$/.test(pointId)) throw Error('ID inválido');
          sanitized.push({ map_id: mapId, point_id: pointId });
        }
        snapshot = { state: 'detected', points: sanitized, at: Date.now(), coverage };
      } else {
        snapshot = { state: m.state, at: Date.now(), coverage };
      }
    } catch {
      snapshot = { state: 'error', at: Date.now(), points: [] };
    }
    revision++;
  });

  chrome.runtime.onMessage.addListener((m, sender, reply) => {
    // MessageSender.url is optional. Own-extension pages only, never content scripts.
    if (sender.id !== chrome.runtime.id || sender.tab || (sender.url && sender.url !== chrome.runtime.getURL('popup.html'))) {
      return;
    }
    if (m?.type === 'status') {
      if (snapshot.state === 'detected') {
        void (async () => {
          const index = await ensureIndex();
          if (index && snapshot.state === 'detected') {
            const res = core.resolve(snapshot.points, index);
            reply({
              ...meta(),
              stats: {
                total_found: res.total_found,
                matched_safe: res.matched_safe,
                ambiguous: res.ambiguous,
                unmatched: res.unmatched,
                unsupported_map: res.unsupported_map,
                ambiguous_points: res.ambiguous_points,
                unmatched_points: res.unmatched_points,
                unsupported_map_points: res.unsupported_map_points
              }
            });
            return;
          }
          reply(meta());
        })();
        return true;
      }
      reply(meta());
      return;
    }
    if (m?.context !== context || m.revision !== revision) {
      reply({ error: 'context-changed' });
      return;
    }
    if (m.type === 'refresh' || m.type === 'export') {
      void (async () => {
        try {
        await refreshAll();
        if (m.type === 'refresh') { reply(meta()); return; }
        if (!snapshot.coverage?.complete || !['detected', 'not-found'].includes(snapshot.state)) {
          reply({ error: snapshot.state === 'not-logged-in' ? 'not-logged-in' : 'global-read-failed' });
          return;
        }
        const exportRevision = revision;
        const index = await ensureIndex();
        if (!index) {
          reply({ error: 'index-unavailable' });
          return;
        }
        // Resolve a stable snapshot only; a concurrent account/map change invalidates it.
        if (revision !== exportRevision || !snapshot.coverage?.complete) { reply({ error: 'context-changed' }); return; }
        const res = core.resolve(snapshot.points ?? [], index);
        reply({
          ...meta(),
          stats: {
            total_found: res.total_found,
            matched_safe: res.matched_safe,
            ambiguous: res.ambiguous,
            unmatched: res.unmatched,
            unsupported_map: res.unsupported_map,
            ambiguous_points: res.ambiguous_points,
            unmatched_points: res.unmatched_points,
            unsupported_map_points: res.unsupported_map_points
          },
          payload: {
            source: 'appsample',
            version: 1,
            markerIds: res.markerIds
          }
        });
        } catch {
          reply({ error: 'global-read-failed', ...meta() });
        }
      })();
      return true; // Keep message channel open for async response
    } else if (m.type === 'clear') {
      window.postMessage({ hexen: 1, type: 'clear', context }, origin);
      snapshot = { state: 'waiting', at: null };
      phase = 'waiting';
      phaseAt = Date.now();
      revision++;
      reply(meta());
    }
  });

  hello();
})();
