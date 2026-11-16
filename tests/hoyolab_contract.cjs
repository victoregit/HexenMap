'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const root = process.argv[2] || path.resolve(__dirname, '..');
const corePath = path.join(root, 'extensions', 'hexen-map-exporter', 'hoyolab-core.js');
const capturePath = path.join(root, 'extensions', 'hexen-map-exporter', 'hoyolab-capture.js');
const bridgePath = path.join(root, 'extensions', 'hexen-map-exporter', 'hoyolab-bridge.js');
const indexPath = path.join(root, 'extensions', 'hexen-map-exporter', 'hoyolab-index.json');

const coreText = fs.readFileSync(corePath, 'utf8');
const captureText = fs.readFileSync(capturePath, 'utf8');
const bridgeText = fs.readFileSync(bridgePath, 'utf8');
const indexData = JSON.parse(fs.readFileSync(indexPath, 'utf8'));

const hoyoOrigin = 'https://act.hoyolab.com';
const endpoint = 'https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2';

function makePayload(points = [{ point_id: 106902, map_id: 2, status: 1 }], retcode = 0) {
  if (retcode === -2004) {
    return { data: null, message: 'Please log in first', retcode: -2004 };
  }
  if (retcode !== 0) {
    return { data: null, message: 'System error', retcode };
  }
  return {
    data: { point_list: points },
    message: 'OK',
    retcode: 0
  };
}

function env() {
  class XHR {
    constructor() {
      this.events = new Map();
      this.status = 200;
      this.responseType = '';
      this.responseText = '';
    }
    open(method, url) {
      this.method = method;
      this.url = url;
      return 42;
    }
    addEventListener(e, f) {
      if (!this.events.has(e)) this.events.set(e, new Set());
      this.events.get(e).add(f);
    }
    removeEventListener(e, f) {
      this.events.get(e)?.delete(f);
    }
    fire(type) {
      for (const f of [...(this.events.get(type) || [])]) f({ type });
    }
  }

  let fetchImpl = () => Promise.resolve(new Response(JSON.stringify(makePayload())));
  const c = {
    URL,
    TextEncoder,
    TextDecoder,
    Uint8Array,
    Response,
    URLSearchParams, AbortController, setTimeout, clearTimeout,
    location: { href: hoyoOrigin + '/ys/app/interactive-map/index.html' },
    XMLHttpRequest: XHR,
    fetch: (...args) => fetchImpl(...args)
  };
  c.setFetchImpl = f => fetchImpl = f;
  c.window = c;
  c.globalThis = c;
  vm.createContext(c);
  vm.runInContext(coreText, c);
  return c;
}

const tick = () => new Promise(r => setTimeout(r, 20));

(async () => {
  console.log('--- 1. Testing HexenHoYoLAB Core Unit Logic ---');
  const c = env();
  const k = c.HexenHoYoLAB;

  // Endpoint targeting
  assert(k.target('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2'));
  assert(k.target('https://api-os-takumi.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list'));
  assert(k.target('https://act.hoyolab.com/ys/app/interactive-map/mark_map_point_list?map_id=2'));
  assert(!k.target('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/list?map_id=2'));
  assert(!k.target('https://evil.hoyolab.com.attacker.com/mark_map_point_list'));
  assert(!k.target('https://firestore.googleapis.com/v1/projects/genshin-impact'));
  assert(!k.target('https://sg-public-api.hoyolab.com/other/api'));

  // parseMapIdFromUrl
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/?map_id=2'), '2');
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/?map_id=7'), '7');
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/ys/app/interactive-map/#/map/9?shown_types=1'), '9');
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/ys/app/interactive-map/#/map/34'), '34');
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/ys/app/interactive-map/#/map/36'), '36');
  assert.equal(k.parseMapIdFromUrl('https://act.hoyolab.com/no_map'), '2');
  assert.equal(k.parseMapIdFromUrl('invalid-url'), '2');

  // Payload extraction: valid cases
  const valid = k.extract(makePayload([{ point_id: 106902, map_id: 2, status: 1 }, { point_id: '106903', status: 1 }]));
  assert.equal(valid.state, 'detected');
  assert.equal(valid.points.length, 2);
  assert.equal(valid.points[0].map_id, '2');
  assert.equal(valid.points[0].point_id, '106902');
  assert.equal(valid.points[1].map_id, '2');
  assert.equal(valid.points[1].point_id, '106903');

  // Valid items extracted faithfully without speculative status guessing
  const withCustom = k.extract(makePayload([
    { point_id: 106902, map_id: 2, status: 1 },
    { point_id: 999999, map_id: 2, status: 0 }
  ]));
  assert.equal(withCustom.points.length, 2);
  assert.equal(withCustom.points[0].point_id, '106902');
  assert.equal(withCustom.points[1].point_id, '999999');

  // Deduplication
  const withDupes = k.extract(makePayload([
    { point_id: 106902, map_id: 2 },
    { point_id: 106902, map_id: 2 },
    { point_id: 106902, map_id: 7 }
  ]));
  assert.equal(withDupes.points.length, 2); // '2:106902' and '7:106902' are distinct compound keys

  // Alternative point lists
  const altPoints = k.extract({ retcode: 0, data: { points: [100, 200] } });
  assert.equal(altPoints.state, 'detected');
  assert.equal(altPoints.points.length, 2);

  // Unauthenticated / Logged out
  const loggedOut = k.extract(makePayload(null, -2004));
  assert.equal(loggedOut.state, 'not-logged-in');
  assert.equal(loggedOut.points.length, 0);

  // API error
  const apiErr = k.extract(makePayload(null, 10001));
  assert.equal(apiErr.state, 'error');
  assert.equal(apiErr.points.length, 0);

  // Missing data
  const missingData = k.extract({ retcode: 0, data: null });
  assert.equal(missingData.state, 'not-found');

  // Empty point list
  const emptyList = k.extract(makePayload([]));
  assert.equal(emptyList.state, 'detected');
  assert.equal(emptyList.points.length, 0);

  // Malformed inputs & bounds
  assert.throws(() => k.extract(null));
  assert.throws(() => k.extract('string'));
  assert.throws(() => k.extract({ junk: 'x'.repeat(k.MAX_BYTES + 1) }));
  assert.throws(() => k.extract({ retcode: 0, data: { point_list: Array(k.MAX_POINTS + 1).fill(1) } }));

  // ID resolution with actual hoyolab-index.json (Teyvat and Phase A, B.1, B.2 & B.3 maps)
  const res = k.resolve([
    { map_id: '2', point_id: '106902' }, // Known 1:1 mapped point -> AppSample 107156
    { map_id: '2', point_id: '106903' }, // Known 1:1 mapped point -> AppSample 107155
    { map_id: '9', point_id: '25278' },  // Map 9 Chasm -> AppSample 28492
    { map_id: '34', point_id: '68620' }, // Map 34 Bygone Eras -> AppSample 69668
    { map_id: '36', point_id: '84140' }, // Map 36 Sacred Mountain -> AppSample 83746
    { map_id: '7', point_id: '24379' },  // Map 7 Enkanomiya -> AppSample 27063
    { map_id: '37', point_id: '96569' }, // Map 37 Temple of Space -> AppSample 96388
    { map_id: '40', point_id: '100285' }, // Map 40 Frost Moon -> AppSample 100874
    { map_id: '2', point_id: '99999999' }, // Unmatched
    { map_id: '8', point_id: '1001' } // Seasonal Archipelago (unsupported map)
  ], indexData);

  assert.equal(res.total_found, 10);
  assert.equal(res.matched_safe, 8);
  assert.equal(res.unmatched, 1);
  assert.equal(res.unsupported_map, 1);
  assert.deepEqual(Array.from(res.markerIds), ['27063', '28492', '69668', '83746', '96388', '100874', '107155', '107156']);
  assert.equal(typeof res.markerIds[0], 'string');

  // Resolution with ambiguous points
  const testIndex = {
    mapping: {
      '2:1': '10',
      '2:2': '20',
      '2:3': 'ambiguous'
    }
  };
  const resAmbiguous = k.resolve([
    { map_id: '2', point_id: '1' },
    { map_id: '2', point_id: '2' },
    { map_id: '2', point_id: '3' },
    { map_id: '2', point_id: '4' }
  ], testIndex);
  assert.equal(resAmbiguous.total_found, 4);
  assert.equal(resAmbiguous.matched_safe, 2);
  assert.equal(resAmbiguous.ambiguous, 1);
  assert.equal(resAmbiguous.unmatched, 1);
  assert.deepEqual(Array.from(resAmbiguous.markerIds), ['10', '20']);
  assert.deepEqual(Array.from(resAmbiguous.ambiguous_points), ['2:3']);
  assert.deepEqual(Array.from(resAmbiguous.unmatched_points), ['2:4']);

  console.log('--- 2. Testing HexenHoYoLAB Observer (fetch & XHR) ---');
  let outputs = [];
  const origFetch = c.fetch;
  const origOpen = c.XMLHttpRequest.prototype.open;
  const stopObserver = k.observe(s => outputs.push(s));

  // Intercept fetch
  c.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([{ point_id: 106902, map_id: 2 }])))));
  await c.fetch(endpoint);
  await tick();
  assert.equal(outputs.at(-1).state, 'detected');
  assert.equal(outputs.at(-1).points.length, 1);

  // Ignored non-target fetch
  await c.fetch('https://example.com/api');
  await tick();
  assert.equal(outputs.length, 1);

  // Fetch with network error
  c.setFetchImpl(() => Promise.reject(new Error('Network error')));
  try { await c.fetch(endpoint); } catch {}
  await tick();
  assert.equal(outputs.at(-1).state, 'error');

  // Intercept XHR with responseType = 'json'
  const xhr1 = new c.XMLHttpRequest();
  xhr1.open('GET', endpoint);
  xhr1.responseType = 'json';
  xhr1.response = makePayload([{ point_id: 106903, map_id: 2 }]);
  xhr1.status = 200;
  xhr1.fire('load');
  await tick();
  assert.equal(outputs.at(-1).state, 'detected');
  assert.equal(outputs.at(-1).points[0].point_id, '106903');

  // XHR with responseType = '' and invalid json
  const xhr2 = new c.XMLHttpRequest();
  xhr2.open('GET', endpoint);
  xhr2.status = 200;
  xhr2.responseText = '{malformed json';
  xhr2.fire('load');
  await tick();
  assert.equal(outputs.at(-1).state, 'error');

  // XHR abort
  const xhr3 = new c.XMLHttpRequest();
  xhr3.open('GET', endpoint);
  xhr3.fire('abort');
  await tick();
  assert.equal(outputs.at(-1).state, 'error');

  // XHR status 500
  const xhr4 = new c.XMLHttpRequest();
  xhr4.open('GET', endpoint);
  xhr4.status = 500;
  xhr4.fire('load');
  await tick();
  assert.equal(outputs.at(-1).state, 'error');

  // Intercept mark mutation via fetch
  c.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({ retcode: 0, message: 'OK', data: null }))));
  await c.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/set_point_mark', {
    method: 'POST',
    body: JSON.stringify({ map_id: 2, point_id: 999999, mark_status: 1 })
  });
  await tick();
  assert.equal(outputs.at(-1).state, 'detected');
  assert(outputs.at(-1).points.some(p => p.point_id === '999999'));

  // Intercept unmark mutation via fetch
  await c.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/set_point_mark', {
    method: 'POST',
    body: JSON.stringify({ map_id: 2, point_id: 999999, mark_status: 0 })
  });
  await tick();
  assert.equal(outputs.at(-1).state, 'detected');
  assert(!outputs.at(-1).points.some(p => p.point_id === '999999'));

  // Stop observer and verify restoration
  stopObserver();
  assert.equal(c.XMLHttpRequest.prototype.open, origOpen);

  console.log('--- 3. Testing MAIN <-> ISOLATED Bridge Contracts ---');
  function createPage(preloadIndex = true) {
    const p = env();
    const listeners = [];
    const runtimeHandlers = [];
    let sender;
    const windowProxy = vm.runInContext('window', p);

    p.crypto = require('node:crypto').webcrypto;
    p.addEventListener = (type, f) => {
      if (type === 'message') listeners.push(f);
    };
    p.postMessage = (data, originValue) => {
      setImmediate(() => {
        for (const f of listeners) f({ source: windowProxy, origin: originValue, data });
      });
    };
    if (preloadIndex) {
      p.HexenHoYoLabIndex = indexData;
    }
    p.chrome = {
      runtime: {
        id: 'hexen-test-ext',
        getURL: s => 'chrome-extension://hexen-test-ext/' + s,
        onMessage: { addListener: f => runtimeHandlers.push(f) }
      }
    };

    const runScript = code => vm.runInContext(code, p);
    const request = m => new Promise(resolve => {
      let resolved = false;
      const done = r => {
        if (!resolved) {
          resolved = true;
          resolve(r);
        }
      };
      let keptOpen = false;
      for (const h of runtimeHandlers) {
        const res = h(m, sender ?? { id: 'hexen-test-ext', url: 'chrome-extension://hexen-test-ext/popup.html' }, done);
        if (res === true) keptOpen = true;
      }
      if (!keptOpen && !resolved) {
        done(undefined);
      }
    });
    const inject = (data, source = windowProxy, where = hoyoOrigin) => {
      for (const f of listeners) f({ source, origin: where, data });
    };

    return { p, runScript, request, inject, setSender: s => sender = s };
  }

  // Test full flow: capture -> fetch -> bridge -> popup export
  const page1 = createPage(true);
  page1.p.setFetchImpl(url => Promise.resolve(new Response(JSON.stringify(makePayload(new URL(url).searchParams.get('map_id') === '2' ? [
    { point_id: 106902, map_id: 2, status: 1 },
    { point_id: 106903, map_id: 2, status: 1 }
  ] : [])))));
  page1.runScript(captureText);
  await page1.p.fetch(endpoint);
  await tick();

  page1.runScript(bridgeText);
  await tick();

  // Status check
  let status = await page1.request({ type: 'status' });
  assert.equal(status.state, 'detected');
  assert.equal(status.count, 2);
  assert.equal(status.connected, true);
  assert.equal(typeof status.context, 'string');
  assert.equal(status.context.length, 32);

  // Export check
  const expQuery = { type: 'export', context: status.context, revision: status.revision };
  let exportRes = await page1.request(expQuery);
  assert(exportRes, 'Export should return response');
  assert.equal(exportRes.payload.source, 'appsample');
  assert.equal(exportRes.payload.version, 1);
  assert.deepEqual(Array.from(exportRes.payload.markerIds), ['107155', '107156']);
  assert.equal(exportRes.stats.matched_safe, 2);
  assert.equal(exportRes.stats.ambiguous, 0);
  assert.equal(exportRes.stats.unmatched, 0);
  assert.equal(exportRes.coverage.complete, true);
  assert.equal(exportRes.coverage.maps.length, 7);
  status = await page1.request({ type: 'status' });

  // Clear check
  let clearRes = await page1.request({ type: 'clear', context: status.context, revision: status.revision });
  assert.equal(clearRes.state, 'waiting');
  assert.equal((await page1.request({ type: 'status' })).state, 'waiting');

  // Security: Foreign extension sender
  page1.setSender({ id: 'foreign-extension-id', url: 'chrome-extension://foreign-extension-id/popup.html' });
  assert.equal(await page1.request({ type: 'status' }), undefined);

  // Security: Tab-level sender (content script impersonation)
  page1.setSender({ id: 'hexen-test-ext', tab: { id: 123 } });
  assert.equal(await page1.request({ type: 'status' }), undefined);
  page1.setSender(null);

  // Security: Context mismatch on export
  const staleExport = await page1.request({ type: 'export', context: 'wrongcontext12345678901234567890', revision: status.revision });
  assert.equal(staleExport.error, 'context-changed');

  // Security: Foreign postMessage origin
  const page2 = createPage(true);
  page2.runScript(bridgeText);
  page2.runScript(captureText);
  await tick();
  let status2 = await page2.request({ type: 'status' });

  // Attacker tries to inject fake snapshot from evil origin
  page2.inject({
    hexen: 1,
    type: 'snapshot',
    context: status2.context,
    state: 'detected',
    points: [{ map_id: '2', point_id: '999999' }]
  }, vm.runInContext('window', page2.p), 'https://evil.attacker.com');
  await tick();
  assert.equal((await page2.request({ type: 'status' })).count, null); // Injection ignored!

  // Security: Disallowed field in snapshot (defense-in-depth)
  page2.inject({
    hexen: 1,
    type: 'snapshot',
    context: status2.context,
    state: 'detected',
    points: [{ map_id: '2', point_id: '106902' }],
    malicious_extra_field: 'exploit'
  });
  await tick();
  assert.equal((await page2.request({ type: 'status' })).state, 'error'); // Disallowed fields cause state: 'error'

  // Security: Malformed point ID in snapshot
  const page3 = createPage(true);
  page3.runScript(bridgeText);
  page3.runScript(captureText);
  await tick();
  let status3 = await page3.request({ type: 'status' });
  page3.inject({
    hexen: 1,
    type: 'snapshot',
    context: status3.context,
    state: 'detected',
    points: [{ map_id: '2', point_id: '../evil/payload' }]
  });
  await tick();
  assert.equal((await page3.request({ type: 'status' })).state, 'error');

  // Test Logged-out API response end-to-end
  const page4 = createPage(true);
  page4.p.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload(null, -2004)))));
  page4.runScript(captureText);
  await page4.p.fetch(endpoint);
  await tick();
  page4.runScript(bridgeText);
  await tick();
  let status4 = await page4.request({ type: 'status' });
  assert.equal(status4.state, 'not-logged-in');
  assert.equal(status4.connected, true);

  console.log('--- 4. Testing Multi-Map Accumulation, Concurrency & Session Lifecycle ---');
  const mmPage = createPage(true);
  mmPage.runScript(bridgeText);
  mmPage.runScript(captureText);
  await tick();

  // 4.1. Fast switching and accumulation across maps 2, 9, 34, 36
  mmPage.inject({
    hexen: 1, type: 'snapshot', context: (await mmPage.request({ type: 'status' })).context,
    state: 'detected',
    points: [{ map_id: '2', point_id: '106902' }, { map_id: '2', point_id: '106903' }]
  });
  await tick();
  assert.equal((await mmPage.request({ type: 'status' })).count, 2);

  // Add Map 9
  mmPage.inject({
    hexen: 1, type: 'snapshot', context: (await mmPage.request({ type: 'status' })).context,
    state: 'detected',
    points: [{ map_id: '2', point_id: '106902' }, { map_id: '2', point_id: '106903' }, { map_id: '9', point_id: '25278' }]
  });
  await tick();
  assert.equal((await mmPage.request({ type: 'status' })).count, 3);

  // Add Map 34, 36, 7, 37, and 40
  mmPage.inject({
    hexen: 1, type: 'snapshot', context: (await mmPage.request({ type: 'status' })).context,
    state: 'detected',
    points: [
      { map_id: '2', point_id: '106902' }, { map_id: '2', point_id: '106903' },
      { map_id: '9', point_id: '25278' },
      { map_id: '34', point_id: '68620' },
      { map_id: '36', point_id: '84140' },
      { map_id: '7', point_id: '24379' },
      { map_id: '37', point_id: '96569' },
      { map_id: '40', point_id: '100285' }
    ]
  });
  await tick();
  const mmStatus = await mmPage.request({ type: 'status' });
  assert.equal(mmStatus.count, 8);
  assert.equal(mmStatus.stats.matched_safe, 8);
  assert.equal(mmStatus.stats.unmatched, 0);
  assert.equal(mmStatus.stats.unsupported_map, 0);

  const byMap = { '2': ['106902', '106903'], '7': ['24379'], '9': ['25278'], '34': ['68620'], '36': ['84140'], '37': ['96569'], '40': ['100285'] };
  const requestedMaps = [];
  mmPage.p.setFetchImpl((url, init) => {
    const id = new URL(url).searchParams.get('map_id');
    requestedMaps.push(id);
    assert.equal(init.credentials, 'include');
    assert.equal(init.headers, undefined);
    return Promise.resolve(new Response(JSON.stringify(makePayload(byMap[id].map(point_id => ({ point_id, map_id: id }))))));
  });
  const mmExport = await mmPage.request({ type: 'export', context: mmStatus.context, revision: mmStatus.revision });
  assert.equal(mmExport.payload.source, 'appsample');
  assert.equal(mmExport.payload.version, 1);
  assert.deepEqual(Array.from(mmExport.payload.markerIds), ['27063', '28492', '69668', '83746', '96388', '100874', '107155', '107156']);
  assert.deepEqual(requestedMaps, ['2', '7', '9', '34', '36', '37', '40']);

  // The existing refresh action reads all maps without navigation, even starting empty.
  const globalPage = createPage(true);
  globalPage.runScript(bridgeText);
  globalPage.runScript(captureText);
  await tick();
  const api = (url) => {
    const id = new URL(url).searchParams.get('map_id');
    return Promise.resolve(new Response(JSON.stringify(makePayload(byMap[id].map(point_id => ({ point_id, map_id: id }))))));
  };
  globalPage.p.setFetchImpl(api);
  let globalStatus = await globalPage.request({ type: 'status' });
  const refreshed = await globalPage.request({ type: 'refresh', context: globalStatus.context, revision: globalStatus.revision });
  assert.equal(refreshed.coverage.complete, true);
  assert.equal(refreshed.count, 8);
  globalStatus = await globalPage.request({ type: 'status' });
  globalPage.p.setFetchImpl(url => new URL(url).searchParams.get('map_id') === '9' ?
    Promise.resolve(new Response('{}', { status: 503 })) : api(url));
  const failedExport = await globalPage.request({ type: 'export', context: globalStatus.context, revision: globalStatus.revision });
  assert.equal(failedExport.error, 'global-read-failed');
  assert.equal(failedExport.payload, undefined);
  assert.equal(failedExport.coverage.complete, false);

  // Concurrent refreshes share one read; empty maps still count toward coverage.
  const fresh = env();
  let freshOutputs = [], freshCalls = 0;
  const freshObserver = fresh.HexenHoYoLAB.observe(s => freshOutputs.push(s));
  fresh.setFetchImpl(() => {
    freshCalls++;
    return Promise.resolve(new Response(JSON.stringify(makePayload([]))));
  });
  const firstRead = freshObserver.refreshAll();
  const secondRead = freshObserver.refreshAll();
  assert.equal(firstRead, secondRead);
  const emptyGlobal = await firstRead;
  assert.equal(freshCalls, 7);
  assert.equal(emptyGlobal.state, 'not-found');
  assert.equal(emptyGlobal.coverage.complete, true);
  // Missing data, pagination and foreign-map data must never be treated as complete.
  for (const bad of [
    { retcode: 0, data: null },
    { retcode: 0, data: { list: [], has_more: true } },
    makePayload([{ map_id: '9', point_id: '25278' }])
  ]) {
    fresh.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(bad))));
    await assert.rejects(freshObserver.refreshAll());
    assert.equal(freshOutputs.at(-1).coverage.complete, false);
  }
  // Logged-out reads stop immediately and never export an earlier account's data.
  fresh.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload(null, -2004)))));
  assert.equal((await freshObserver.refreshAll()).state, 'not-logged-in');
  assert.equal(freshOutputs.at(-1).points.length, 0);

  // Account switching while a request is in flight invalidates the whole read.
  const switching = env();
  switching.document = { cookie: 'account_id_v2=account_A' };
  let releaseRead;
  const switchingOutputs = [];
  const switchingObserver = switching.HexenHoYoLAB.observe(s => switchingOutputs.push(s));
  switching.setFetchImpl(() => new Promise(resolve => { releaseRead = resolve; }));
  const switchingRead = switchingObserver.refreshAll();
  switching.document.cookie = 'account_id_v2=account_B';
  releaseRead(new Response(JSON.stringify(makePayload([{ map_id: '2', point_id: '106902' }]))));
  await assert.rejects(switchingRead);
  assert(!switchingOutputs.some(s => s.coverage?.complete));

  // A failed map is retried by the normal refresh action, restoring a complete snapshot.
  globalPage.p.setFetchImpl(api);
  const retryStatus = await globalPage.request({ type: 'status' });
  const retried = await globalPage.request({ type: 'refresh', context: retryStatus.context, revision: retryStatus.revision });
  assert.equal(retried.coverage.complete, true);
  assert.equal(retried.count, 8);

  // 4.2. Core observer deliver: sequential map accumulation via fetch
  const obsPage = env();
  let obsOutputs = [];
  const obsCore = obsPage.HexenHoYoLAB;
  obsCore.observe(s => obsOutputs.push(s));

  // Map 2 arrives with 2 points
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }, { point_id: '106903', map_id: '2' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 2);

  // Map 9 arrives with 1 point -> accumulated to 3
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '25278', map_id: '9' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=9');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 3);

  // Map 34 arrives with 1 point -> accumulated to 4
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '68620', map_id: '34' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=34');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 4);

  // Map 36 arrives with 1 point -> accumulated to 5
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '84140', map_id: '36' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=36');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 5);

  // Map 7 arrives with 1 point -> accumulated to 6
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '24379', map_id: '7' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=7');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 6);

  // Map 37 arrives with 1 point -> accumulated to 7
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '96569', map_id: '37' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=37');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 7);

  // Map 40 arrives with 1 point -> accumulated to 8
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '100285', map_id: '40' }
  ])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=40');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 8);

  // 4.3. Empty response on one map: Map 9 returns empty -> clears only Map 9, keeping Map 2, 34, 36, 7, 37, 40
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([])))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=9');
  await tick();
  assert.equal(obsOutputs.at(-1).points.length, 7);
  assert(!obsOutputs.at(-1).points.some(p => p.map_id === '9'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '2'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '34'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '36'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '7'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '37'));
  assert(obsOutputs.at(-1).points.some(p => p.map_id === '40'));

  // 4.4. Session Termination (not-logged-in): wipes all accumulated maps completely
  obsPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload(null, -2004)))));
  await obsPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(obsOutputs.at(-1).state, 'not-logged-in');
  assert.equal(obsOutputs.at(-1).points.length, 0);

  // 4.5. Out of order responses for the SAME map
  const oooPage = env();
  let oooOutputs = [];
  oooPage.HexenHoYoLAB.observe(s => oooOutputs.push(s));

  // Request 1 sent (serial 1) - delayed
  let resolveReq1;
  const p1 = new Promise(r => resolveReq1 = r);
  oooPage.setFetchImpl(() => p1);
  const f1 = oooPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');

  // Request 2 sent (serial 2) - arrives fast with updated markers
  oooPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }, { point_id: '106903', map_id: '2' }
  ])))));
  await oooPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(oooOutputs.at(-1).points.length, 2);

  // Request 1 finally arrives late with old stale data (1 point)
  resolveReq1(new Response(JSON.stringify(makePayload([{ point_id: '106902', map_id: '2' }]))));
  await f1;
  await tick();
  // Must STILL be 2 points; stale serial 1 must NOT overwrite serial 2!
  assert.equal(oooOutputs.at(-1).points.length, 2);

  console.log('--- 5. Testing Session Epoch Lifecycle, Account Switching & Stale Response Rejection ---');
  // 5.1. Scenario 1 & 2: Logout while requests are pending + delayed response for another map arriving after logout
  const sessPage = env();
  let sessOutputs = [];
  const sessObserver = sessPage.HexenHoYoLAB.observe(s => sessOutputs.push(s));
  assert.equal(sessObserver.getEpoch(), 1);

  // In-flight request for Map 9 is sent during Session Epoch 1
  let resolvePendingMap9;
  const pMap9 = new Promise(r => resolvePendingMap9 = r);
  sessPage.setFetchImpl(() => pMap9);
  const fPendingMap9 = sessPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=9');

  // Now logout occurs (either via -2004 response or logout endpoint)
  sessPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload(null, -2004)))));
  await sessPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(sessOutputs.at(-1).state, 'not-logged-in');
  assert.equal(sessOutputs.at(-1).points.length, 0);
  assert(sessObserver.getEpoch() > 1);

  // The delayed Map 9 response finally arrives late with points from the pre-logout session
  resolvePendingMap9(new Response(JSON.stringify(makePayload([{ point_id: '25278', map_id: '9' }]))));
  await fPendingMap9;
  await tick();
  // Stale epoch response MUST be discarded! State must remain not-logged-in, points must remain 0!
  assert.equal(sessOutputs.at(-1).state, 'not-logged-in');
  assert.equal(sessOutputs.at(-1).points.length, 0);

  // 5.2. Scenario 3 & 4: Account A switching to Account B via auth response with new identity + delayed response from Account A
  const acctPage = env();
  acctPage.document = { cookie: 'account_id_v2=account_A_1111' };
  let acctOutputs = [];
  const acctObserver = acctPage.HexenHoYoLAB.observe(s => acctOutputs.push(s));

  // Account A loads Map 2 (2 points) and Map 9 (1 point)
  acctPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }, { point_id: '106903', map_id: '2' }
  ])))));
  await acctPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  acctPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '25278', map_id: '9' }
  ])))));
  await acctPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=9');
  await tick();
  assert.equal(acctOutputs.at(-1).points.length, 3);

  // Account A confirms its initial game role (establishing role identity baseline)
  acctPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({
    retcode: 0,
    message: 'OK',
    data: { list: [{ game_biz: 'hk4e_global', game_uid: 'account_A_0001', is_chosen: true }] }
  }))));
  await acctPage.fetch('https://api-os-takumi.hoyolab.com/binding/api/getUserGameRolesByCookie');
  await tick();
  assert.equal(acctOutputs.at(-1).points.length, 3);

  // Account A dispatches a slow request for Map 34
  let resolveAcctAMap34;
  const pAcctAMap34 = new Promise(r => resolveAcctAMap34 = r);
  acctPage.setFetchImpl(() => pAcctAMap34);
  const fAcctAMap34 = acctPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=34');

  // Direct switch to Account B: role switch response with different game_uid
  acctPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({
    retcode: 0,
    message: 'OK',
    data: { list: [{ game_biz: 'hk4e_global', game_uid: 'account_B_9999', is_chosen: true }] }
  }))));
  await acctPage.fetch('https://api-os-takumi.hoyolab.com/binding/api/getUserGameRolesByCookie');
  await tick();
  // Session epoch advanced, points cleared for new account
  assert.equal(acctOutputs.at(-1).points.length, 0);

  // Account B loads Map 2 (1 point)
  acctPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }
  ])))));
  await acctPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(acctOutputs.at(-1).points.length, 1);
  assert.equal(acctOutputs.at(-1).points[0].map_id, '2');

  // Stale Map 34 response from Account A arrives now
  resolveAcctAMap34(new Response(JSON.stringify(makePayload([{ point_id: '68620', map_id: '34' }]))));
  await fAcctAMap34;
  await tick();
  // Must NOT pollute Account B! Total points must remain 1 (only Map 2)
  assert.equal(acctOutputs.at(-1).points.length, 1);
  assert(!acctOutputs.at(-1).points.some(p => p.map_id === '34'));
  assert(!acctOutputs.at(-1).points.some(p => p.map_id === '9'));

  // 5.3. Scenario 3: Cookie change detection advances epoch even without explicit API call
  const cookiePage = env();
  let cookieOutputs = [];
  cookiePage.document = { cookie: 'account_id_v2=account_A_1111' };
  const cookieObserver = cookiePage.HexenHoYoLAB.observe(s => cookieOutputs.push(s));
  const epBefore = cookieObserver.getEpoch();

  cookiePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }
  ])))));
  await cookiePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(cookieOutputs.at(-1).points.length, 1);

  // Cookie changes in page to Account B
  cookiePage.document.cookie = 'account_id_v2=account_B_2222';
  // Next request detects the cookie difference and advances epoch
  cookiePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '84140', map_id: '36' }
  ])))));
  await cookiePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=36');
  await tick();
  assert(cookieObserver.getEpoch() > epBefore);
  // Account B only has Map 36; Map 2 from Account A was safely cleared!
  assert.equal(cookieOutputs.at(-1).points.length, 1);
  assert.equal(cookieOutputs.at(-1).points[0].map_id, '36');

  // 5.4. RECURRENT AUTH CHECKS WITHOUT ACCOUNT SWITCH DO NOT CLEAR PROGRESS
  const stablePage = env();
  let stableOutputs = [];
  stablePage.document = { cookie: 'account_id_v2=stable_user_1001' };
  const stableObserver = stablePage.HexenHoYoLAB.observe(s => stableOutputs.push(s));
  const stableEp = stableObserver.getEpoch();

  // 1. User loads Map 2 (2 points)
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }, { point_id: '106903', map_id: '2' }
  ])))));
  await stablePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(stableOutputs.at(-1).points.length, 2);

  // 2. Background periodic token verification arrives (/token/verify)
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({ retcode: 0, message: 'OK', data: {} }))));
  await stablePage.fetch('https://passport-api-v4.hoyolab.com/account/ma-passport/token/verifyLtoken');
  await tick();
  // Epoch must NOT change, points must NOT be cleared!
  assert.equal(stableObserver.getEpoch(), stableEp);
  assert.equal(stableOutputs.at(-1).points.length, 2);

  // 3. User navigates to Map 9 (Chasm): loads 1 point -> accumulated to 3
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '25278', map_id: '9' }
  ])))));
  await stablePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=9');
  await tick();
  assert.equal(stableOutputs.at(-1).points.length, 3);

  // 4. Background /getUserGameRoles arrives with the SAME user
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({
    retcode: 0,
    message: 'OK',
    data: { list: [{ game_biz: 'hk4e_global', game_uid: 'stable_user_1001', is_chosen: true }] }
  }))));
  await stablePage.fetch('https://api-os-takumi.hoyolab.com/binding/api/getUserGameRolesByCookie');
  await tick();
  // Epoch must NOT change, points must NOT be cleared!
  assert.equal(stableObserver.getEpoch(), stableEp);
  assert.equal(stableOutputs.at(-1).points.length, 3);

  // 5. User navigates to Map 34 (Sea of Bygone Eras): loads 1 point -> accumulated to 4
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '68620', map_id: '34' }
  ])))));
  await stablePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=34');
  await tick();
  assert.equal(stableOutputs.at(-1).points.length, 4);

  // 6. Background /getCookieAccountInfo arrives with the SAME account
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({
    retcode: 0,
    message: 'OK',
    data: { account_id: 'stable_user_1001' }
  }))));
  await stablePage.fetch('https://api-os-takumi.hoyolab.com/auth/api/getCookieAccountInfoByLtoken');
  await tick();
  assert.equal(stableObserver.getEpoch(), stableEp);
  assert.equal(stableOutputs.at(-1).points.length, 4);

  // 7. User navigates to Map 36 (Ancient Sacred Mountain): loads 1 point -> accumulated to 5
  stablePage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '84140', map_id: '36' }
  ])))));
  await stablePage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=36');
  await tick();
  assert.equal(stableOutputs.at(-1).points.length, 5);

  // All 4 maps (2, 9, 34, 36) remain accumulated and intact!
  assert(stableOutputs.at(-1).points.some(p => p.map_id === '2'));
  assert(stableOutputs.at(-1).points.some(p => p.map_id === '9'));
  assert(stableOutputs.at(-1).points.some(p => p.map_id === '34'));
  assert(stableOutputs.at(-1).points.some(p => p.map_id === '36'));

  // 5.5. HttpOnly scenario: document.cookie is null, but auth API delivers identity
  const httpOnlyPage = env();
  let hoOutputs = [];
  httpOnlyPage.document = {}; // no cookie access
  const hoObserver = httpOnlyPage.HexenHoYoLAB.observe(s => hoOutputs.push(s));
  const hoEp = hoObserver.getEpoch();

  // Load Map 2 with account A
  httpOnlyPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify(makePayload([
    { point_id: '106902', map_id: '2' }
  ])))));
  await httpOnlyPage.fetch('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list?map_id=2');
  await tick();
  assert.equal(hoOutputs.at(-1).points.length, 1);

  // Routine token check arrives with no identity payload: must NOT advance epoch
  httpOnlyPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({ retcode: 0, message: 'OK' }))));
  await httpOnlyPage.fetch('https://passport-api-v4.hoyolab.com/account/ma-passport/token/verifyLtoken');
  await tick();
  assert.equal(hoObserver.getEpoch(), hoEp);
  assert.equal(hoOutputs.at(-1).points.length, 1);

  // Explicit logout arrives: advances epoch and sets not-logged-in
  httpOnlyPage.setFetchImpl(() => Promise.resolve(new Response(JSON.stringify({ retcode: 0, message: 'OK' }))));
  await httpOnlyPage.fetch('https://passport-api-v4.hoyolab.com/account/ma-passport/api/webLogout');
  await tick();
  assert(hoObserver.getEpoch() > hoEp);
  assert.equal(hoOutputs.at(-1).state, 'not-logged-in');
  assert.equal(hoOutputs.at(-1).points.length, 0);

  console.log('All HoYoLAB core, capture, bridge and security contract tests passed successfully!');
})().catch(e => {
  console.error(e);
  process.exitCode = 1;
});
