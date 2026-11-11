from src.live.panel import CompactPanel
from src.overlay.window_tracker import GameWindowRect


def panel(position):
    result=CompactPanel();result.last_panel_position=position;result.compact_size=76
    result.panel_desktop_bounds=lambda:(0,0,5120,2160)
    return result


def test_eye_stays_inside_small_game_window_on_ultrawide_monitor():
    app=panel((32,80));game=GameWindowRect(1600,400,1920,1200,is_found=True)
    assert app.compact_position(game)==(1612,412)
    app.last_panel_position=(5000,2000)
    assert app.compact_position(game)==(3432,1512)


def test_eye_follows_game_movement_with_same_client_offset():
    app=panel((1700,500));game=GameWindowRect(1600,400,1920,1200,is_found=True)
    assert app.compact_position(game)==(1700,500)
    moved=GameWindowRect(1900,600,1920,1200,is_found=True)
    assert app.compact_position(moved,follow=True)==(2000,700)


def test_negative_monitor_coordinates_are_preserved():
    app=panel((-5000,-900));game=GameWindowRect(-3840,-100,1920,1200,is_found=True)
    assert app.compact_position(game)==(-3828,-88)
