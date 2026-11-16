/* Shared dependency-free HoYoLAB validation, map reads, observer, and ID resolution. */
(() => {
  'use strict';
  const MAX_BYTES = 16 * 1024 * 1024, MAX_POINTS = 300000;
  const SUPPORTED_MAPS = Object.freeze(['2', '7', '9', '34', '36', '37', '40']);
  const bytes = text => new TextEncoder().encode(text).byteLength;

  const allowedHosts = [
    'sg-public-api.hoyolab.com',
    'api-os-takumi.hoyolab.com',
    'api-os-takumi.mihoyo.com',
    'act.hoyolab.com',
    'passport-api-v4.hoyolab.com',
    'passport-api.hoyolab.com',
    'bbs-api-os.hoyolab.com'
  ];

  function isMarkerEndpoint(urlStr) {
    try {
      const p = new URL(urlStr, location.href).pathname;
      return p.includes('/mark_map_point_list') ||
             p.includes('/point/mark_map_point_list') ||
             p.includes('/point/user_mark_point_list') ||
             p.includes('/point/mark_point_list') ||
             (p.includes('/point/') && p.includes('mark'));
    } catch {
      return false;
    }
  }

  function isSessionBoundaryEndpoint(urlStr) {
    try {
      const p = new URL(urlStr, location.href).pathname;
      return p.includes('/logout') ||
             p.includes('webLogout') ||
             p.includes('/login') ||
             p.includes('/token/verify') ||
             p.includes('/verifyLtoken') ||
             p.includes('/verifyCookieToken') ||
             p.includes('/getUserGameRoles') ||
             p.includes('/changeGameRole') ||
             p.includes('/change_role') ||
             p.includes('/getCookieAccountInfo') ||
             p.includes('/getAccountInfo');
    } catch {
      return false;
    }
  }

  function target(value) {
    try {
      const u = new URL(value, location.href);
      if (!allowedHosts.includes(u.hostname)) return false;
      return isMarkerEndpoint(value) || isSessionBoundaryEndpoint(value);
    } catch {
      return false;
    }
  }

  function isListEndpoint(urlStr) {
    try {
      const p = new URL(urlStr, location.href).pathname;
      return p.includes('mark_map_point_list') ||
             p.includes('user_mark_point_list') ||
             p.includes('point_list');
    } catch {
      return false;
    }
  }

  function parseMutation(reqBody, reqUrl) {
    try {
      let bodyObj = null;
      if (typeof reqBody === 'string') {
        try { bodyObj = JSON.parse(reqBody); } catch {}
      } else if (reqBody && typeof reqBody === 'object') {
        bodyObj = reqBody;
      }
      const u = new URL(reqUrl, location.href);
      const mapId = String(bodyObj?.map_id ?? u.searchParams.get('map_id') ?? '2');
      const pointId = String(bodyObj?.point_id ?? bodyObj?.id ?? u.searchParams.get('point_id') ?? '');
      const status = bodyObj?.mark_status ?? bodyObj?.status ?? u.searchParams.get('status');
      const isUnmark = status === 0 || status === '0' || u.pathname.includes('unmark');
      if (pointId && /^[0-9]{1,32}$/.test(pointId)) {
        return { mapId, pointId, isUnmark };
      }
    } catch {}
    return null;
  }

  function parseMapIdFromUrl(value) {
    try {
      const u = new URL(value, location.href);
      const mid = u.searchParams.get('map_id');
      if (mid && /^[0-9]{1,16}$/.test(mid)) return String(mid);

      const hash = u.hash || (typeof location !== 'undefined' ? location.hash : '');
      const hashMatch = hash && hash.match(/#\/map\/([0-9]{1,16})/);
      if (hashMatch) return hashMatch[1];
    } catch {}
    return '2'; // Default Teyvat
  }

  function extract(payload, defaultMapId = '2') {
    if (!payload || typeof payload !== 'object') throw Error('Resposta HoYoLAB inválida.');
    if (bytes(JSON.stringify(payload)) > MAX_BYTES) throw Error('Resposta acima de 16 MiB.');

    if (payload.retcode === -2004 || payload.retcode === -100) {
      return { state: 'not-logged-in', points: [] };
    }
    if (typeof payload.retcode === 'number' && payload.retcode !== 0) {
      return { state: 'error', points: [] };
    }

    const data = payload.data;
    if (!data) {
      return { state: 'not-found', points: [] };
    }

    let rawList = null;
    if (Array.isArray(data)) {
      rawList = data;
    } else if (typeof data === 'object') {
      rawList = data.point_list ?? data.list ?? data.points ?? data.point_ids ??
                data.point_id_list ?? data.mark_list ?? data.point_status_list ??
                data.marked_points ?? data.marks;
      if (!Array.isArray(rawList)) {
        const numericKeys = Object.keys(data).filter(k => /^[0-9]{1,32}$/.test(k));
        if (numericKeys.length > 0) {
          rawList = numericKeys;
        }
      }
    }

    if (!Array.isArray(rawList)) {
      return { state: 'not-found', points: [] };
    }
    if (rawList.length > MAX_POINTS) throw Error('Lista de pontos acima do limite de 300.000.');

    const normalizedPoints = [];
    const seenCompound = new Set();

    for (const item of rawList) {
      let pointId = '';
      let mapId = defaultMapId;

      if (typeof item === 'object' && item !== null) {
        pointId = String(item.point_id ?? item.id ?? item.pointId ?? item.mark_id ?? item.point_sn ?? '');
        if (item.map_id !== undefined && item.map_id !== null) {
          mapId = String(item.map_id);
        } else if (item.mapId !== undefined && item.mapId !== null) {
          mapId = String(item.mapId);
        }
      } else if (typeof item === 'number' || typeof item === 'string') {
        pointId = String(item);
      }

      if (!/^[0-9]{1,32}$/.test(pointId) || !/^[0-9]{1,16}$/.test(mapId)) {
        continue;
      }

      const compound = `${mapId}:${pointId}`;
      if (!seenCompound.has(compound)) {
        seenCompound.add(compound);
        normalizedPoints.push({ map_id: mapId, point_id: pointId });
      }
    }

    return {
      state: 'detected',
      points: normalizedPoints,
      at: Date.now()
    };
  }

  function resolve(points, indexData) {
    if (!Array.isArray(points)) throw Error('Lista de pontos inválida.');
    const mapping = indexData?.mapping ?? indexData ?? {};

    const matchedIds = new Set();
    const unmatchedPoints = [];
    const ambiguousPoints = [];
    const unsupportedMapPoints = [];

    const supportedMaps = new Set(SUPPORTED_MAPS);

    for (const pt of points) {
      const mapId = String(pt.map_id ?? '2');
      const pointId = String(pt.point_id ?? pt.id ?? '');
      if (!pointId) continue;

      const compoundKey = `${mapId}:${pointId}`;

      if (!supportedMaps.has(mapId)) {
        unsupportedMapPoints.push(compoundKey);
        continue;
      }

      const targetAsId = mapping[compoundKey];

      if (targetAsId === 'ambiguous') {
        ambiguousPoints.push(compoundKey);
      } else if (typeof targetAsId === 'string' && /^[0-9]{1,32}$/.test(targetAsId)) {
        matchedIds.add(targetAsId);
      } else {
        unmatchedPoints.push(compoundKey);
      }
    }

    // Sort decimal IDs numerically for consistency
    const sortedMarkerIds = [...matchedIds].sort((a, b) => (BigInt(a) < BigInt(b) ? -1 : 1));

    return {
      total_found: points.length,
      matched_safe: sortedMarkerIds.length,
      ambiguous: ambiguousPoints.length,
      unmatched: unmatchedPoints.length,
      unsupported_map: unsupportedMapPoints.length,
      markerIds: sortedMarkerIds,
      unmatched_points: unmatchedPoints,
      ambiguous_points: ambiguousPoints,
      unsupported_map_points: unsupportedMapPoints
    };
  }

  async function read(response, progress = () => {}) {
    const copy = response.clone();
    if (!copy.body?.getReader) {
      const text = await copy.text();
      if (bytes(text) > MAX_BYTES) throw Error('Tamanho acima do limite.');
      progress('validating');
      return JSON.parse(text);
    }
    const reader = copy.body.getReader(), chunks = [];
    let size = 0;
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_BYTES) {
          void reader.cancel().catch(() => {});
          throw Error('Tamanho acima do limite.');
        }
        chunks.push(value);
      }
    } finally {
      reader.releaseLock();
    }
    const data = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      data.set(chunk, offset);
      offset += chunk.byteLength;
    }
    progress('validating');
    return JSON.parse(new TextDecoder().decode(data));
  }

  function extractIdentitiesFromPayload(payload) {
    if (!payload || typeof payload !== 'object') return { passportId: null, gameUid: null };
    let passportId = null, gameUid = null;
    try {
      const data = payload.data;
      if (data && typeof data === 'object') {
        const directId = data.account_id ?? data.uid ?? data.account_uid ?? data.user_id;
        if (directId !== undefined && directId !== null && String(directId).trim()) {
          passportId = String(directId).trim();
        }
        const list = data.list ?? data.game_roles;
        if (Array.isArray(list) && list.length > 0) {
          const chosen = list.find(r => r.is_chosen);
          if (chosen?.game_uid) {
            gameUid = String(chosen.game_uid).trim();
          } else {
            const uids = list.map(r => String(r.game_uid ?? r.uid ?? '')).filter(Boolean).sort();
            if (uids.length > 0) gameUid = uids.join(',');
          }
        }
      }
    } catch {}
    return { passportId, gameUid };
  }

  function readCookieAccountId() {
    try {
      if (typeof document !== 'undefined' && typeof document.cookie === 'string') {
        const match = document.cookie.match(/(?:^|;\s*)(?:account_id_v2|ltuid_v2|account_id|ltuid)=([^;]+)/);
        if (match && match[1]) return match[1].trim();
      }
    } catch {}
    return null;
  }

  function observe(emit, progress = () => {}) {
    const originalFetch = window.fetch;
    const proto = XMLHttpRequest.prototype;
    const originalOpen = proto.open;
    const pending = new Map();
    let stopped = false, sequence = 0;
    let sessionEpoch = 1;
    let activePassportId = readCookieAccountId();
    let activeGameUid = null;
    const acceptedByMap = new Map();
    let currentPoints = [];
    let hasFullList = false;
    let refreshPromise = null;
    let mutationRevision = 0;
    let refreshController = null;

    function refreshAll() {
      if (refreshPromise) return refreshPromise;
      checkCookieIdentity();
      const epoch = sessionEpoch;
      const initialMutation = mutationRevision;
      refreshPromise = (async () => {
        let points = [];
        const completed = [];
        try {
          for (const mapId of SUPPORTED_MAPS) {
            if (stopped || epoch !== sessionEpoch) throw Error('context-changed');
            progress('request');
            const serial = ++sequence;
            // Discard older passive responses for this map, including empty lists.
            acceptedByMap.set(mapId, serial);
            const controller = new AbortController();
            refreshController = controller;
            const timeout = setTimeout(() => controller.abort(), 15000);
            let snapshot;
            try {
              const url = new URL('https://sg-public-api.hoyolab.com/common/map_user/ys_obc/v1/map/point/mark_map_point_list');
              url.search = new URLSearchParams({ map_id: mapId, app_sn: 'ys_obc', lang: 'en-us' });
              const response = await originalFetch.call(window, url.href, {
                credentials: 'include', signal: controller.signal, cache: 'no-store'
              });
              if (!response.ok) throw Error('map-read-failed');
              const payload = await read(response, progress);
              if (payload?.data?.has_more || payload?.data?.hasMore || payload?.data?.next_cursor) {
                throw Error('incomplete-map-list');
              }
              snapshot = extract(payload, mapId);
            } finally {
              clearTimeout(timeout);
              if (refreshController === controller) refreshController = null;
            }
            checkCookieIdentity();
            if (stopped || epoch !== sessionEpoch || mutationRevision !== initialMutation) throw Error('context-changed');
            if (snapshot.state === 'not-logged-in') {
              advanceEpoch('not-logged-in');
              activePassportId = null;
              activeGameUid = null;
              emit(snapshot);
              return { state: 'not-logged-in', points: [] };
            }
            // Missing/malformed data is not an empty map and must not erase progress.
            if (snapshot.state !== 'detected' || snapshot.points.some(p => p.map_id !== mapId)) {
              throw Error('map-read-failed');
            }
            points = points.concat(snapshot.points);
            if (points.length > MAX_POINTS) throw Error('too-many-points');
            completed.push(mapId);
          }
          if (stopped || epoch !== sessionEpoch) throw Error('context-changed');
          currentPoints = points;
          hasFullList = true;
          const snapshot = {
            state: points.length ? 'detected' : 'not-found', points: [...points], at: Date.now(),
            coverage: { complete: true, maps: [...completed], total: SUPPORTED_MAPS.length }
          };
          emit(snapshot);
          return snapshot;
        } catch (error) {
          if (!stopped && epoch === sessionEpoch) {
            emit({ state: 'error', points: [], at: Date.now(),
              coverage: { complete: false, maps: completed, total: SUPPORTED_MAPS.length } });
          }
          throw error;
        }
      })().finally(() => { refreshPromise = null; });
      return refreshPromise;
    }

    function advanceEpoch(reason = 'unknown') {
      refreshController?.abort();
      sessionEpoch++;
      currentPoints = [];
      hasFullList = false;
      acceptedByMap.clear();
    }

    function checkPassportChange(newPassportId) {
      if (!newPassportId) return;
      if (!activePassportId) {
        activePassportId = newPassportId;
        return;
      }
      if (newPassportId !== activePassportId) {
        activePassportId = newPassportId;
        activeGameUid = null;
        advanceEpoch('passport-account-changed');
        emit({ state: 'waiting', points: [] });
      }
    }

    function checkGameUidChange(newGameUid) {
      if (!newGameUid) return;
      if (!activeGameUid) {
        activeGameUid = newGameUid;
        return;
      }
      if (newGameUid !== activeGameUid) {
        activeGameUid = newGameUid;
        advanceEpoch('game-uid-changed');
        emit({ state: 'waiting', points: [] });
      }
    }

    function checkCookieIdentity() {
      const cookieId = readCookieAccountId();
      if (cookieId) {
        checkPassportChange(cookieId);
      }
    }

    function handleSessionBoundary(urlStr, payload) {
      const isLogout = urlStr.includes('logout') || urlStr.includes('webLogout');
      if (isLogout) {
        advanceEpoch('logout');
        activePassportId = null;
        activeGameUid = null;
        emit({ state: 'not-logged-in', points: [] });
        return;
      }

      if (payload && (payload.retcode === -2004 || payload.retcode === -100)) {
        advanceEpoch('not-logged-in');
        activePassportId = null;
        activeGameUid = null;
        emit({ state: 'not-logged-in', points: [] });
        return;
      }

      const { passportId, gameUid } = extractIdentitiesFromPayload(payload);
      if (passportId) {
        checkPassportChange(passportId);
      }
      if (gameUid) {
        checkGameUidChange(gameUid);
      }
      checkCookieIdentity();
    }

    function failure(serial, mapId = '2', reqEpoch = 1) {
      if (stopped || reqEpoch !== sessionEpoch) return;
      const last = acceptedByMap.get(mapId) || 0;
      if (serial >= last) emit({ state: 'error' });
    }

    function deliver(payload, url, serial, reqBody = null, reqEpoch = 1) {
      if (stopped) return;
      if (reqEpoch !== sessionEpoch) {
        // Discard stale response originating from a previous session epoch/generation
        return;
      }
      try {
        const defaultMapId = parseMapIdFromUrl(url);
        const lastAccepted = acceptedByMap.get(defaultMapId) || 0;
        if (serial < lastAccepted) return;

        const listEndpoint = isListEndpoint(url);

        // Check if this was an active mutation (mark/unmark)
        const mutation = parseMutation(reqBody, url);
        if (mutation && payload?.retcode === 0) {
          mutationRevision++;
          acceptedByMap.set(defaultMapId, serial);
          const { mapId, pointId, isUnmark } = mutation;
          if (isUnmark) {
            currentPoints = currentPoints.filter(p => !(p.map_id === mapId && p.point_id === pointId));
          } else {
            if (!currentPoints.some(p => p.map_id === mapId && p.point_id === pointId)) {
              currentPoints.push({ map_id: mapId, point_id: pointId });
            }
          }
          emit({
            state: currentPoints.length > 0 ? 'detected' : 'not-found',
            points: [...currentPoints],
            at: Date.now()
          });
          return;
        }

        const snapshot = extract(payload, defaultMapId);
        // If not a list endpoint and no points extracted, ignore rather than wiping out
        if (!listEndpoint && snapshot.state === 'not-found' && hasFullList) {
          return;
        }

        acceptedByMap.set(defaultMapId, serial);

        if (snapshot.state === 'not-logged-in') {
          // Authentication error / logout immediately invalidates session epoch and points
          advanceEpoch('not-logged-in');
          activePassportId = null;
          activeGameUid = null;
          emit(snapshot);
          return;
        }

        if (snapshot.state === 'detected') {
          hasFullList = true;
          const incomingMapIds = new Set(snapshot.points.map(p => p.map_id));
          if (incomingMapIds.size === 0 && defaultMapId) {
            incomingMapIds.add(defaultMapId);
          }
          currentPoints = currentPoints.filter(p => !incomingMapIds.has(p.map_id)).concat(snapshot.points);
          if (currentPoints.length > MAX_POINTS) {
            currentPoints = currentPoints.slice(0, MAX_POINTS);
          }
          emit({
            state: currentPoints.length > 0 ? 'detected' : 'not-found',
            points: [...currentPoints],
            at: Date.now()
          });
        } else if (snapshot.state === 'not-found') {
          hasFullList = true;
          currentPoints = currentPoints.filter(p => p.map_id !== defaultMapId);
          emit({
            state: currentPoints.length > 0 ? 'detected' : 'not-found',
            points: [...currentPoints],
            at: Date.now()
          });
        } else {
          emit(snapshot);
        }
      } catch {
        failure(serial, parseMapIdFromUrl(url), reqEpoch);
      }
    }

    function wrappedFetch(...args) {
      const promise = originalFetch.apply(this, args);
      const input = args[0];
      const init = args[1];
      const urlStr = typeof input === 'string' || input instanceof URL ? String(input) : input?.url;
      const reqBody = init?.body ?? null;

      if (urlStr && target(urlStr)) {
        checkCookieIdentity();
        const reqEpoch = sessionEpoch;
        const serial = ++sequence;

        if (isSessionBoundaryEndpoint(urlStr)) {
          void promise.then(response => {
            if (stopped) return;
            if (urlStr.includes('logout') || urlStr.includes('webLogout')) {
              handleSessionBoundary(urlStr, null);
              return;
            }
            if (response.ok) {
              void read(response, progress).then(
                p => handleSessionBoundary(urlStr, p),
                () => checkCookieIdentity()
              );
            }
          }).catch(() => {});
          return promise;
        }

        progress('request');
        void promise.then(response => {
          if (stopped) return;
          if (!response.ok) { failure(serial, parseMapIdFromUrl(urlStr), reqEpoch); return; }
          progress('receiving');
          void read(response, progress).then(
            p => deliver(p, urlStr, serial, reqBody, reqEpoch),
            () => failure(serial, parseMapIdFromUrl(urlStr), reqEpoch)
          );
        }, () => failure(serial, parseMapIdFromUrl(urlStr), reqEpoch)).catch(() => {});
      }
      return promise;
    }

    function wrappedOpen(method, url, ...rest) {
      pending.get(this)?.();
      const result = originalOpen.call(this, method, url, ...rest);
      const urlStr = String(url);
      let capturedBody = null;
      const originalSend = this.send;
      this.send = function(body) {
        capturedBody = body;
        return originalSend.apply(this, arguments);
      };

      if (!stopped && target(urlStr)) {
        const xhr = this;
        checkCookieIdentity();
        const reqEpoch = sessionEpoch;
        const cleanup = () => {
          for (const e of ['load', 'error', 'abort', 'timeout', 'loadend']) {
            xhr.removeEventListener(e, listener);
          }
          pending.delete(xhr);
        };
        const listener = event => {
          cleanup();
          if (stopped) return;
          const serial = ++sequence;

          if (isSessionBoundaryEndpoint(urlStr)) {
            if (urlStr.includes('logout') || urlStr.includes('webLogout')) {
              handleSessionBoundary(urlStr, null);
              return;
            }
            if (xhr.status === 200) {
              let parsed = null;
              try {
                parsed = xhr.responseType === 'json' ? xhr.response : JSON.parse(xhr.responseText);
              } catch {}
              handleSessionBoundary(urlStr, parsed);
            }
            return;
          }

          if (event?.type && event.type !== 'load') {
            if (event.type !== 'loadend') failure(serial, parseMapIdFromUrl(urlStr), reqEpoch);
            return;
          }
          let status, type, payload;
          try {
            status = xhr.status;
            type = xhr.responseType;
            payload = type === 'json' ? xhr.response : xhr.responseText;
          } catch {
            failure(serial, parseMapIdFromUrl(urlStr), reqEpoch);
            return;
          }
          progress('receiving');
          Promise.resolve().then(() => {
            if (status !== 200) { failure(serial, parseMapIdFromUrl(urlStr), reqEpoch); return; }
            progress('validating');
            try {
              if (type === 'json') deliver(payload, urlStr, serial, capturedBody, reqEpoch);
              else if (!type || type === 'text') {
                if (bytes(payload) > MAX_BYTES) throw Error();
                deliver(JSON.parse(payload), urlStr, serial, capturedBody, reqEpoch);
              }
            } catch {
              failure(serial, parseMapIdFromUrl(urlStr), reqEpoch);
            }
          });
        };
        pending.set(xhr, cleanup);
        for (const e of ['load', 'error', 'abort', 'timeout', 'loadend']) {
          xhr.addEventListener(e, listener);
        }
      }
      return result;
    }

    window.fetch = wrappedFetch;
    proto.open = wrappedOpen;

    const unhook = () => {
      stopped = true;
      refreshController?.abort();
      if (window.fetch === wrappedFetch) window.fetch = originalFetch;
      if (proto.open === wrappedOpen) proto.open = originalOpen;
      for (const cleanup of [...pending.values()]) cleanup();
    };
    unhook.advanceEpoch = advanceEpoch;
    unhook.getEpoch = () => sessionEpoch;
    unhook.refreshAll = refreshAll;
    return unhook;
  }

  globalThis.HexenHoYoLAB = Object.freeze({
    MAX_BYTES,
    MAX_POINTS,
    SUPPORTED_MAPS,
    target,
    isMarkerEndpoint,
    isSessionBoundaryEndpoint,
    extractIdentitiesFromPayload,
    readCookieAccountId,
    parseMapIdFromUrl,
    isListEndpoint,
    parseMutation,
    extract,
    resolve,
    read,
    observe,
    bytes
  });
})();
