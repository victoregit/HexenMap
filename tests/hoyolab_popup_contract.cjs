'use strict';
// HoYoLAB Popup contract: simulates popup interaction on act.hoyolab.com
const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const root = process.argv[2] || path.resolve(__dirname, '..');
const elements = new Map();
let interval, blob, downloads = 0, reloads = 0, created = 0, nativePayload = null;
let confirmResult = true, confirmCalls = [], refreshes = 0, exportCalls = 0, failExport = false;
const coverage = { complete: true, maps: ['2', '7', '9', '34', '36', '37', '40'], total: 7 };

const elementIds = ['state', 'detail', 'export', 'refresh', 'open', 'loading', 'stage', 'send', 'stats', 'extension-version'];
for (const id of elementIds) {
  elements.set(id, {
    disabled: false,
    hidden: false,
    textContent: '',
    innerHTML: '',
    handlers: {},
    addEventListener(e, f) { this.handlers[e] = f; }
  });
}

let snapshot = {
  source: 'hoyolab',
  state: 'not-logged-in',
  at: 1000,
  count: 0,
  context: 'b'.repeat(32),
  revision: 1,
  connected: true
};
let activeTabId = 42;
const hoyoUrl = 'https://act.hoyolab.com/ys/app/interactive-map/index.html';

const U = class extends URL {};
U.createObjectURL = b => { blob = b; return 'blob:local'; };
U.revokeObjectURL = () => {};

const c = {
  URL: U,
  TextEncoder,
  TextDecoder,
  Blob,
  console,
  setTimeout: () => {},
  setInterval: f => { interval = f; },
  confirm: msg => { confirmCalls.push(msg); return confirmResult; },
  document: {
    getElementById: id => elements.get(id),
    createElement: () => ({
      click: () => downloads++,
      download: ''
    })
  },
  chrome: {
    runtime: {
      getManifest: () => ({ version: '9.8.7' }),
      sendNativeMessage: async (host, payload) => {
        assert.equal(host, 'com.hexenmap.exporter');
        assert.deepEqual(Object.keys(payload).sort(), ['markerIds', 'source', 'version']);
        nativePayload = payload;
        return { ok: true, count: payload.markerIds.length, status: 'queued' };
      }
    },
    tabs: {
      query: async () => [{ id: activeTabId, url: hoyoUrl }],
      sendMessage: async (id, m) => {
        assert.equal(id, activeTabId);
        if (m.type === 'status') return { ...snapshot };
        if (m.type === 'refresh') {
          refreshes++;
          snapshot = { ...snapshot, coverage, revision: snapshot.revision + 1 };
          return snapshot;
        }
        if (m.type === 'clear') {
          snapshot = { ...snapshot, state: 'waiting', count: null, revision: 2 };
          return snapshot;
        }
        if (m.type === 'export') {
          exportCalls++;
          if (failExport) return { error: 'global-read-failed' };
          snapshot = { ...snapshot, coverage, revision: snapshot.revision + 1 };
          return {
            ...snapshot,
            stats: {
              total_found: 4,
              matched_safe: 2,
              ambiguous: 1,
              unmatched: 1,
              unsupported_map: 0
            },
            payload: { source: 'appsample', version: 1, markerIds: ['107155', '107156'] }
          };
        }
      },
      reload: async () => reloads++,
      create: async () => created++
    }
  }
};
c.window = c;

vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(root, 'data', 'import', 'appsample-core.js'), 'utf8'), c);
vm.runInContext(fs.readFileSync(path.join(root, 'extensions', 'hexen-map-exporter', 'popup.js'), 'utf8'), c);

(async () => {
  await new Promise(r => setImmediate(r));

  console.log('--- 1. Initial Unauthenticated HoYoLAB Popup State ---');
  assert.equal(elements.get('extension-version').textContent, 'EXPORTAÇÃO LOCAL · v9.8.7');
  assert.equal(elements.get('state').textContent, 'Sessão não autenticada');
  assert(elements.get('detail').textContent.includes('Faça login'));
  assert.equal(elements.get('export').disabled, true);
  assert.equal(elements.get('send').disabled, true);
  assert.equal(elements.get('open').textContent, 'Abrir HoYoLAB');

  console.log('--- 2. Transition to Detected HoYoLAB State ---');
  snapshot = {
    source: 'hoyolab',
    state: 'detected',
    at: Date.now(),
    count: 4,
    context: 'b'.repeat(32),
    revision: 3,
    connected: true,
    stats: {
      total_found: 4,
      matched_safe: 2,
      ambiguous: 1,
      unmatched: 1,
      unsupported_map: 0
    }
  };
  await interval();

  assert.equal(elements.get('state').textContent, 'Progresso HoYoLAB detectado');
  assert(elements.get('detail').textContent.includes('2 marcadores convertidos'));
  assert.equal(elements.get('export').disabled, false);
  assert.equal(elements.get('send').disabled, false);
  assert.equal(elements.get('stats').hidden, false);
  assert(elements.get('stats').innerHTML.includes('Concluídos nos mapas lidos:'));
  assert(elements.get('stage').textContent.includes('Leitura parcial'));
  assert(elements.get('stats').innerHTML.includes('Correspondentes AppSample:'));
  assert(elements.get('stats').innerHTML.includes('Ambíguos rejeitados:'));
  assert(elements.get('stats').innerHTML.includes('Sem correspondência:'));

  console.log('--- 3. User Export (JSON Download) with Confirmation ---');
  // First test cancellation:
  confirmResult = false;
  await elements.get('export').handlers.click();
  assert.equal(downloads, 0); // Cancelled, no download
  assert.equal(confirmCalls.length, 1);

  // Then test confirmation:
  confirmResult = true;
  await elements.get('export').handlers.click();
  assert.equal(downloads, 1);
  assert.equal(exportCalls, 2); // Both attempts refresh on export, even after earlier detection.
  assert(elements.get('stage').textContent.includes('7 de 7 mapas'));
  const downloadedJson = JSON.parse(await blob.text());
  assert.deepEqual(downloadedJson, {
    source: 'appsample',
    version: 1,
    markerIds: ['107155', '107156']
  });

  console.log('--- 4. Send to Hexen Map via Native Messaging ---');
  confirmResult = true;
  await elements.get('send').handlers.click();
  assert.equal(elements.get('state').textContent, 'Enviado para a prévia');
  assert.deepEqual(JSON.parse(JSON.stringify(nativePayload)), {
    source: 'appsample',
    version: 1,
    markerIds: ['107155', '107156']
  });

  console.log('--- 5. Default Global Refresh & Open Actions ---');
  await elements.get('refresh').handlers.click();
  assert.equal(reloads, 0);
  assert.equal(refreshes, 1);

  // A failed global read must never download or send a partial payload.
  failExport = true;
  await elements.get('export').handlers.click();
  assert.equal(downloads, 1);
  assert(elements.get('detail').textContent.includes('todos os mapas'));
  nativePayload = null;
  await elements.get('send').handlers.click();
  assert.equal(nativePayload, null);
  assert(elements.get('detail').textContent.includes('todos os mapas'));

  await elements.get('open').handlers.click();
  assert.equal(created, 1);

  // Reopening on an authenticated page refreshes all maps through the same action.
  const reopened = { ...c };
  reopened.window = reopened;
  vm.createContext(reopened);
  vm.runInContext(fs.readFileSync(path.join(root, 'data', 'import', 'appsample-core.js'), 'utf8'), reopened);
  vm.runInContext(fs.readFileSync(path.join(root, 'extensions', 'hexen-map-exporter', 'popup.js'), 'utf8'), reopened);
  await new Promise(r => setImmediate(r));
  assert.equal(refreshes, 2);
  assert.equal(reloads, 0);

  console.log('HoYoLAB popup contract tests passed successfully!');
})().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
