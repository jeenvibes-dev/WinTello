from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_build_scripts_reference_asset_generation():
    build_bat = (PROJECT_ROOT / "build.bat").read_text()
    build_sh = (PROJECT_ROOT / "build.sh").read_text()
    assert "generate_assets.py" in build_bat
    assert "generate_assets.py" in build_sh


def test_spec_references_icon_and_asset_directories():
    spec_text = (PROJECT_ROOT / "tello_controller.spec").read_text()
    assert "sounds/*.wav" in spec_text
    assert "assets/*.png" in spec_text
    assert "assets/icon.ico" in spec_text


def test_generated_assets_exist_after_generation():
    sounds = [
        PROJECT_ROOT / "sounds" / "connect.wav",
        PROJECT_ROOT / "sounds" / "takeoff.wav",
        PROJECT_ROOT / "sounds" / "land.wav",
        PROJECT_ROOT / "sounds" / "low_battery.wav",
        PROJECT_ROOT / "sounds" / "error.wav",
    ]
    images = [
        PROJECT_ROOT / "assets" / "icon.png",
        PROJECT_ROOT / "assets" / "icon.ico",
    ]
    for path in sounds + images:
        assert path.exists(), f"Missing generated asset: {path}"
