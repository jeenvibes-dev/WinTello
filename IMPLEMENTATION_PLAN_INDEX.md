# Tello Controller Implementation Plan

This plan breaks the spec into buildable phases so the app can be implemented and tested incrementally in one working session. Each phase is intentionally self-contained enough that Codex can be directed to complete it separately, while still producing artifacts that feed cleanly into the next phase.

## Recommended Build Order

1. Phase 0: Project Foundation
2. Phase 1: Controller Input Layer
3. Phase 2: Drone Interface and Telemetry
4. Phase 3: Main Loop and Pygame Dashboard
5. Phase 4: Packaging, Flight Validation, and Competition Readiness

## Why This Split Works

- It gets a runnable app skeleton in place before feature work starts.
- It lets the controller path be validated without the drone.
- It keeps drone-risky work isolated behind a wrapper with test doubles.
- It delays packaging until the app is already behaving correctly.
- It creates multiple opportunities to test on real hardware before the final build.

## Testing Policy

- Every phase must add or update automated tests before the phase is considered complete.
- Automated tests should be runnable locally on demand and suitable for CI later.
- Manual test steps must also be written at the end of each phase so you can verify hardware behavior yourself.
- Prefer fast unit and component tests first, then hardware-assisted manual checks second.

## Phase Files

- [PHASE_0_FOUNDATION.md](C:\Users\aksha\Documents\New project\TelloPy\plans\PHASE_0_FOUNDATION.md)
- [PHASE_1_CONTROLLER_INPUT.md](C:\Users\aksha\Documents\New project\TelloPy\plans\PHASE_1_CONTROLLER_INPUT.md)
- [PHASE_2_DRONE_INTERFACE.md](C:\Users\aksha\Documents\New project\TelloPy\plans\PHASE_2_DRONE_INTERFACE.md)
- [PHASE_3_APP_INTEGRATION_UI.md](C:\Users\aksha\Documents\New project\TelloPy\plans\PHASE_3_APP_INTEGRATION_UI.md)
- [PHASE_4_PACKAGING_AND_VALIDATION.md](C:\Users\aksha\Documents\New project\TelloPy\plans\PHASE_4_PACKAGING_AND_VALIDATION.md)

## Suggested Teaming Pattern For Codex

- Give one phase file at a time to a main Codex agent.
- Within a phase, parallelize by workstream rather than by file alone.
- Merge and test at the end of each phase before moving on.
- Do not start real-flight tests until Phase 2 exit criteria are met.

## Global Definition of Done

- App launches without crashing when controller or drone are absent.
- Controller input, speed modes, hold-to-takeoff logic, and reconnect flows work.
- Drone wrapper prevents unsafe commands and tolerates SDK/network failures.
- UI clearly communicates controller/drone state and telemetry.
- Packaged executable launches on a Windows machine without Python installed.
- Each implemented phase leaves behind passing automated tests plus a manual verification checklist.
