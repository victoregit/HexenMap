"""Screen capture subsystem providing Win32 and cross-platform capture backends."""

from src.capture.base import ScreenCaptureInterface
from src.capture.win32_capture import (
    MockScreenCapture,
    Win32ScreenCapture,
    get_screen_capture,
)

__all__ = [
    "ScreenCaptureInterface",
    "MockScreenCapture",
    "Win32ScreenCapture",
    "get_screen_capture",
]
