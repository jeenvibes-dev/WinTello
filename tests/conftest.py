from __future__ import annotations

import os
from pathlib import Path


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def pytest_sessionstart(session):  # pragma: no cover
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
