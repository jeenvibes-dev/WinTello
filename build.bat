@echo off
setlocal
py -3.13 scripts\generate_assets.py
py -3.13 -m PyInstaller --noconfirm tello_controller.spec
