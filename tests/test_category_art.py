import io,json,hashlib
from PIL import Image
import pytest
from src.live import category_art as art


@pytest.fixture
def personal_icons(tmp_path,monkeypatch):
    root=tmp_path/'userData/assets/appsample';root.mkdir(parents=True)
    stream=io.BytesIO();Image.new('RGBA',(64,64),(90,180,240,255)).save(stream,format='PNG');raw=stream.getvalue()
    (root/'o111.png').write_bytes(raw)
    (root/'SOURCE.json').write_text(json.dumps({'icons':{'as-o111':{'file':'o111.png','sha256':hashlib.sha256(raw).hexdigest()}}}))
    monkeypatch.setattr(art,'install_dir',lambda:tmp_path);art.manifest.cache_clear();art.category_image.cache_clear()
    yield root
    art.manifest.cache_clear();art.category_image.cache_clear()


def test_exact_category_art_is_cached_and_other_sources_are_not_guessed(personal_icons):
    image=art.category_image('as-o111')
    assert image.size==(22,22) and art.category_image('as-o111') is image
    assert art.category_image('kongying:o111') is None
    assert art.category_image('common-chest') is None # Existing official art keeps priority.


def test_collected_card_art_preserves_alpha_in_grayscale(personal_icons):
    image=art.category_image('as-o111',34,True)
    r,g,b,a=image.getpixel((10,10));assert r==g==b and a==255


def test_corrupted_or_missing_icon_falls_back(personal_icons):
    (personal_icons/'o111.png').write_bytes(b'bad')
    assert art.category_image('as-o111') is None


def test_asset_paths_cannot_escape_the_personal_directory(personal_icons):
    source=json.loads((personal_icons/'SOURCE.json').read_text());source['icons']['as-o111']['file']='../../outside.png'
    (personal_icons/'SOURCE.json').write_text(json.dumps(source))
    assert art.category_image('as-o111') is None
