#!/usr/bin/env bash
set -euo pipefail
python3 scripts/generate_assets.py
python3 -m PyInstaller --noconfirm tello_controller.spec
