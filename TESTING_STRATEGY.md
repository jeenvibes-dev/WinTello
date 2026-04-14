# Tello Controller Testing Strategy

## Goal

Keep the project shippable at all times by requiring fast automated tests in every phase and pairing them with short manual checks for hardware behavior that cannot be fully simulated.

## Testing Layers

### 1. Fast Automated Unit Tests

- Run on every phase before work is considered complete.
- Cover pure logic first:
  - config values
  - dataclasses and state defaults
  - controller input processing
  - safety-rule decisions
  - alert selection
  - resource and asset loading fallbacks
- Should not require a real drone, real controller, or real audio device.

### 2. Automated Component Tests

- Exercise module boundaries with mocks or fake backends.
- Examples:
  - fake pygame joystick enumeration
  - fake Tello backend
  - main-loop action dispatch with mocked controller/drone/UI objects
  - shutdown behavior when airborne versus grounded
- These should still run locally in seconds.

### 3. Manual Hardware Checks

- Done at the end of each phase.
- Validate real controller hot-plug, real drone connection, and real flight behavior.
- Keep the checklist short and phase-specific so testing stays practical.

### 4. Packaged-Build Validation

- Run after packaging changes.
- Verify the packaged app launches and loads assets on a machine without Python installed.

## Framework and Conventions

- Use `pytest` as the default test runner.
- Keep tests in `tests/`.
- Name files `test_*.py`.
- Prefer deterministic tests over timing-sensitive sleeps.
- Use dependency injection, fakes, and mocking instead of real hardware.
- Extract logic into small helper functions when direct UI or hardware testing would be brittle.

## Headless and Environment Strategy

- Use a headless-friendly mode for pygame tests.
- Set `SDL_VIDEODRIVER=dummy` in tests when a real display is not needed.
- Treat sound playback as optional in tests by mocking mixer access or using missing-file fallback paths.
- Avoid requiring live Wi-Fi or a real Tello for automated runs.
- The project still requires the real `pygame` package to be installed; tests should not depend on a fake renderer fallback.

## Per-Phase Minimum Expectations

### Phase 0

- Imports and bootstrap path
- config and model defaults
- resource loading fallback
- headless app startup and shutdown

### Phase 1

- axis processing pipeline
- speed scaling
- button edge detection
- takeoff hold timing
- controller reconnect scan logic

### Phase 2

- connection retry policy
- telemetry state updates
- safety guards for commands
- fake backend integration

### Phase 3

- controller-to-action dispatch
- alert prioritization
- shutdown safety flow
- sound fallback
- UI presentation helpers

### Phase 4

- full regression suite
- packaging config checks
- regression tests for bugs found during rehearsal

## Commands

### Run the Full Automated Suite

```powershell
py -3.13 -m pytest
```

### Run One Phase's Tests

```powershell
py -3.13 -m pytest tests
```

## What Must Happen Before A Phase Is Done

1. New code for the phase is implemented.
2. Automated tests for that phase are added or updated.
3. `python -m pytest` passes locally.
4. The phase's manual checklist is run by a human.
5. Any bug found manually gets either:
   - fixed immediately with a regression test, or
   - logged explicitly before moving on.
