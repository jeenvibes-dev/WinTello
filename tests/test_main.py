from __future__ import annotations

import main


def test_run_app_headless_smoke():
    result = main.run_app(frame_limit=1, headless=True, auto_connect=False)
    assert result == 0
