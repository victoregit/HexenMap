/* MAIN world: observe HoYoLAB and read all supported maps with the browser session. */
(() => {
  'use strict';
  if (window.__hexenHoYoLabCaptureV1) return;
  const origin = 'https://act.hoyolab.com';
  let context = null, early = null, phase = 'waiting', running = false, observer = null;

  function progress(next) {
    phase = next;
    if (context) window.postMessage({ hexen: 1, type: 'progress', context, phase }, origin);
  }

  function publish(snapshot) {
    if (snapshot.state === 'ignored') return;
    if (!context) {
      early = snapshot;
      return;
    }
    window.postMessage({ hexen: 1, type: 'snapshot', context, ...snapshot }, origin);
    early = null;
  }

  window.addEventListener('message', event => {
    if (event.source !== window || event.origin !== origin) return;
    const m = event.data;
    if (m?.hexen !== 1 || !m.type || typeof m.context !== 'string' || !/^[a-f0-9]{32}$/.test(m.context)) return;
    if (context && context !== m.context) return;
    if (m.type === 'refresh' && context && /^[a-f0-9]{32}$/.test(m.request)) {
      void observer.refreshAll().then(
        () => window.postMessage({ hexen: 1, type: 'refresh-result', context, request: m.request }, origin),
        () => window.postMessage({ hexen: 1, type: 'refresh-result', context, request: m.request, error: 'global-read-failed' }, origin)
      );
      return;
    }
    if (m.type === 'clear') {
      if (observer && typeof observer.advanceEpoch === 'function') {
        observer.advanceEpoch('bridge-clear');
      }
      return;
    }
    if (m.type !== 'hello') return;
    context = m.context;
    if (!running) {
      window.postMessage({ hexen: 1, type: 'startup-error', context }, origin);
      return;
    }
    window.postMessage({ hexen: 1, type: 'attached', context }, origin);
    progress(phase);
    if (early) publish(early);
  });

  try {
    observer = HexenHoYoLAB.observe(publish, progress);
    running = true;
    window.__hexenHoYoLabCaptureV1 = true;
  } catch {
    phase = 'failed';
  }

  window.postMessage({ hexen: 1, type: 'ready' }, origin);
})();
