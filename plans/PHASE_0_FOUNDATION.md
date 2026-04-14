# Phase 0: Project Foundation

## Goal

Create the repo structure, configuration model, asset-loading helpers, and a minimal runnable shell so every later phase can plug into stable interfaces.

## Outcome

At the end of this phase, the app should launch a pygame window, run a 60 FPS loop, show placeholder UI state, and exit cleanly even if no controller or drone is present.

## Exit Criteria

- Project structure matches the spec closely enough to build against.
- `main.py` launches a window and cleanly shuts down.
- `config.py` contains all constants needed by later phases.
- A shared resource-path helper exists for development and PyInstaller builds.
- Placeholder implementations exist for controller, drone, UI, and sound hooks.
- Requirements and build scripts are present, even if packaging is not yet verified.
- Automated tests exist for the phase foundation pieces and pass locally.

## Detailed Tasks

### Workstream A: Repository and Runtime Skeleton

- Create the top-level application files:
  - `main.py`
  - `controller.py`
  - `drone.py`
  - `ui.py`
  - `config.py`
  - `requirements.txt`
  - `README.md`
  - `build.bat`
  - `build.sh`
  - `tello_controller.spec`
- Create asset directories:
  - `sounds/`
  - `assets/`
- Add a minimal app bootstrap in `main.py`:
  - initialize pygame
  - initialize mixer with failure tolerance
  - create display and clock
  - instantiate placeholder `Controller`, `Drone`, and `UI`
  - run a basic main loop at configured FPS
  - handle quit and cleanup

### Workstream B: Shared Configuration and Data Contracts

- Implement `config.py` with constants from the spec.
- Define initial dataclasses and enums that later phases will share:
  - `ControllerState`
  - `TelemetryData`
  - speed mode enum or constants
  - optional alert type enum
- Decide and document module interfaces now so later implementation can proceed in parallel:
  - `Controller.update() -> ControllerState`
  - `Drone.connect()`, `Drone.disconnect()`, `Drone.send_rc(...)`
  - `Drone.get_telemetry() -> TelemetryData`
  - `UI.draw(...)`

### Workstream C: Resource and Asset Strategy

- Add a `resource_path()` helper for PyInstaller-safe file loading.
- Create a small sound-loading utility or helper function that:
  - attempts to load a sound
  - returns `None` on failure
  - logs a warning instead of crashing
- Add placeholder notes in README for required sound and icon assets.
- Decide whether to check in placeholder silent assets or generate them later in Phase 4.

### Workstream D: Documentation and Dev Setup

- Add `requirements.txt` with the base dependencies from the spec.
- Add test dependencies and a test runner strategy, preferably `pytest`.
- Write a short `README.md` covering:
  - local setup
  - how to run the app
  - how to run automated tests
  - expected hardware
  - current phase limitations
- Add non-final `build.bat`, `build.sh`, and `tello_controller.spec` placeholders aligned to the intended packaging approach.

### Workstream E: Automated Test Foundation

- Create a `tests/` directory and initial test file layout.
- Add automated tests for:
  - config import and default constants
  - dataclass construction and default-state validity
  - `resource_path()` behavior in normal development mode
  - missing-sound fallback behavior
  - app bootstrap startup/shutdown path using mocks or a headless-friendly setup
- If pygame display initialization is hard to test directly, isolate startup helpers so they can be tested without opening a real window.
- Add a single documented command to run the automated tests.

## Parallelization Plan

- Agent 1: app skeleton and main loop
- Agent 2: config module, dataclasses, shared interfaces
- Agent 3: README, requirements, build scripts, spec file
- Agent 4: resource-path helper and sound-loading fallback
- Agent 5: test harness, first pytest suite, and test-run documentation

## Handoff Artifacts Required Before Phase 1

- Stable dataclass definitions committed
- `main.py` event loop established
- placeholder UI drawing something visible
- placeholder controller and drone classes importable without hardware

## Automated Tests Required

- Add tests that verify the app modules import without hardware attached.
- Add tests for `resource_path()` and missing-asset fallback behavior.
- Add tests that validate dataclass defaults and core config values.
- Add a startup/shutdown smoke test around the main app shell using mocks or headless mode.
- Record the exact command to run this phase's automated tests in the README.

## Manual Test Checklist

### Smoke Tests

- Launch the app from source and confirm a window opens.
- Close the window using the title-bar close button and confirm a clean exit.
- Run the app with no Xbox controller connected and confirm no crash.
- Run the app with no drone/Wi-Fi connection and confirm no crash.

### Component Checks

- Verify `resource_path()` resolves correctly in a normal dev run.
- Temporarily point a sound loader at a missing file and confirm the app continues.
- Confirm placeholder telemetry and controller state render without exceptions.

### Completion Gate

- Do not move to Phase 1 until the project can be launched repeatedly with consistent startup and shutdown behavior and the Phase 0 automated tests are passing.
