from PIL import Image

from src.live.brand import badge_frames, animation_frame,badge_symbol_angle
from src.live.storage import bundle_dir


def test_collapsed_badge_stays_clickable_during_long_cycle_with_occasional_cut():
    import json
    assets=bundle_dir()/'data/assets/brand'
    metadata=json.loads((assets/'animations.json').read_text(encoding='utf-8'))['minimized']
    assert metadata['identity']=='electro-rift-spin-v3'
    frames,durations=badge_frames(64)
    assert len(frames)==len(durations)==504
    assert set(durations)=={41,42}
    assert sum(durations)==21000
    assert all(frame.size==(64,64) for frame in frames)
    # No blank button, including the old transparent beginning/end of the cut.
    assert all(sum(value>0 for value in frame.getchannel('A').crop((26,26,38,38)).getdata())>60 for frame in frames)
    assert frames[72].getchannel('A').getextrema()==(0,255)
    assert all({value for _,value in frame.getchannel('A').getcolors()}<={0,255} for frame in frames)
    assert len({frame.tobytes() for frame in frames})>60
    assert badge_frames(64)[0] is frames
    elapsed=0
    for index,duration in enumerate(durations):
        assert animation_frame(durations,elapsed)==(index,duration)
        elapsed+=duration
    assert animation_frame(durations,21000)==(0,durations[0])


def test_collapsed_badge_reads_the_atlas_in_row_order_without_neighbor_pixels():
    import json
    assets=bundle_dir()/'data/assets/brand'
    metadata=json.loads((assets/'animations.json').read_text(encoding='utf-8'))['minimized']
    frames,_=badge_frames(76)
    with Image.open(assets/'minimized-rift.png') as atlas:
        assert atlas.size==(1536,2880)
        for playback,index in [(0,65),(7,72),(8,73),(23,88),(24,87),(45,66)]:
            x=index%8*192;y=index//8*192
            expected=atlas.crop((x,y,x+192,y+192)).convert('RGBA').resize((76,76),Image.Resampling.LANCZOS)
            expected.putalpha(expected.getchannel('A').point(lambda value:255 if value>=128 else 0))
            # Independent emblem and bloom occupy the central area only.
            assert frames[playback].crop((0,0,76,20)).tobytes()==expected.crop((0,0,76,20)).tobytes()


def test_emblem_never_reverses_and_loop_has_no_rotation_jump():
    angles=[badge_symbol_angle(i/240) for i in range(21*240+1)]
    assert all(b>a for a,b in zip(angles,angles[1:]))
    assert abs(angles[-1]-angles[0]-1080)<1e-8
    assert abs((angles[1]-angles[0])-(angles[-1]-angles[-2]))<.001


def test_launcher_frames_match_lossless_atlas_in_reading_order():
    assets=bundle_dir()/'data/assets/brand'
    import json
    timing=json.loads((assets/'animations.json').read_text(encoding='utf-8'))
    assert timing['loading_identity']=='traveler-viator-transparent-v3'
    assert sum(timing['loading_durations_ms'])==2000
    with Image.open(assets/'loading.png') as atlas:
        assert atlas.size==(192*48,192)
        for index in range(48):
            with Image.open(assets/'loading'/f'{index:02}.png') as frame:
                assert frame.tobytes()==atlas.crop((index*192,0,(index+1)*192,192)).tobytes()
                assert frame.getchannel('A').getextrema()[0]==0


def test_animation_uses_real_durations_and_recovers_after_delayed_callbacks():
    durations=(230,30,560)
    assert animation_frame(durations,0)==(0,230)
    assert animation_frame(durations,229)==(0,1)
    assert animation_frame(durations,230)==(1,30)
    assert animation_frame(durations,260)==(2,560)
    assert animation_frame(durations,820)==(0,230)
    assert animation_frame(durations,820*7+250)==(1,10)


def test_windows_icon_has_transparency_and_sizes_for_taskbar_and_executable():
    with Image.open(bundle_dir()/'data/assets/brand/app.ico') as icon:
        assert {(16,16),(32,32),(48,48),(256,256)}<=icon.ico.sizes()
        for size in icon.ico.sizes():
            assert icon.ico.getimage(size).getchannel('A').getextrema()==(0,255)


def test_launcher_constellation_has_no_icon_background_or_emblem_plate():
    import numpy as np
    assets=bundle_dir()/'data/assets/brand'
    for index in [0,12,24,33,47]:
        with Image.open(assets/'loading'/f'{index:02}.png') as frame:
            alpha=np.asarray(frame.getchannel('A'))
            assert alpha[0,0]==alpha[0,-1]==alpha[-1,0]==alpha[-1,-1]==0
            assert np.count_nonzero(alpha)<alpha.size*.35
    with Image.open(assets/'loading/33.png') as frame:
        assert frame.getchannel('A').getextrema()==(0,255)
