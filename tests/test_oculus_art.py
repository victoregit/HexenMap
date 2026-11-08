import hashlib,io,json
from pathlib import Path
from PIL import Image
from src.live import oculus_art as art


def test_manifest_identifies_the_eight_official_oculi_by_name():
    source=json.loads((Path(__file__).resolve().parents[1]/'data/assets/oculi/SOURCE.json').read_text(encoding='utf-8'))
    assert tuple(source['icons'])==art.ORDER
    for category,entry in source['icons'].items():
        assert entry['name'].lower()==category and len(entry['sha256'])==64
        assert entry['url'].startswith(('https://act.hoyoverse.com/','https://act-webstatic.hoyoverse.com/'))


def test_corrupted_or_missing_personal_art_uses_the_existing_symbol(tmp_path,monkeypatch):
    metadata=tmp_path/'data/assets/oculi';metadata.mkdir(parents=True)
    personal=tmp_path/'userData/assets/oculi';personal.mkdir(parents=True)
    stream=io.BytesIO();Image.new('RGBA',(12,12),(0,200,200,255)).save(stream,format='PNG');raw=stream.getvalue()
    (metadata/'SOURCE.json').write_text(json.dumps({'icons':{'anemoculus':{'file':'anemoculus.png','sha256':hashlib.sha256(raw).hexdigest()}}}))
    monkeypatch.setattr(art,'bundle_dir',lambda:tmp_path);monkeypatch.setattr(art,'install_dir',lambda:tmp_path)
    try:
        art.oculus_art.cache_clear();assert art.oculus_art('anemoculus') is None
        (personal/'anemoculus.png').write_bytes(raw);art.oculus_art.cache_clear();assert art.oculus_art('anemoculus').size==(12,12)
        (personal/'anemoculus.png').write_bytes(b'corrupted');art.oculus_art.cache_clear();assert art.oculus_art('anemoculus') is None
    finally:art.oculus_art.cache_clear()
