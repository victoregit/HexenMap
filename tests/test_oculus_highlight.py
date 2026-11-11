from PIL import Image,ImageDraw
from src.live import marker_art as art


def test_oculus_outline_is_visual_only_and_original_image_is_preserved(monkeypatch):
    source=Image.new('RGBA',(32,32));ImageDraw.Draw(source).ellipse((9,9,23,23),fill='#739A9A')
    original=source.tobytes()
    monkeypatch.setattr(art,'map_art',lambda category:source)
    art.pin_image.cache_clear();art.icon_geometry.cache_clear()
    try:
        geometry=art.icon_geometry('cryoculus',28);image=art.pin_image('cryoculus',28,28)
        halo=[]
        for y in range(28):
            for x in range(28):
                if image.getpixel((x,y))[3] and not geometry.contains(0,0,x+geometry.left,y+geometry.top):halo.append((x,y))
        assert halo and geometry.visual_rows!=geometry.rows
        # The visual halo must not recreate a bright white plate behind the art.
        colors=[image.getpixel(point)[:3] for point in halo]
        assert all(max(color)<210 for color in colors)
        assert len(set(colors))>2
        collected=art.pin_image('cryoculus',28,28,True)
        assert collected.getchannel('A').tobytes()==image.getchannel('A').tobytes()
        assert source.tobytes()==original
    finally:art.pin_image.cache_clear();art.icon_geometry.cache_clear()
