from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


def resource_path(relative_path: str) -> str:
    """Return an absolute path for a bundled or local resource."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return os.path.join(base_path, relative_path)
    return str(Path(__file__).resolve().parent / relative_path)


def load_sound(pygame_module: Any, relative_path: str):
    """Load a sound if available, otherwise return None."""
    try:
        return pygame_module.mixer.Sound(resource_path(relative_path))
    except Exception as exc:  # pragma: no cover - intentionally broad for resilience
        LOGGER.warning("Unable to load sound %s: %s", relative_path, exc)
        return None
