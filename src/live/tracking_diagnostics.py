"""Explicit, bounded local minimap recordings; never changes game progress."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import threading
import time
import zipfile

import cv2


class MinimapRecording:
    duration = 20.
    max_bytes = 50 * 1024 * 1024
    interval = .05

    def __init__(self, root: Path, metadata: dict, *, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.directory = root / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        self.directory.mkdir(parents=True)
        self.metadata = dict(metadata, schema=1, duration_limit_s=self.duration,
                             byte_limit=self.max_bytes, uploaded=False)
        self.queue = queue.Queue(maxsize=8)
        self.stopping = threading.Event()
        self.done = threading.Event()
        self.dropped = 0
        self.last_frame = -float('inf')
        self.error = ''
        self.thread = threading.Thread(target=self._write, name='MinimapDiagnostic', daemon=True)
        self.thread.start()

    def record(self, frame, stamp, details):
        if self.stopping.is_set():
            return
        if self.clock() - self.started >= self.duration:
            self.stop()
            return
        if stamp - self.last_frame < self.interval:
            return
        self.last_frame = stamp
        # Only the minimap corner; preserve the actual captured geometry for replay.
        crop = None
        if frame is not None:
            h, w = frame.shape[:2]
            crop = frame[:max(1, round(h * .35)), :max(1, round(w * .30))].copy()
            details = dict(details, captured_shape=list(frame.shape), crop_origin=[0, 0])
        try:
            self.queue.put_nowait((stamp - self.started, crop, details))
        except queue.Full:
            self.dropped += 1

    def stop(self):
        self.stopping.set()

    def close(self):
        self.stop()
        self.thread.join(timeout=3)

    def _write(self):
        count = size = 0
        reason = 'stopped'
        try:
            with (self.directory / 'frames.jsonl').open('w', encoding='utf-8') as log:
                while True:
                    if self.clock() - self.started >= self.duration:
                        reason = 'duration_limit'
                        self.stop()
                    try:
                        elapsed, crop, details = self.queue.get(timeout=.1)
                    except queue.Empty:
                        if self.stopping.is_set():
                            break
                        continue
                    data = b''
                    filename = None
                    if crop is not None:
                        ok, encoded = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
                        if not ok:
                            raise OSError('JPEG encoding failed')
                        data = encoded.tobytes()
                        filename = f'{count:04d}.jpg'
                    row = json.dumps(dict(details, elapsed_s=elapsed, image=filename), allow_nan=False) + '\n'
                    row_size = len(row.encode('utf-8')) + len(data)
                    if size + row_size > self.max_bytes - 16384:
                        reason = 'space_limit'
                        self.stop()
                        break
                    if filename:
                        (self.directory / filename).write_bytes(data)
                    log.write(row)
                    size += row_size
                    count += 1
        except (OSError, ValueError, TypeError, cv2.error) as exc:
            self.error = str(exc)
            reason = 'write_error'
        finally:
            self.stop()
            self.metadata.update(frames=count, bytes=size, dropped_frames=self.dropped,
                                 stop_reason=reason, error=self.error)
            try:
                temporary = self.directory / 'manifest.json.tmp'
                temporary.write_text(json.dumps(self.metadata, indent=2), encoding='utf-8')
                temporary.replace(self.directory / 'manifest.json')
            except OSError as exc:
                self.error = str(exc)
            self.done.set()

    def export(self, destination: Path):
        if not self.done.is_set():
            raise ValueError('Recording is still running')
        destination = Path(destination)
        # Never include progress, credentials or unrelated installation files.
        temporary = destination.with_name(destination.name + '.tmp')
        try:
            with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in self.directory.iterdir():
                    if path.name in ('manifest.json', 'frames.jsonl') or path.suffix == '.jpg':
                        archive.write(path, path.name)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


# Mandatory Failure Classification Codes (Stage 4 Diagnostic Specification)
REFERENCE_MISSING = 'REFERENCE_MISSING'
REFERENCE_LOAD_FAILED = 'REFERENCE_LOAD_FAILED'
MAP_CLASSIFICATION_FAILED = 'MAP_CLASSIFICATION_FAILED'
LAYER_CLASSIFICATION_FAILED = 'LAYER_CLASSIFICATION_FAILED'
LOW_MATCH_CONFIDENCE = 'LOW_MATCH_CONFIDENCE'
TRANSFORM_FAILED = 'TRANSFORM_FAILED'
COORDINATE_SPACE_MISMATCH = 'COORDINATE_SPACE_MISMATCH'
MARKER_DATA_MISSING = 'MARKER_DATA_MISSING'
RENDER_FILTERED = 'RENDER_FILTERED'
STALE_TRACKING_STATE = 'STALE_TRACKING_STATE'

FAILURE_CODES = frozenset({
    REFERENCE_MISSING,
    REFERENCE_LOAD_FAILED,
    MAP_CLASSIFICATION_FAILED,
    LAYER_CLASSIFICATION_FAILED,
    LOW_MATCH_CONFIDENCE,
    TRANSFORM_FAILED,
    COORDINATE_SPACE_MISMATCH,
    MARKER_DATA_MISSING,
    RENDER_FILTERED,
    STALE_TRACKING_STATE,
})


class RecognitionStageDiagnostic:
    """Per-stage recognition attempt diagnostic record."""

    def __init__(self, *,
                 timestamp: float = 0.0,
                 previous_scope: tuple[str, str] | None = None,
                 candidate_map: str | None = None,
                 candidate_layer: str | None = None,
                 selected_reference: str | None = None,
                 visual_matches: int = 0,
                 confidence: float = 0.0,
                 geometric_validation: bool = False,
                 transform_state: str = 'UNAVAILABLE',
                 eligible_markers: int = 0,
                 drawn_markers: int = 0,
                 failure_reason: str | None = None,
                 elapsed_ms: float = 0.0):
        self.timestamp = timestamp
        self.previous_scope = tuple(previous_scope) if previous_scope is not None else None
        self.candidate_map = candidate_map
        self.candidate_layer = candidate_layer
        self.selected_reference = selected_reference
        self.visual_matches = visual_matches
        self.confidence = confidence
        self.geometric_validation = geometric_validation
        self.transform_state = transform_state
        self.eligible_markers = eligible_markers
        self.drawn_markers = drawn_markers
        self.failure_reason = failure_reason
        self.elapsed_ms = elapsed_ms

    def to_dict(self) -> dict:
        return {
            'timestamp': round(self.timestamp, 3),
            'previous_scope': list(self.previous_scope) if self.previous_scope else None,
            'candidate_map': self.candidate_map,
            'candidate_layer': self.candidate_layer,
            'selected_reference': self.selected_reference,
            'visual_matches': self.visual_matches,
            'confidence': round(self.confidence, 3),
            'geometric_validation': self.geometric_validation,
            'transform_state': self.transform_state,
            'eligible_markers': self.eligible_markers,
            'drawn_markers': self.drawn_markers,
            'failure_reason': self.failure_reason,
            'elapsed_ms': round(self.elapsed_ms, 2),
        }

    def format_log(self) -> str:
        lines = [
            'Map Recognition',
            f'Timestamp: {self.timestamp:.3f}',
            f'Previous: {self.previous_scope[0] if self.previous_scope else "NONE"}/{self.previous_scope[1] if self.previous_scope else "NONE"}',
            f'Candidate Map: {self.candidate_map or "NONE"}',
            f'Candidate Layer: {self.candidate_layer or "NONE"}',
            f'Reference: {self.selected_reference or "NONE"}',
            f'Visual Matches: {self.visual_matches}',
            f'Confidence: {self.confidence:.2f}',
            f'Geometric Validation: {"OK" if self.geometric_validation else "FAILED"}',
            f'Transform: {self.transform_state}',
            f'Markers: {self.drawn_markers}/{self.eligible_markers}',
            f'Reason: {self.failure_reason or "SUCCESS"}',
            f'Elapsed: {self.elapsed_ms:.1f}ms',
        ]
        return '\n'.join(lines)


def classify_scope_support(map_id: str, layer_id: str | None, reference_store=None) -> tuple[bool, str | None, str]:
    """Audit whether a scope is supported or has missing reference packages.

    Explicitly identifies Teyvat (as-map-2) underground layers as REFERENCE_MISSING.
    """
    if map_id == 'as-map-2' and layer_id not in (None, 'surface'):
        return False, REFERENCE_MISSING, 'Camadas subterrâneas de Teyvat não possuem pacotes de referência instalados'

    if reference_store is not None:
        try:
            scope = (map_id, layer_id or 'surface')
            if scope not in reference_store.scopes:
                return False, REFERENCE_MISSING, f'Escopo {scope} não encontrado no repositório de referências'
        except Exception as exc:
            return False, REFERENCE_LOAD_FAILED, str(exc)

    return True, None, 'OK'


class RecognitionDiagnosticsLog:
    """Bounded thread-safe ring buffer of recent recognition attempts."""

    def __init__(self, maxlen: int = 50):
        self.maxlen = maxlen
        self._entries: list[RecognitionStageDiagnostic] = []
        self._lock = threading.Lock()

    def record(self, diag: RecognitionStageDiagnostic):
        with self._lock:
            self._entries.append(diag)
            if len(self._entries) > self.maxlen:
                self._entries.pop(0)

    def latest(self) -> RecognitionStageDiagnostic | None:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [e.to_dict() for e in self._entries]

