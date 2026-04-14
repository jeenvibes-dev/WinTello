# Tello Controller

Python + pygame desktop app for controlling a DJI Tello with an Xbox controller.

## Current Status

Phase 3 integration is implemented. The app now includes the main control loop, dashboard rendering, alert selection, button legends, controller visualization, and sound fallbacks on top of the controller and drone layers.

## Local Setup

```powershell
py -3.13 -m pip install -r requirements.txt
```

Note: this project now requires the real `pygame` package and no longer uses a fallback renderer.
On this machine, use Python 3.13 for the app and tests. Python 3.14 is installed too, but `pygame 2.6.1` is working here under Python 3.13.

## Run The App

```powershell
py -3.13 main.py
```

If the laptop is not connected to the Tello Wi-Fi yet, the app should still launch and remain in a disconnected state.

## Run Automated Tests

```powershell
py -3.13 -m pytest
```

## Build The App

```powershell
build.bat
```

This generates the icon and WAV files first, then builds the packaged executable with PyInstaller.

## Hardware Expectations

- Windows 10 or 11
- Xbox controller over USB or Bluetooth
- DJI Tello on local Wi-Fi for later phases

## Current Limitations

- Packaging files are scaffolded but not verified yet
- A working local `pygame` installation is required to launch the app window
- Packaging and competition-day validation still belong to Phase 4
