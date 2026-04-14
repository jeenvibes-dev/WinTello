from __future__ import annotations

from dataclasses import dataclass

import main
from models import ControllerState, TelemetryData


@dataclass
class FakeSound:
    plays: int = 0

    def play(self) -> None:
        self.plays += 1


class FakeDrone:
    def __init__(self) -> None:
        self.manual_reconnect_called = 0
        self.takeoff_called = 0
        self.land_called = 0
        self.flip_called = 0
        self.sent_rc = []
        self._airborne = False

    def takeoff(self) -> bool:
        self.takeoff_called += 1
        self._airborne = True
        return True

    def land(self) -> bool:
        self.land_called += 1
        self._airborne = False
        return True

    def flip(self, direction=None) -> bool:
        self.flip_called += 1
        self.last_flip_direction = direction
        return True

    def send_rc(self, left_right: int, forward_back: int, up_down: int, yaw: int) -> None:
        self.sent_rc.append((left_right, forward_back, up_down, yaw))

    @property
    def is_airborne(self) -> bool:
        return self._airborne

    def disconnect(self) -> None:
        self._airborne = False
        self.disconnect_called = getattr(self, "disconnect_called", 0) + 1


def make_runtime() -> main.Runtime:
    return main.Runtime(
        screen=None,
        clock=None,
        controller=None,
        drone=FakeDrone(),
        ui=None,
        sounds={
            "connect": FakeSound(),
            "takeoff": FakeSound(),
            "land": FakeSound(),
            "low_battery": FakeSound(),
            "error": FakeSound(),
        },
        button_flash_until={},
        low_battery_sound_at=0.0,
        last_connection_state=None,
        last_low_battery_state=False,
        last_error_state=False,
        action_threads={},
        action_lock=__import__("threading").Lock(),
        busy_action=None,
    )


def test_determine_alert_priority_prefers_emergency():
    controller_state = ControllerState(connected=True)
    telemetry = TelemetryData(connected=True, battery=5, emergency_active=True)

    text, level = main.determine_alert(controller_state, telemetry)
    assert text == "EMERGENCY STOP ACTIVATED"
    assert level == "danger"


def test_determine_alert_low_battery_warning():
    controller_state = ControllerState(connected=True)
    telemetry = TelemetryData(connected=True, battery=15)

    text, level = main.determine_alert(controller_state, telemetry)
    assert text == "LOW BATTERY - LAND SOON"
    assert level == "warning"


def test_handle_controller_actions_dispatches_buttons_and_rc():
    runtime = make_runtime()
    controller_state = ControllerState(
        connected=True,
        right_x=10,
        right_y=-20,
        left_y=30,
        left_x=-40,
        takeoff_land_pressed=True,
        flip_direction="left",
        r2_pressed=True,
        l2_pressed=True,
    )

    main.handle_controller_actions(runtime, controller_state)

    assert runtime.drone.takeoff_called == 1
    assert runtime.drone.flip_called == 1
    assert runtime.drone.last_flip_direction == "left"
    assert runtime.drone.sent_rc[-1] == (10, -20, 30, -40)


def test_rc_mapping_keeps_yaw_on_left_stick_x():
    runtime = make_runtime()
    controller_state = ControllerState(
        connected=True,
        left_x=55,
        left_y=22,
        right_x=-33,
        right_y=44,
    )

    main.handle_controller_actions(runtime, controller_state)

    left_right, forward_back, up_down, yaw = runtime.drone.sent_rc[-1]
    assert left_right == -33
    assert forward_back == 44
    assert up_down == 22
    assert yaw == 55


def test_handle_controller_actions_sends_neutral_when_controller_missing():
    runtime = make_runtime()
    controller_state = ControllerState(connected=False)

    main.handle_controller_actions(runtime, controller_state)
    assert runtime.drone.sent_rc[-1] == (0, 0, 0, 0)


def test_build_ui_state_exposes_takeoff_prompt_and_button_highlight():
    runtime = make_runtime()
    runtime.button_flash_until["r2_y"] = 9999999999.0
    controller_state = ControllerState(connected=True, r2_pressed=True)
    telemetry = TelemetryData(connected=True)

    ui_state = main.build_ui_state(runtime, controller_state, telemetry)
    assert ui_state.takeoff_prompt == "Press Y while holding R2 to take off or land"
    assert ui_state.highlighted_buttons["r2_y"] is True
    assert ui_state.connection_label == "CONNECTED"
    assert ui_state.busy_text is None


def test_takeoff_land_combo_lands_when_drone_is_airborne():
    runtime = make_runtime()
    runtime.drone._airborne = True
    controller_state = ControllerState(connected=True, takeoff_land_pressed=True)

    main.handle_controller_actions(runtime, controller_state)
    assert runtime.drone.land_called == 1


def test_start_action_marks_runtime_busy_then_clears():
    runtime = make_runtime()

    def action():
        return True

    started = main.start_action(runtime, "takeoff", action, runtime.sounds["takeoff"])
    assert started is True
    for thread in list(runtime.action_threads.values()):
        thread.join(timeout=1.0)
    assert runtime.busy_action is None
    assert runtime.sounds["takeoff"].plays == 1


def test_maybe_play_sounds_handles_connection_and_low_battery_transitions():
    runtime = make_runtime()
    telemetry = TelemetryData(connected=False, battery=50)
    main.maybe_play_sounds(runtime, telemetry)

    telemetry.connected = True
    main.maybe_play_sounds(runtime, telemetry)
    assert runtime.sounds["connect"].plays == 1

    telemetry.battery = 15
    main.maybe_play_sounds(runtime, telemetry)
    assert runtime.sounds["low_battery"].plays == 1


def test_play_sound_ignores_missing_sound():
    main.play_sound(None)


def test_shutdown_lands_before_disconnect_when_airborne():
    runtime = make_runtime()
    runtime.drone._airborne = True

    main.shutdown(runtime)

    assert runtime.drone.land_called == 1
    assert runtime.drone.disconnect_called == 1
