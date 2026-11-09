from dataclasses import replace
import threading

from src.live.catalog import Item
from src.live.marker_hints import HintService, identity, marker_url, parse_comments, TTL


ITEM = Item('appsample:marker:123', 'Baú', 'common-chest', 0, 0, map_id='as-map-2')
PAYLOAD = {'data':{'comments':[
    {'content':'Original', 'trans':{'pt':'<p>Acenda as tochas.</p><script>bad()</script>'},
     'aname':'Pessoa', 'vote':15, 'image':'/gim/comments/o17/123/test.jpg'},
    {'content':'<b>Outra dica</b>', 'vote':2, 'image':'https://evil.invalid/image.jpg'}]}}


def test_exact_source_identity_and_deep_link():
    assert identity(ITEM) == ('o17', '123', '2')
    assert marker_url(ITEM).endswith('?id=123&mid=2&type=o17')
    assert identity(replace(ITEM, category='as-o52', map_id='as-map-7')) == ('o52','123','7')
    assert identity(replace(ITEM, id='teyvat.moe:123')) is None
    assert identity(replace(ITEM, category='unknown')) is None
    assert identity(replace(ITEM, map_id='teyvat')) is None


def test_translation_html_images_and_votes():
    rows = parse_comments(PAYLOAD)
    assert rows[0]['text'] == 'Acenda as tochas.'
    assert rows[0]['translated'] and rows[0]['votes'] == 15
    assert rows[0]['image'] == 'https://game-cdn.appsample.com/gim/comments/o17/123/test.jpg'
    assert rows[1]['text'] == 'Outra dica' and rows[1]['image'] == ''


def test_cache_offline_and_refresh(tmp_path):
    calls = []
    now = [100]
    def fetch(*key):
        calls.append(key)
        return PAYLOAD
    service = HintService(tmp_path, fetch=fetch, clock=lambda:now[0])
    first = service.request(ITEM).result(2)
    assert first.comments[0]['text'] == 'Acenda as tochas.'
    assert service.request(ITEM).result(2).comments == first.comments
    assert len(calls) == 1
    service.request(ITEM, refresh=True).result(2)
    assert len(calls) == 2
    now[0] += TTL + 1
    service.fetch = lambda *args: (_ for _ in ()).throw(OSError('offline'))
    stale = service.request(ITEM).result(2)
    assert stale.comments == first.comments and 'antiga' in stale.message
    assert 'auid' not in next(tmp_path.glob('*.json')).read_text()


def test_no_comments_vs_invalid_response_and_corrupt_cache(tmp_path):
    service = HintService(tmp_path, fetch=lambda *key:{'data':{'comments':[]}})
    assert service.request(ITEM).result(2).comments == []
    for path in tmp_path.glob('*.json'):
        path.write_text('broken', encoding='utf-8')
    service.fetch = lambda *key:{'error':'rate limited'}
    result = service.request(ITEM).result(2)
    assert not result.comments and 'Não foi possível' in result.message


def test_deduplicates_requests_and_bounds_pending_work(tmp_path):
    gate = threading.Event()
    def fetch(*key):
        gate.wait(2)
        return PAYLOAD
    service = HintService(tmp_path, fetch=fetch)
    try:
        first = service.request(ITEM)
        assert service.request(ITEM) is first
        second = service.request(replace(ITEM, id='appsample:marker:124'))
        busy = service.request(replace(ITEM, id='appsample:marker:125')).result(1)
        assert 'ocupada' in busy.message
    finally:
        gate.set()
    assert first.result(2).comments and second.result(2).comments


def test_unsupported_source_never_fetches(tmp_path):
    service = HintService(tmp_path, fetch=lambda *args:1/0)
    assert 'indisponível' in service.request(replace(ITEM, id='demo:1')).result().message


def test_card_switch_and_close_ignore_old_responses():
    from concurrent.futures import Future
    from types import SimpleNamespace
    import tkinter as tk
    from src.live.marker_menu import MarkerMenu
    from src.live.marker_hints import HintResult
    root = tk.Tk()
    root.withdraw()
    futures = []
    photo_futures = []
    class Service:
        def request(self, *args, **kwargs):
            future = Future()
            futures.append(future)
            return future
        def request_image(self, url):
            future = Future()
            photo_futures.append(future)
            return future
    native = SimpleNamespace(popup=lambda *args:1, place=lambda *args:None)
    game = SimpleNamespace(x=-800,y=0,width=800,height=600)
    progress = SimpleNamespace(is_collected=lambda *args:False)
    card = None
    try:
        card = MarkerMenu(root,native,game,[ITEM,replace(ITEM,id='appsample:marker:124')],
                          progress,lambda *args:None,lambda:None,-10,590,hints=Service())
        left, top, right, bottom = card.bounds
        assert game.x <= left < right <= game.x+game.width
        assert 0 <= top < bottom <= game.height
        old_generation = card.hint_generation
        card.select(1)
        futures[0].set_result(HintResult([{'text':'old'}], 'old'))
        card._poll_hints(futures[0],old_generation)
        assert card.photos == []
        futures[1].set_result(HintResult(parse_comments(PAYLOAD), 'AppSample'))
        card._poll_hints(futures[1],card.hint_generation)
        assert len(card.photos) == 1
        from PIL import Image
        from src.live.marker_hints import PhotoResult
        photo_futures[0].set_result(PhotoResult(Image.new('RGB',(800,600),'red'),'Foto'))
        card._poll_photo(photo_futures[0],card.photo_generation)
        assert card.photo_image is not None
        assert card.photo_image.width() <= card.photo_size[0]
        assert card.photo_canvas.type(card.photo_canvas.find_all()[0]) == 'image'
        card._load_hints(True)
        card.destroy()
        card = None
        futures[2].set_result(HintResult([], 'closed'))
        root.update()
    finally:
        if card is not None:
            card.destroy()
        root.destroy()


def test_photos_decode_cache_and_failure(tmp_path):
    import io
    from PIL import Image
    output = io.BytesIO()
    Image.new('RGB',(1920,1080),'blue').save(output,format='PNG')
    calls = []
    def fetch(url):
        calls.append(url)
        return output.getvalue()
    service = HintService(tmp_path, fetch_image=fetch)
    url = 'https://game-cdn.appsample.com/gim/comments/o17/123/test.png'
    result = service.request_image(url).result(3)
    assert result.image.size == (960,540)
    assert service.request_image(url).result(3).image.size == (960,540)
    assert len(calls) == 1
    assert service.request_image('https://evil.invalid/photo').result().image is None
    service.fetch_image = lambda url:b'not an image'
    assert service.request_image(url+'-bad').result(3).image is None


def test_photos_preserved_after_top_ten_text_comments():
    payload = {'data':{'comments':[{'content':'text','vote':100-i} for i in range(20)] +
                                  [{'image':'/gim/comments/o17/123/photo.jpg','vote':1}]}}
    assert any(row['image'] for row in parse_comments(payload))
