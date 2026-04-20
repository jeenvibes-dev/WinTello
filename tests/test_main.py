from __future__ import annotations

import main


class DisplayInfo:
    def __init__(self, width: int, height: int) -> None:
        self.current_w = width
        self.current_h = height


def test_run_app_headless_smoke():
    result = main.run_app(frame_limit=1, headless=True, auto_connect=False)
    assert result == 0


def test_initial_window_size_caps_to_large_display_preference():
    assert main.calculate_initial_window_size(DisplayInfo(2560, 1440)) == (1600, 900)


def test_initial_window_size_adapts_to_laptop_display():
    assert main.calculate_initial_window_size(DisplayInfo(1366, 768)) == (1256, 660)


def test_initial_window_size_can_fit_below_minimum_on_small_display():
    assert main.calculate_initial_window_size(DisplayInfo(900, 600)) == (828, 516)
