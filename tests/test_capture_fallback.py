from unittest.mock import Mock

import numpy as np

from src.live.native import Windows
from src.overlay.window_tracker import GameWindowRect


def setup_native(frames):
    native=Windows.__new__(Windows);native.capture_visible=False
    native.foreground=lambda rect:True
    native._capture_frame=Mock(side_effect=frames)
    native._capture_graphics=Mock(return_value=None)
    return native,GameWindowRect(50,80,1920,1200,hwnd=99)


def test_white_desktop_uses_client_then_retains_working_backend():
    white=np.full((1200,1920,3),255,np.uint8)
    game=np.full((1200,1920,3),80,np.uint8)
    native,rect=setup_native([white,game,game])
    assert native.capture(rect) is game
    assert [c.args[-1] for c in native._capture_frame.call_args_list]==[None,99]
    assert native.capture(rect) is game
    assert native._capture_frame.call_args.args[-1]==99
    assert not native.capture_error


def test_partial_frame_checks_captured_pixels_instead_of_zero_padding():
    frame=np.zeros((1200,1920,3),np.uint8);frame[:420]=255
    native,rect=setup_native([frame,frame])
    assert native.capture(rect,.35) is None
    assert 'branca/preta' in native.capture_error


def test_streamer_sharing_never_falls_back_to_desktop_with_own_pins():
    native,rect=setup_native([np.zeros((1200,1920,3),np.uint8)])
    native.capture_visible=True
    assert native.capture(rect) is None
    native._capture_frame.assert_called_once_with(rect,1.,None,99)


def test_healthy_desktop_does_not_retry():
    game=np.full((1200,1920,3),80,np.uint8)
    native,rect=setup_native([game])
    assert native.capture(rect) is game
    native._capture_frame.assert_called_once_with(rect,1.,None,None)


def test_both_gdi_methods_fail_then_graphics_capture_is_retained():
    white=np.full((1200,1920,3),255,np.uint8)
    game=np.full((1200,1920,3),80,np.uint8)
    native,rect=setup_native([white,white])
    native._capture_graphics.return_value=game
    assert native.capture(rect) is game
    assert native.capture_backend=='Windows Graphics Capture'
    assert native.capture(rect) is game
    assert native._capture_frame.call_count==2
