from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from utils import load_sound, resource_path


def test_resource_path_resolves_inside_project():
    resolved = Path(resource_path("README.md"))
    assert resolved.name == "README.md"
    assert resolved.exists()


def test_load_sound_returns_none_when_asset_missing():
    fake_pygame = SimpleNamespace(mixer=SimpleNamespace(Sound=lambda path: (_ for _ in ()).throw(FileNotFoundError(path))))
    sound = load_sound(fake_pygame, "sounds/missing.wav")
    assert sound is None
