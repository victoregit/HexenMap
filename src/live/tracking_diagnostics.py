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
