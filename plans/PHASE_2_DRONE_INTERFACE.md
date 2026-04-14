# Phase 2: Drone Interface and Telemetry

## Goal

Implement a fault-tolerant Tello wrapper that isolates `djitellopy`, enforces safety rules, and can be tested first with a fake backend and then against the real drone.

## Outcome

At the end of this phase, the app should be able to connect to the Tello, poll telemetry in the background, send safe RC commands, and recover from common failures without crashing the UI loop.

## Exit Criteria

- Drone connection and reconnect logic follow the spec.
- Telemetry polling runs on a background thread at the configured interval.
- SDK exceptions are caught and converted into app state rather than crashes.
- Safety gates exist for takeoff, land, flip, and emergency behavior.
- Neutral RC is sent whenever controller or drone state is unsafe.
- Manual retry via Start button can be wired in cleanly.
- Automated tests cover safety rules, reconnect behavior, and telemetry-state transitions.

## Detailed Tasks

### Workstream A: Drone Wrapper and Connection Lifecycle

- Create a `Drone` class that owns:
  - `djitellopy.Tello` instance
  - connection state
  - airborne state
  - retry counters and timing
- Implement startup connection flow:
  - connect once on app startup
  - retry every configured interval
  - stop auto-retry after max failures
- Implement manual reconnect entry point for the Start button.
- Add clean disconnect and `end()` handling for app shutdown.

### Workstream B: Telemetry Thread and Shared State

- Implement a thread-safe telemetry store backed by `TelemetryData`.
- Start a polling thread only after a successful connection.
- Poll:
  - battery
  - height
  - temperature
  - flight time
- Derive or store:
  - `connected`
  - `airborne`
  - signal strength state if feasible
- On telemetry failure:
  - mark disconnected
  - stop trusting stale values
  - trigger reconnect path

### Workstream C: Command Layer and Safety Guards

- Implement `send_rc(left_right, forward_back, up_down, yaw)`.
- Add a guard that sends `(0, 0, 0, 0)` if:
  - controller disconnected
  - drone disconnected
  - app state is otherwise unsafe
- Implement:
  - `takeoff()`
  - `land()`
  - `emergency()`
  - `flip(direction)`
- Enforce spec rules:
  - takeoff only if connected, grounded, battery above minimum
  - land only if airborne
  - flip only if airborne, battery high enough, height high enough
  - emergency always allowed

### Workstream D: Test Double and Logging

- Create a fake drone backend interface or adapter for development.
- Make it easy to switch between fake and real backends for component testing.
- Add concise console logging for:
  - connect attempts
  - reconnect attempts
  - command failures
  - telemetry failures
- Keep logs readable enough to support field debugging during rehearsals.

### Workstream E: Automated Drone Tests

- Add unit tests around the drone wrapper using the fake backend.
- Add tests for:
  - initial connection success and failure
  - retry timing policy
  - retry exhaustion behavior
  - telemetry updates and exception handling
  - safety guards for takeoff, land, emergency, and flip
  - neutral RC fallback when controller or drone state is unsafe
- Mock timing and threading boundaries where needed so tests stay fast and deterministic.

## Parallelization Plan

- Agent 1: connection lifecycle and reconnect policy
- Agent 2: telemetry thread, thread-safe state, stale-data handling
- Agent 3: RC command methods and safety guards
- Agent 4: fake backend, backend abstraction, and logging support
- Agent 5: automated tests for wrapper behavior and fake-backend scenarios

## Integration Notes For The Next Phase

- UI should not talk to `djitellopy` directly.
- Main loop should consume telemetry snapshots, not mutable internals.
- Surface enough status to support alerts:
  - disconnected
  - retrying
  - retry exhausted
  - low battery
  - emergency event active

## Automated Tests Required

- Add fake-backend unit tests for connection, telemetry, and command behavior.
- Add tests for telemetry exceptions and reconnect-state transitions.
- Add tests that blocked actions do not call the backend when safety rules fail.
- Add tests that emergency remains callable regardless of airborne state.
- Keep the suite runnable without Wi-Fi and without the real drone.

## Manual Test Checklist

### Fake-Backend Tests

- Run the app against a fake drone backend and confirm telemetry values render.
- Simulate connection failure and confirm retry behavior matches configured timing.
- Simulate telemetry exceptions and confirm the app stays alive while state changes to disconnected.
- Simulate invalid flip conditions and confirm flip is blocked.

### Real-Drone Bench Tests

- Connect to Tello Wi-Fi and launch the app; confirm initial connection succeeds.
- Verify battery appears correctly in the app.
- Confirm manual Start-button retry works after a forced disconnect.
- With props off or in a safe bench setup, verify command methods can be invoked without crashes.

### Safe Flight-Prep Tests

- Confirm `takeoff()` is blocked when battery is too low.
- Confirm `land()` is ignored when already grounded.
- Confirm `send_rc(0,0,0,0)` is issued when controller state is disconnected.
- Force a Wi-Fi disconnect and confirm the app transitions to disconnected/retrying instead of hanging.

### Completion Gate

- Do not move to Phase 3 until the drone wrapper can survive repeated connect/disconnect cycles and telemetry failures without terminating the app and the Phase 2 automated tests are passing.
