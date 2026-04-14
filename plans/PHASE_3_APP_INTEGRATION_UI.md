# Phase 3: Main Loop and Pygame Dashboard

## Goal

Wire the controller and drone layers into the full application loop, implement the dashboard UI from the spec, and validate the app end to end before packaging.

## Outcome

At the end of this phase, the desktop app should feel feature-complete from a user perspective: live controller visualization, telemetry display, status alerts, button legends, sound cues, and safe shutdown behavior.

## Exit Criteria

- Main loop integrates controller, drone, UI, and sound cleanly at 60 FPS.
- UI layout matches the spec closely enough for competition use.
- Alerts and status indicators respond to real state transitions.
- App-close safety behavior lands the drone if airborne.
- Missing assets do not crash the app.
- Automated tests cover UI state selection, event mapping, and integrated app behavior that can be tested without real hardware.

## Detailed Tasks

### Workstream A: Main Loop Orchestration

- Flesh out `main.py` into the real orchestration layer:
  - poll pygame events
  - update controller
  - map controller state to drone actions
  - poll or read telemetry snapshot
  - draw UI
  - tick clock
- Implement event-to-action mapping:
  - A hold trigger -> takeoff
  - B -> land
  - X -> emergency
  - Y -> flip
  - LB/RB -> speed changes
  - Start -> reconnect or refresh telemetry
- On shutdown:
  - if airborne, land first
  - wait briefly for completion
  - disconnect drone
  - quit pygame cleanly

### Workstream B: Dashboard Rendering

- Implement the top status bar with title and connection pill.
- Implement the left telemetry/status panel:
  - battery bar with thresholds
  - height in meters
  - temperature
  - flight time
  - speed mode
- Implement the right controller visual panel:
  - left stick visual
  - right stick visual
  - labels
  - numeric axis values
- Implement the bottom legend bar with temporary button highlights.

### Workstream C: Alert and Sound System

- Implement alert selection and prioritization logic for:
  - low battery
  - critical battery
  - controller disconnected
  - drone disconnected
  - emergency active
  - optional takeoff-hold prompt
- Add pulsing or flashing behavior where specified.
- Play sounds on:
  - connection success
  - takeoff
  - land
  - low battery repeating interval
  - disconnect/error
- Ensure absent sound files do not break the app.

### Workstream D: Performance and Resilience Pass

- Make sure UI redraws remain responsive while telemetry polling is active.
- Confirm the app does not freeze on SDK call failures.
- Add lightweight protections around pygame event handling so transient errors do not kill the main loop.
- Check for command spam or unnecessary duplicate sound/alert triggers.

### Workstream E: Automated Integration and UI Tests

- Add tests for alert selection and prioritization logic.
- Add tests for button-to-action mapping in the main loop using mocked controller and drone objects.
- Add tests for shutdown safety behavior when the drone is airborne versus grounded.
- Add tests for sound fallback so missing files do not crash the integrated app.
- Add rendering-oriented tests where practical by checking draw-call decisions or extracted presentation helpers instead of pixel-perfect snapshots.

## Parallelization Plan

- Agent 1: main loop orchestration and action wiring
- Agent 2: dashboard layout and rendering primitives
- Agent 3: alert state machine and sound events
- Agent 4: performance/resilience pass and edge-case handling
- Agent 5: integration tests for action wiring, alert logic, and shutdown behavior

## Integration Notes For The Next Phase

- Keep PyInstaller path handling in place for all assets.
- Avoid hard-coding dev-only paths in UI or sound code.
- Leave small seams for packaging-time inclusion of generated assets if needed.

## Automated Tests Required

- Add tests for alert-priority logic and timing-based alert clearing.
- Add tests for button action dispatch from controller state to drone methods.
- Add tests for speed-mode UI state and highlight behavior if these are represented in testable helpers.
- Add tests for app-close flow to confirm land-then-disconnect sequencing.
- Keep this suite mostly hardware-free by relying on mocks and fake state snapshots.

## Manual Test Checklist

### Integrated Desktop Tests

- Launch the full app and confirm all panels render.
- Run with no drone and no controller; confirm the UI still shows meaningful status.
- Connect only the controller and confirm live stick visualization updates.
- Connect only the drone and confirm telemetry fields populate.

### Functional Tests

- Verify each mapped button performs the intended action exactly once.
- Confirm speed-mode label and highlight update immediately when LB/RB are pressed.
- Trigger low-battery and disconnect alert states through simulated or forced values and confirm the correct alert appears.
- Confirm emergency alert persists for the intended short duration and then clears.

### Safe Flight Tests

- Perform a short takeoff-hover-land cycle and confirm:
  - hold-to-takeoff works
  - telemetry updates during hover
  - B lands cleanly
- Move each axis one at a time and confirm direction mapping matches the spec.
- Unplug the controller mid-hover and confirm the app sends neutral control and the drone stabilizes.

### Completion Gate

- Do not move to packaging until the integrated app has passed at least one short real-flight session without crashes or confusing UI state and the Phase 3 automated tests are passing.
