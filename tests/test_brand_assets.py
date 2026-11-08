from PIL import Image

from src.live.brand import badge_frames, animation_frame
from src.live.storage import bundle_dir


def test_gif_disposal_timing_transparency_and_small_size_are_preserved():
    frames,durations=badge_frames(64)
    with Image.open(bundle_dir()/'data/assets/brand/minimized.gif') as original:
        assert len(frames)==original.n_frames==68
        for n,frame in enumerate(frames):
            original.seek(n)
            assert durations[n]==original.info['duration']
            assert frame.size==(64,64) and frame.getchannel('A').getextrema()==(0,255)
    assert len({frame.tobytes() for frame in frames})>1
    assert badge_frames(64)[0] is frames


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
