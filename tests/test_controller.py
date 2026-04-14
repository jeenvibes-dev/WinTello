from __future__ import annotations

from dataclasses import dataclass, field

import config
from controller import Controller, process_axis, read_hat, speed_mode_max, trigger_pressed


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class FakeJoystick:
    axes: dict = field(default_factory=dict)
    buttons: dict = field(default_factory=dict)
    hats: dict = field(default_factory=dict)
    initialized: bool = False

    def init(self) -> None:
        self.initialized = True

    def get_init(self) -> bool:
        return self.initialized

    def get_axis(self, index: int) -> float:
        return self.axes.get(index, 0.0)

    def get_numaxes(self) -> int:
        if not self.axes:
            return 6
        return max(self.axes.keys()) + 1

    def get_button(self, index: int) -> int:
        return int(self.buttons.get(index, False))

    def get_hat(self, index: int):
        return self.hats.get(index, (0, 0))

    def get_name(self) -> str:
        return "Fake Controller"


class FakeJoystickModule:
    def __init__(self) -> None:
        self.devices = []

    def init(self) -> None:
        return None

    def get_count(self) -> int:
        return len(self.devices)

    def Joystick(self, index: int) -> FakeJoystick:
        return self.devices[index]


class FakeEventModule:
    def pump(self) -> None:
        return None


class FakePygame:
    def __init__(self, joystick_module: FakeJoystickModule) -> None:
        self.joystick = joystick_module
        self.event = FakeEventModule()


def test_process_axis_deadzone_returns_zero():
    assert process_axis(0.05, config.SPEED_NORMAL) == 0
    assert process_axis(-0.10, config.SPEED_NORMAL) == 0


def test_process_axis_scales_to_speed_limit():
    assert process_axis(1.0, config.SPEED_FAST) == config.SPEED_FAST
    assert process_axis(-1.0, config.SPEED_SLOW) == -config.SPEED_SLOW


def test_process_axis_inverts_y_values():
    assert process_axis(1.0, config.SPEED_NORMAL, invert=True) == -config.SPEED_NORMAL
    assert process_axis(-1.0, config.SPEED_NORMAL, invert=True) == config.SPEED_NORMAL


def test_controller_detects_hotplug_after_scan_interval():
    clock = FakeClock()
    joystick_module = FakeJoystickModule()
    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)

    first_state = controller.update()
    assert first_state.connected is False

    joystick = FakeJoystick()
    joystick_module.devices = [joystick]
    clock.advance(1.1)

    connected_state = controller.update()
    assert connected_state.connected is True
    assert joystick.initialized is True


def test_trigger_pressed_normalizes_trigger_axes():
    assert trigger_pressed(-1.0) is False
    assert trigger_pressed(0.0) is False
    assert trigger_pressed(1.0) is True


def test_read_hat_defaults_to_center():
    joystick = FakeJoystick()
    assert read_hat(joystick) == (0, 0)


def test_takeoff_land_combo_fires_once():
    clock = FakeClock()
    joystick = FakeJoystick(axes={5: 1.0}, buttons={3: True})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]
    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)

    first_state = controller.update()
    second_state = controller.update()

    assert first_state.takeoff_land_pressed is True
    assert first_state.r2_pressed is True
    assert second_state.takeoff_land_pressed is False


def test_flip_combo_reads_dpad_direction_with_l2():
    clock = FakeClock()
    joystick = FakeJoystick(axes={4: 1.0}, hats={0: (0, 1)})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]
    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)

    state = controller.update()
    second_state = controller.update()
    assert state.flip_direction == "forward"
    assert state.l2_pressed is True
    assert state.dpad_y == 1
    assert second_state.flip_direction is None


def test_flip_combo_reports_left_and_right():
    clock = FakeClock()
    joystick = FakeJoystick(axes={4: 1.0}, hats={0: (-1, 0)})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]
    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)

    left_state = controller.update()
    assert left_state.flip_direction == "left"

    joystick.hats[0] = (1, 0)
    right_state = controller.update()
    assert right_state.flip_direction == "right"


def test_disconnect_returns_neutral_state():
    clock = FakeClock()
    joystick = FakeJoystick(axes={0: 0.0, 2: 1.0})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]
    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)

    joystick.axes[0] = 1.0
    connected_state = controller.update()
    assert connected_state.connected is True
    assert connected_state.left_x == config.SPEED_NORMAL

    joystick_module.devices = []
    clock.advance(1.1)
    disconnected_state = controller.update()

    assert disconnected_state.connected is False
    assert disconnected_state.left_x == 0.0
    assert disconnected_state.right_y == 0.0


def test_controller_calibrates_neutral_axis_offsets():
    clock = FakeClock()
    joystick = FakeJoystick(axes={3: -0.4})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]

    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)
    neutral_state = controller.update()
    assert neutral_state.right_y == 0

    joystick.axes[3] = 0.6
    moved_state = controller.update()
    assert moved_state.right_y != 0


def test_l2_suppresses_backward_motion_bleed():
    clock = FakeClock()
    joystick = FakeJoystick(axes={3: 0.7, 4: 1.0})
    joystick_module = FakeJoystickModule()
    joystick_module.devices = [joystick]

    controller = Controller(pygame_module=FakePygame(joystick_module), time_fn=clock)
    state = controller.update()
    assert state.l2_pressed is True
    assert state.right_y == 0
    assert state.controller_name == "Fake Controller"
