# Tello Xbox Controller Desktop App — Full Specification

## Project Overview

A standalone Python + pygame desktop application that enables DJI Tello drone flight control using an Xbox controller, completely bypassing the crash-prone official Tello iPad app. The app communicates with the Tello via UDP commands (djitellopy SDK) and intentionally does NOT use the video stream, eliminating the root cause of the iPad crashes. This app is being built for a TSA (Technology Student Association) competition with a hard 2-week deadline.

---

## Goals & Constraints

### Primary Goals
- Provide reliable, crash-free DJI Tello flight control via Xbox controller
- Display real-time drone telemetry (battery, height, speed, connection status)
- Run as a standalone desktop app (no terminal, no IDE required)
- Package as a single .exe (Windows) or .app (Mac) via PyInstaller

### Hard Constraints
- **No video streaming** — this is intentional; video causes the iPad crashes and is not needed
- **2-week build timeline** — must be testable by day 7, competition-ready by day 14
- **Single-file packaging** — competition day requires one-click launch, no Python install
- **Xbox controller only** — Xbox One or Xbox Series X|S controller via USB or Bluetooth
- **Offline operation** — no internet required; laptop connects directly to Tello Wi-Fi AP

### Non-Goals (out of scope)
- Video feed display
- Mobile/tablet support
- Keyboard flight control (controller only; keyboard used only for app-level shortcuts)
- Multi-drone support
- Recording or logging flight data to file

---

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ |
| UI Framework | pygame | 2.5+ |
| Drone SDK | djitellopy | 2.5+ |
| Packaging | PyInstaller | 6.0+ |
| OS Target | Windows 10/11 (primary), macOS (secondary) |

### Install Command
```bash
pip install djitellopy pygame pyinstaller
```

---

## Application Architecture

### File Structure
```
tello-controller/
├── main.py                  # Entry point — initializes app and runs main loop
├── controller.py            # Xbox controller input handling
├── drone.py                 # Tello connection, commands, telemetry polling
├── ui.py                    # Pygame window rendering (dashboard, HUD)
├── config.py                # All tunable constants (deadzone, speeds, window size, colors)
├── sounds/
│   ├── connect.wav          # Short chime on successful Tello connection
│   ├── takeoff.wav          # Short chime on takeoff
│   ├── land.wav             # Short chime on landing
│   ├── low_battery.wav      # Warning beep for low battery
│   └── error.wav            # Error buzz for connection loss or failures
├── assets/
│   └── icon.png             # App window icon (64x64 or 128x128 PNG)
├── tello_controller.spec    # PyInstaller spec file for building .exe
├── build.bat                # Windows build script (runs PyInstaller)
├── build.sh                 # macOS/Linux build script
├── requirements.txt         # pip freeze output
└── README.md                # Setup and usage instructions
```

### Module Responsibilities

#### `main.py` — Application Entry Point
- Initialize pygame display, mixer (for sounds), and clock
- Instantiate Controller, Drone, and UI objects
- Run the main game loop at 60 FPS:
  1. Poll controller inputs via `Controller.update()`
  2. Send flight commands via `Drone.send_rc()` or button-triggered commands
  3. Poll drone telemetry via `Drone.get_telemetry()`
  4. Render UI via `UI.draw()`
  5. Handle pygame quit event and cleanup
- On exit: send land command (if airborne), disconnect drone, quit pygame

#### `controller.py` — Xbox Controller Input
- Detect and initialize the first connected pygame joystick
- Read axis values each frame and apply deadzone + sensitivity curve
- Read button states and detect press/release edges (not held states, to avoid repeat triggers)
- Expose a clean data object each frame:
  ```python
  @dataclass
  class ControllerState:
      # Axes (float, -100 to 100 after processing)
      left_x: float     # Yaw (rotate)
      left_y: float     # Throttle (up/down)
      right_x: float    # Roll (strafe)
      right_y: float    # Pitch (forward/back)
      
      # Button press edges (True only on the frame the button is first pressed)
      a_pressed: bool        # Takeoff
      b_pressed: bool        # Land
      x_pressed: bool        # Emergency stop
      y_pressed: bool        # Flip
      lb_pressed: bool       # Speed: slow
      rb_pressed: bool       # Speed: fast
      start_pressed: bool    # Query battery / reconnect
      
      # Controller meta
      connected: bool
  ```
- Handle controller disconnect gracefully (set `connected = False`, UI shows warning)
- Handle controller reconnect (re-scan joysticks each second if disconnected)

#### `drone.py` — Tello Drone Interface
- Wrap djitellopy.Tello with connection management and error handling
- **Connection**: connect on startup, auto-reconnect on failure (retry every 3 seconds, max 5 retries)
- **Flight Commands**:
  - `send_rc(left_right, forward_back, up_down, yaw)` — called every frame from controller axes
  - `takeoff()` — with safety guard (only if not already airborne)
  - `land()` — with safety guard (only if airborne)
  - `emergency()` — immediate motor shutoff
  - `flip(direction)` — forward flip (only if battery > 50% and height > 0.5m)
- **Telemetry** (polled in a background thread every 500ms):
  ```python
  @dataclass
  class TelemetryData:
      connected: bool
      battery: int           # 0-100 %
      height: int            # cm
      temperature: int       # °C
      flight_time: int       # seconds since takeoff
      speed: float           # estimated speed (from SDK)
      airborne: bool         # True if currently flying
      signal_strength: str   # "strong" / "weak" / "none"
  ```
- All SDK calls wrapped in try/except — never crash the app on a Tello error
- Expose `is_connected`, `is_airborne` properties for UI and safety checks

#### `ui.py` — Pygame Dashboard Rendering
- Render all UI elements onto the pygame display surface each frame
- **No pygame GUI widgets / no text input** — display only (all interaction is via Xbox controller)
- Layout divided into sections (see UI Layout section below)
- All colors, fonts, and sizes pulled from `config.py`
- Render at native resolution; scale text for readability

#### `config.py` — Tunable Constants
```python
# ── Window ──
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 500
WINDOW_TITLE = "Tello Controller"
FPS = 60

# ── Controller ──
DEADZONE = 0.15              # Ignore axis values below 15%
SENSITIVITY_CURVE = "linear" # "linear" or "exponential"
EXPONENTIAL_FACTOR = 2.0     # Used if SENSITIVITY_CURVE == "exponential"
TAKEOFF_HOLD_TIME = 1.0      # Seconds to hold A before takeoff triggers

# ── Speed Modes ──
SPEED_SLOW = 30              # Max RC value in slow mode (0-100)
SPEED_NORMAL = 60            # Default speed
SPEED_FAST = 90              # Max RC value in fast mode

# ── Drone ──
RECONNECT_INTERVAL = 3.0     # Seconds between reconnect attempts
MAX_RECONNECT_RETRIES = 5
TELEMETRY_POLL_INTERVAL = 0.5  # Seconds between telemetry queries
LOW_BATTERY_THRESHOLD = 20   # % — triggers warning
FLIP_MIN_BATTERY = 50        # % — minimum battery to allow flip
FLIP_MIN_HEIGHT = 50         # cm — minimum height to allow flip

# ── Colors (RGB tuples) ──
COLOR_BG = (18, 18, 30)
COLOR_PANEL = (30, 30, 50)
COLOR_TEXT = (220, 220, 230)
COLOR_TEXT_DIM = (120, 120, 140)
COLOR_ACCENT = (0, 150, 255)
COLOR_SUCCESS = (0, 200, 100)
COLOR_WARNING = (255, 200, 0)
COLOR_DANGER = (255, 60, 60)
COLOR_BATTERY_HIGH = (0, 200, 100)
COLOR_BATTERY_MED = (255, 200, 0)
COLOR_BATTERY_LOW = (255, 60, 60)
```

---

## UI Layout

The pygame window (800×500) is divided into panels:

```
┌─────────────────────────────────────────────────────────┐
│  TELLO CONTROLLER                          [CONNECTED]  │  ← Top bar: title + connection status
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│   DRONE STATUS       │      CONTROLLER VISUAL           │
│                      │                                  │
│   Battery: ██████ 78%│      ┌───┐          ┌───┐       │
│   Height:  1.2m      │      │ L │          │ R │       │
│   Temp:    65°C      │      │   │          │   │       │
│   Flight:  0:45      │      └───┘          └───┘       │
│   Speed Mode: NORMAL │      (live joystick positions)   │
│                      │                                  │
├──────────────────────┴──────────────────────────────────┤
│  [A] Takeoff  [B] Land  [X] STOP  [Y] Flip   LB/RB Spd│  ← Bottom bar: button legend
├─────────────────────────────────────────────────────────┤
│  ⚠ LOW BATTERY — LAND SOON                             │  ← Alert bar (hidden when no alerts)
└─────────────────────────────────────────────────────────┘
```

### Panel Details

#### Top Bar
- Left: App title "TELLO CONTROLLER" in bold
- Right: Connection pill — green "CONNECTED" or red "DISCONNECTED" with pulsing animation when disconnected

#### Drone Status Panel (left, ~35% width)
- Battery bar: horizontal fill bar, color changes (green > 50%, yellow 20–50%, red < 20%), percentage text
- Height: in meters (converted from cm), 1 decimal place
- Temperature: Celsius, warn if > 80°C
- Flight time: MM:SS format, starts counting on takeoff
- Speed mode: "SLOW" (blue) / "NORMAL" (white) / "FAST" (orange) label

#### Controller Visual Panel (right, ~65% width)
- Two joystick representations (circles with a dot showing current position)
- Left stick dot moves in real-time with left_x and left_y input
- Right stick dot moves in real-time with right_x and right_y input
- Labels under each: "YAW / THROTTLE" and "ROLL / PITCH"
- Axis values displayed numerically below each stick (e.g., "X: 32  Y: -15")

#### Bottom Bar — Button Legend
- Horizontal row of labeled buttons: [A] Takeoff, [B] Land, [X] STOP, [Y] Flip, LB/RB Speed
- Each highlights/flashes briefly when the corresponding button is pressed
- The button corresponding to current speed mode stays highlighted (LB for slow, RB for fast)

#### Alert Bar (conditional)
- Hidden when there are no alerts
- Appears with a yellow or red background when:
  - Battery < 20%: "⚠ LOW BATTERY — LAND SOON" (yellow bg, pulsing)
  - Battery < 10%: "🔴 CRITICAL BATTERY — LANDING RECOMMENDED" (red bg, pulsing)
  - Controller disconnected: "🎮 CONTROLLER DISCONNECTED — Reconnecting..." (red bg)
  - Drone disconnected: "📡 DRONE DISCONNECTED — Reconnecting..." (red bg)
  - Emergency stop triggered: "🛑 EMERGENCY STOP ACTIVATED" (red bg, 3 second display)

---

## Controller Mapping (Xbox)

| Xbox Input | Axis/Button | Action | Notes |
|-----------|-------------|--------|-------|
| Left Stick Y | Axis 1 | Throttle (up/down) | Up = ascend, Down = descend |
| Left Stick X | Axis 0 | Yaw (rotate L/R) | Left = rotate CCW, Right = rotate CW |
| Right Stick Y | Axis 4 (varies) | Pitch (fwd/back) | Up = forward, Down = backward |
| Right Stick X | Axis 3 (varies) | Roll (strafe L/R) | Left = strafe left, Right = strafe right |
| A Button | Button 0 | Takeoff | Hold for 1 second (safety) |
| B Button | Button 1 | Land | Single press |
| X Button | Button 2 | Emergency Stop | Single press, immediate motor kill |
| Y Button | Button 3 | Flip Forward | Only if battery > 50% and height > 50cm |
| LB (Left Bumper) | Button 4 | Slow Speed Mode | Sets max speed to 30% |
| RB (Right Bumper) | Button 5 | Fast Speed Mode | Sets max speed to 90% |
| Start Button | Button 7 | Reconnect / Status | If disconnected: retry connection. If connected: refresh telemetry. |

### Axis Processing Pipeline
1. Read raw axis value from pygame (-1.0 to 1.0)
2. Apply deadzone: if `abs(value) < DEADZONE`, set to 0
3. Remap remaining range: scale (DEADZONE..1.0) → (0..1.0)
4. Apply sensitivity curve:
   - Linear: `output = remapped_value`
   - Exponential: `output = sign(remapped_value) * (abs(remapped_value) ** EXPONENTIAL_FACTOR)`
5. Multiply by current speed mode max (SPEED_SLOW / SPEED_NORMAL / SPEED_FAST)
6. Cast to int and clamp to -100..100
7. Invert Y axes (pygame Y axis is inverted vs Tello convention)

### Button Edge Detection
- Track previous frame button state for each button
- `pressed = current and not previous` — triggers action once on press, not on hold
- Exception: A button (takeoff) uses a hold timer — must be held for `TAKEOFF_HOLD_TIME` seconds
  - On A press start: begin timer, show "Hold A to takeoff..." in UI
  - On A held for 1.0s: trigger takeoff, play takeoff sound
  - On A released before 1.0s: cancel, show nothing

### Controller Hot-Plug
- If no joystick is detected at startup, show "Connect Xbox Controller" in UI and scan every 1 second
- If joystick disconnects mid-session:
  - Immediately send `send_rc(0, 0, 0, 0)` to stop all movement (drone hovers)
  - Show alert in UI
  - Scan for reconnection every 1 second
  - On reconnect, resume normal operation (no takeoff/land, just RC control resumes)

---

## Drone Communication

### Connection Flow
1. App starts → attempt `tello.connect()`
2. On success: play connect sound, update UI to "CONNECTED", start telemetry thread
3. On failure: show "DISCONNECTED" in UI, retry every `RECONNECT_INTERVAL` seconds
4. After `MAX_RECONNECT_RETRIES` failures: show "Connection failed — check Wi-Fi" and stop retrying (Start button to retry manually)

### RC Command Loop
- Every frame (60 FPS), send `tello.send_rc_control(left_right, forward_back, up_down, yaw)`
- Values are ints from -100 to 100
- If controller is disconnected or drone is not connected, send `(0, 0, 0, 0)` to maintain hover

### Telemetry Thread
- Background thread running a loop with `TELEMETRY_POLL_INTERVAL` sleep
- Each cycle:
  - `tello.get_battery()` → int
  - `tello.get_height()` → int (cm)
  - `tello.get_temperature()` → int (°C)
  - `tello.get_flight_time()` → int (seconds)
- Store results in a thread-safe `TelemetryData` dataclass
- If any query raises an exception, set `connected = False` and trigger reconnect logic

### Safety Rules
- **Takeoff** only allowed if: connected, not already airborne, battery > 10%
- **Land** only allowed if: airborne (otherwise ignored)
- **Emergency Stop** always allowed — sends `tello.emergency()` regardless of state
- **Flip** only allowed if: airborne, battery > `FLIP_MIN_BATTERY`, height > `FLIP_MIN_HEIGHT`
- **App close (window X or Escape key)**: if airborne, send `land()` first, wait up to 5 seconds, then `tello.end()` and quit

---

## Sound Design

All sounds are short (< 1 second), low-bitrate WAV files to keep the package small.

| Event | Sound | Description |
|-------|-------|-------------|
| Tello connected | `connect.wav` | Pleasant rising two-tone chime |
| Takeoff | `takeoff.wav` | Quick ascending tone |
| Land | `land.wav` | Quick descending tone |
| Low battery (< 20%) | `low_battery.wav` | Two short warning beeps, repeats every 30 seconds |
| Error / disconnect | `error.wav` | Low buzzer tone |

If sound files are missing, the app should continue without sound (log a warning to console, don't crash).

### Generating Sounds Programmatically
If pre-made WAV files are not available, generate simple tones at build time using pygame.mixer or a simple script:
```python
# Example: generate a simple beep tone
import numpy as np
import wave, struct
sample_rate = 22050
duration = 0.3
freq = 880
t = np.linspace(0, duration, int(sample_rate * duration), False)
samples = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
# Write to WAV...
```
This keeps the project self-contained with no external sound assets needed.

---

## Packaging with PyInstaller

### PyInstaller Spec File (`tello_controller.spec`)
```python
# tello_controller.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('sounds/*.wav', 'sounds'),
        ('assets/*.png', 'assets'),
    ],
    hiddenimports=['djitellopy'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name='TelloController',
    icon='assets/icon.png',
    console=False,           # No terminal window
    onefile=True,            # Single .exe
)
```

### Build Commands
```bash
# Windows
pyinstaller --onefile --noconsole --add-data "sounds;sounds" --add-data "assets;assets" --name TelloController main.py

# macOS
pyinstaller --onefile --noconsole --add-data "sounds:sounds" --add-data "assets:assets" --name TelloController main.py
```

### Resource Path Helper
Since PyInstaller bundles assets into a temp directory, use this helper to resolve paths:
```python
import sys, os

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)
```
Use this for all sound and asset file loading.

---

## Error Handling Strategy

| Scenario | Behavior |
|----------|----------|
| No Xbox controller at startup | Show "Connect controller" message in UI. Scan every 1s. |
| Controller disconnects mid-flight | Send RC(0,0,0,0) → drone hovers. Alert in UI. Auto-scan for reconnect. |
| Tello not found on Wi-Fi | Show "Check Wi-Fi" message. Retry connection every 3s up to 5 times. |
| Tello disconnects mid-flight | Tello auto-lands after ~15s with no commands. Alert in UI. Auto-reconnect. |
| djitellopy raises exception | Catch all exceptions from SDK calls. Log to console. Never crash the app. |
| Pygame event error | Catch and ignore. Main loop must never exit unexpectedly. |
| Sound file missing | Skip sound playback, log warning. App runs silently. |
| Battery hits 0% during flight | Tello handles this internally (forced landing). UI shows critical alert. |

---

## Testing Checklist

### Phase 1: Unit / Component Tests (no drone needed)
- [ ] Controller detection: plug in Xbox controller, verify `ControllerState` populates
- [ ] Axis deadzone: small stick movements produce 0 output
- [ ] Axis sensitivity: full stick deflection produces ±SPEED_MAX output
- [ ] Button edge detection: press A, verify `a_pressed` is True for exactly 1 frame
- [ ] Takeoff hold timer: hold A for 0.5s → no takeoff. Hold A for 1.0s → takeoff triggers
- [ ] UI renders without drone connected (all telemetry shows "—")
- [ ] Controller disconnect/reconnect cycle works
- [ ] Sound playback works (or graceful fallback if files missing)
- [ ] PyInstaller build produces working .exe / .app

### Phase 2: Integration Tests (drone required)
- [ ] Connect to Tello, verify battery reading appears in UI
- [ ] Takeoff via A button, hover stable
- [ ] All four axes control drone movement correctly
- [ ] B button lands drone
- [ ] X button triggers emergency stop
- [ ] Speed modes: LB switches to slow, RB switches to fast, feel the difference
- [ ] Y button flip works (with battery/height guards)
- [ ] Unplug controller mid-hover → drone holds position
- [ ] Replug controller → control resumes
- [ ] Disconnect Wi-Fi mid-hover → drone auto-lands after ~15s
- [ ] Reconnect Wi-Fi → app reconnects to drone

### Phase 3: Stress Tests
- [ ] Fly full battery (13 min) — app remains responsive throughout
- [ ] Rapid stick movements for 2 min — no lag or command queue buildup
- [ ] 10 consecutive takeoff/land cycles — all succeed
- [ ] Run packaged .exe on clean Windows machine (no Python installed)

---

## Competition Day Startup Procedure

1. Power on laptop
2. Plug Xbox controller into USB
3. Power on Tello (side button → yellow blink)
4. Connect laptop Wi-Fi to `TELLO-XXXXXX`
5. Double-click `TelloController.exe`
6. Verify UI shows: ✅ CONNECTED, ✅ Controller OK, Battery > 80%
7. Hold A for 1 second → takeoff
8. Fly the course
9. Press B to land
10. If anything goes wrong → press X for emergency stop

---

## Future Enhancements (Post-Competition, Out of Scope)

- Optional video feed toggle (enable only when iPad crash issue is resolved)
- Flight path recording and replay
- Keyboard control as fallback input
- Multi-controller support (pilot + camera operator)
- Telemetry logging to CSV for post-flight analysis
- Custom button mapping UI
- Tello EDU support (mission pads, multi-drone swarm)
