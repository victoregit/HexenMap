"""On-demand public AppSample comments; no account access or progress writes."""
from concurrent.futures import Future
from dataclasses import dataclass
from html.parser import HTMLParser
from html import escape
import json
import re
import threading
import time
import hashlib
import io
import os
import tempfile
from PIL import Image, ImageOps
from urllib.parse import urlencode
from urllib.request import urlopen

from src.live.storage import write_json

MAX_BYTES = 512 * 1024
TTL = 7 * 86400


def identity(item):
    match = re.fullmatch(r'appsample:marker:([0-9]{1,12})', item.id)
    kind = {'common-chest':'o17', 'exquisite-chest':'o44', 'precious-chest':'o45',
            'luxurious-chest':'o46', 'remarkable-chest':'o269'}.get(item.category)
    if kind is None and re.fullmatch(r'as-o[0-9]{1,6}', item.category):
        kind = item.category[3:]
    map_match = re.fullmatch(r'as-map-([0-9]{1,3})', item.map_id)
    if not match or not kind or not map_match:
        return None
    return kind, match[1], map_match[1]


def marker_url(item):
    key = identity(item)
    if key is None:
        return None
    kind, identifier, map_id = key
    return 'https://genshin-impact-map.appsample.com/?' + urlencode(
        {'id':identifier, 'mid':map_id, 'type':kind})


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('br', 'p', 'div', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value, limit=4000):
    parser = PlainText()
    parser.feed(value[:16000] if isinstance(value, str) else '')
    return ''.join(parser.parts).strip()[:limit]


def parse_comments(payload):
    data = payload.get('data') if isinstance(payload, dict) else None
    rows = data.get('comments') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError('Formato de comentários não reconhecido')
    comments = []
    for row in rows[:50]:
        if not isinstance(row, dict):
            continue
        translations = row.get('trans')
        translated = translations.get('pt') if isinstance(translations, dict) else None
        text = plain(translated or row.get('content'))
        image = row.get('image', '')
        image = ('https://game-cdn.appsample.com' + image
                 if isinstance(image, str) and re.fullmatch(r'/gim/comments/[A-Za-z0-9_./-]+', image) else '')
        votes = row.get('vote', 0)
        if text or image:
            comments.append({'text':text, 'author':plain(row.get('aname'), 80),
                             'votes':votes if type(votes) is int else 0,
                             'translated':bool(translated), 'image':image})
    return sorted(comments, key=lambda row:row['votes'], reverse=True)[:50]


@dataclass(frozen=True)
class HintResult:
    comments: list
    message: str


@dataclass(frozen=True)
class PhotoResult:
    image: object
    message: str


def photo_url(url):
    return isinstance(url, str) and re.fullmatch(
        r'https://game-cdn\.appsample\.com/gim/comments/[A-Za-z0-9_./-]+', url) is not None


class HintService:
    def __init__(self, directory, fetch=None, clock=time.time, fetch_image=None):
        self.directory = directory
        self.fetch = fetch or self._fetch
        self.clock = clock
        self.lock = threading.Lock()
        self.pending = {}
        self.fetch_image = fetch_image or self._fetch_image

    @staticmethod
    def _fetch(kind, identifier):
        query = urlencode({'action':'get', 'app':'gim', 'ttl':7000, 'categoryId':kind,
                           'docId':identifier, 'sort':'', 'page':1, 'pageSize':50})
        with urlopen('https://cache-proxy.lemonapi.com/skywise/comment/v1?' + query, timeout=8) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Resposta de comentários grande demais')
        return json.loads(raw)

    @staticmethod
    def _fetch_image(url):
        with urlopen(url, timeout=8) as response:
            if not photo_url(response.geturl()):
                raise ValueError('Origem da foto inválida')
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('Foto grande demais')
        return raw

    @staticmethod
    def _decode_image(raw):
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('Foto grande demais')
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError('Dimensões de foto grandes demais')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((960, 640), Image.Resampling.LANCZOS)
            return image.copy()

    def request_image(self, url):
        future = Future()
        if not photo_url(url):
            future.set_result(PhotoResult(None, 'Foto indisponível.'))
            return future
        key = ('photo', hashlib.sha256(url.encode()).hexdigest())
        with self.lock:
            if key in self.pending:
                return self.pending[key]
            if len(self.pending) >= 2:
                future.set_result(PhotoResult(None, 'Consulta ocupada. Tente outra vez.'))
                return future
            self.pending[key] = future
        threading.Thread(target=self._run_image, args=(key, url, future), name='MarkerPhoto', daemon=True).start()
        return future

    def _run_image(self, key, url, future):
        try:
            result = self._load_image(key[1], url)
        except Exception:
            result = PhotoResult(None, 'Não foi possível carregar esta foto.')
        with self.lock:
            self.pending.pop(key, None)
        future.set_result(result)

    def _load_image(self, digest, url):
        directory = self.directory / 'photos'
        path = directory / (digest + '.jpg')
        cached = None
        try:
            if path.stat().st_size <= 8 * 1024 * 1024:
                cached = self._decode_image(path.read_bytes())
                if 0 <= self.clock() - path.stat().st_mtime < TTL:
                    return PhotoResult(cached, 'Foto do AppSample · cópia local')
        except (OSError, ValueError):
            pass
        try:
            image = self._decode_image(self.fetch_image(url))
        except Exception:
            if cached is not None:
                return PhotoResult(cached, 'Sem conexão · foto salva anteriormente')
            return PhotoResult(None, 'Não foi possível carregar esta foto. Use Atualizar.')
        temp = None
        try:
            directory.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(dir=directory, suffix='.tmp')
            with os.fdopen(fd, 'wb') as output:
                image.save(output, format='JPEG', quality=88)
            os.replace(temp, path)
            files = sorted(directory.glob('*.jpg'), key=lambda p:p.stat().st_mtime, reverse=True)
            total = 0
            for index, file in enumerate(files):
                total += file.stat().st_size
                if index >= 128 or total > 32 * 1024 * 1024:
                    file.unlink()
        except OSError:
            pass
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)
        return PhotoResult(image, 'Foto da comunidade · AppSample')

    def request(self, item, refresh=False):
        key = identity(item)
        future = Future()
        if key is None:
            future.set_result(HintResult([], 'Ajuda indisponível para esta fonte.'))
            return future
        key = key[:2]
        with self.lock:
            if key in self.pending:
                return self.pending[key]
            if len(self.pending) >= 2:
                future.set_result(HintResult([], 'Consulta ocupada. Use Atualizar em instantes.'))
                return future
            self.pending[key] = future
        threading.Thread(target=self._run, args=(key, future, refresh), name='MarkerHints', daemon=True).start()
        return future

    def _run(self, key, future, refresh):
        try:
            result = self._load(key, refresh)
        except Exception:
            result = HintResult([], 'Não foi possível carregar as dicas. Tente Atualizar.')
        with self.lock:
            self.pending.pop(key, None)
        future.set_result(result)

    def _load(self, key, refresh=False):
        path = self.directory / ('-'.join(key) + '.json')
        cached = None
        try:
            if path.stat().st_size <= MAX_BYTES:
                cached = json.loads(path.read_text(encoding='utf-8'))
                # Validate cached content through the same parser used for the network.
                comments = parse_comments(cached['payload'])
                age = self.clock() - cached['saved_at']
                if not refresh and cached.get('photo_catalog') is True and 0 <= age < TTL:
                    return HintResult(comments, 'Cópia local · AppSample')
        except (OSError, ValueError, KeyError, TypeError):
            cached = None
        try:
            rows = parse_comments(self.fetch(*key))
        except Exception:
            if cached is not None:
                return HintResult(comments, 'Sem conexão · cópia local antiga do AppSample')
            return HintResult([], 'Não foi possível carregar as dicas. Tente Atualizar ou abra o AppSample.')
        # Store only display fields, never account identifiers or raw API responses.
        payload = {'data':{'comments':[{'content':escape(r['text']), 'aname':escape(r['author']), 'vote':r['votes'],
                    'trans':{'pt':escape(r['text'])} if r['translated'] else {},
                    'image':r['image'].removeprefix('https://game-cdn.appsample.com')} for r in rows]}}
        try:
            write_json(path, {'saved_at':self.clock(), 'photo_catalog':True, 'payload':payload})
            files = sorted(self.directory.glob('o*-*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
            for old in files[128:]:
                old.unlink()
        except OSError:
            pass
        return HintResult(rows, 'Fotos da comunidade · AppSample')
