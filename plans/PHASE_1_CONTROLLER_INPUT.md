# Phase 1: Controller Input Layer

## Goal

Build and validate the Xbox controller subsystem independently from the drone so joystick processing, takeoff hold timing, speed modes, and reconnect behavior are already trustworthy before flight testing begins.

## Outcome

At the end of this phase, the app should show live controller state in the window and expose a reliable `ControllerState` object every frame.

## Exit Criteria

- Xbox controller detection works at startup and during hot-plug.
- Axis processing follows the spec pipeline exactly.
- Button edge detection works without repeated triggers.
- Takeoff hold logic works with cancel-on-release behavior.
- Speed mode selection can be exercised from LB/RB.
- Disconnect behavior forces neutral RC output in the published state.
- Automated tests cover the controller processing rules and pass locally.

## Detailed Tasks

### Workstream A: Joystick Discovery and Lifecycle

- Implement joystick scanning using pygame joystick APIs.
- Detect the first connected Xbox-compatible controller.
- Store connected/disconnected state in the controller module.
- Re-scan every second if no controller is present.
- Handle disconnects mid-session without crashing:
  - mark `connected = False`
  - clear live inputs to zero
  - preserve enough state for reconnect recovery

### Workstream B: Axis Mapping and Processing

- Implement a mapping layer for:
  - left stick X and Y
  - right stick X and Y
- Add axis-index constants in one place to simplify later calibration if needed.
- Implement the full processing pipeline:
  - raw read
  - deadzone
  - remap surviving range
  - sensitivity curve
  - speed-mode scaling
  - clamp to `-100..100`
  - invert Y axes to match Tello convention
- Return processed values in the `ControllerState` dataclass.

### Workstream C: Button Logic

- Implement frame-based button edge detection for:
  - A
  - B
  - X
  - Y
  - LB
  - RB
  - Start
- Implement A-button hold timing:
  - start timer on press
  - cancel on early release
  - trigger once when hold duration reaches threshold
- Expose hold-progress info if helpful for UI messaging.

### Workstream D: State Publishing and Debug Visibility

- Make `Controller.update()` produce a fully-populated state object every frame.
- Add controller labels or debug values the UI can display now:
  - axis values
  - connection state
  - takeoff hold progress
  - speed mode
- Ensure state remains stable when pygame emits unusual or transient events.

### Workstream E: Automated Controller Tests

- Add unit tests for axis deadzone, remapping, sensitivity curves, clamping, and Y-axis inversion.
- Add tests for speed-mode scaling across slow, normal, and fast.
- Add tests for button edge detection so press events fire once.
- Add tests for A-button hold timing, including early release cancellation and single-trigger behavior.
- Add tests for disconnected-controller behavior to ensure the published state returns neutral values.
- Use pygame wrappers, dependency injection, or mocks so the tests do not require a physical controller.

## Parallelization Plan

- Agent 1: joystick discovery, reconnect scan, lifecycle handling
- Agent 2: axis mapping, deadzone/remap/curve processing
- Agent 3: button edge detection and takeoff hold timer
- Agent 4: controller debug rendering contract and integration hooks for UI
- Agent 5: controller unit tests and fake-input helpers

## Integration Notes For The Next Phase

- `ControllerState` should already include everything `Drone` and `UI` need.
- Avoid direct drone calls from the controller module.
- Keep speed mode as controller-owned state unless architecture clearly favors a shared app state object.

## Automated Tests Required

- Add unit tests for each axis-processing step and final output range.
- Add edge-detection tests for all mapped buttons.
- Add takeoff-hold timing tests with mocked time progression.
- Add tests for hot-plug scanning logic using mocked joystick enumeration.
- Ensure this suite runs without the drone and without a real controller attached.

## Manual Test Checklist

### Manual No-Drone Tests

- Plug in the controller before app launch and confirm it is detected.
- Start the app with no controller, then connect the controller and confirm detection within one second.
- Disconnect the controller while the app is running and confirm state drops to disconnected without crashing.
- Reconnect and confirm live axis updates resume.

### Axis and Button Verification

- Move each stick slightly inside the deadzone and confirm values stay at zero.
- Move each stick to full travel and confirm outputs reach the configured max for the active speed mode.
- Switch between slow, normal, and fast modes and confirm scaling changes visibly.
- Press B, X, Y, LB, RB, and Start and confirm each press-edge appears once rather than every frame.

### Takeoff Hold Tests

- Tap A quickly and confirm no takeoff trigger.
- Hold A for roughly half the threshold and release; confirm cancel behavior.
- Hold A through the full threshold and confirm one trigger only.
- Continue holding A after trigger and confirm it does not retrigger repeatedly.

### Completion Gate

- Do not start real drone command work until controller state is stable for at least 10 minutes of repeated plugging, unplugging, and stick/button use, and the controller automated tests are passing.
