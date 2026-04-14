from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

import pygame

import config
from models import ControllerState


LEFT_X_AXIS = 0
LEFT_Y_AXIS = 1
RIGHT_X_AXIS = 2
RIGHT_Y_AXIS = 3
LEFT_TRIGGER_AXIS = 4
RIGHT_TRIGGER_AXIS = 5
TRIGGER_THRESHOLD = 0.75

A_BUTTON = 0
B_BUTTON = 1
X_BUTTON = 2
Y_BUTTON = 3
LB_BUTTON = 4
RB_BUTTON = 5
START_BUTTON = 7

BUTTON_NAME_TO_INDEX = {
    "a": A_BUTTON,
    "b": B_BUTTON,
    "x": X_BUTTON,
    "y": Y_BUTTON,
    "lb": LB_BUTTON,
    "rb": RB_BUTTON,
    "start": START_BUTTON,
}

DEFAULT_PREVIOUS_BUTTONS = {name: False for name in BUTTON_NAME_TO_INDEX}


class Controller:
    """Xbox controller input handling with hot-plug support."""

    def __init__(
        self,
        pygame_module: Any = pygame,
        time_fn=time.monotonic,
    ) -> None:
        self._pygame = pygame_module
        self._time_fn = time_fn
        self._joystick: Optional[Any] = None
        self._last_scan_time = 0.0
        self._speed_mode = "NORMAL"
        self._previous_buttons: Dict[str, bool] = dict(DEFAULT_PREVIOUS_BUTTONS)
        self._previous_takeoff_combo = False
        self._previous_flip_combo: Optional[str] = None
        self._axis_offsets: Dict[int, float] = {}
        self._state = self._disconnected_state()
        joystick_module = getattr(self._pygame, "joystick", None)
        if joystick_module is not None:
            try:
                joystick_module.init()
            except Exception:
                pass
        self._scan_for_controller(force=True)

    def update(self) -> ControllerState:
        self._pump_events()

        if not self._has_active_joystick():
            self._scan_for_controller()
            if not self._has_active_joystick():
                self._state = self._disconnected_state()
                return self._state

        try:
            return self._read_controller_state()
        except Exception:
            self._handle_disconnect()
            self._state = self._disconnected_state()
            return self._state

    def _pump_events(self) -> None:
        event_module = getattr(self._pygame, "event", None)
        if event_module is None:
            return
        pump = getattr(event_module, "pump", None)
        if pump is None:
            return
        try:
            pump()
        except Exception:
            pass

    def _scan_for_controller(self, force: bool = False) -> None:
        now = self._time_fn()
        if not force and (now - self._last_scan_time) < 1.0:
            return

        self._last_scan_time = now
        joystick_module = getattr(self._pygame, "joystick", None)
        if joystick_module is None:
            self._handle_disconnect()
            return

        count = joystick_module.get_count()
        if count <= 0:
            self._handle_disconnect()
            return

        joystick = joystick_module.Joystick(0)
        init = getattr(joystick, "init", None)
        if callable(init):
            init()
        self._joystick = joystick
        self._capture_axis_offsets()

    def _has_active_joystick(self) -> bool:
        if self._joystick is None:
            return False
        joystick_module = getattr(self._pygame, "joystick", None)
        if joystick_module is None or joystick_module.get_count() <= 0:
            return False
        get_init = getattr(self._joystick, "get_init", None)
        if callable(get_init):
            try:
                return bool(get_init())
            except Exception:
                return False
        return True

    def _read_controller_state(self) -> ControllerState:
        assert self._joystick is not None
        current_speed = speed_mode_max(self._speed_mode)

        raw_buttons = {
            name: bool(self._joystick.get_button(index))
            for name, index in BUTTON_NAME_TO_INDEX.items()
        }
        raw_axes = self._read_raw_axes()

        edges = {
            name: raw_buttons[name] and not self._previous_buttons[name]
            for name in BUTTON_NAME_TO_INDEX
        }

        dpad_x, dpad_y = read_hat(self._joystick)
        l2_pressed = trigger_pressed(axis_value(raw_axes, LEFT_TRIGGER_AXIS))
        r2_pressed = trigger_pressed(axis_value(raw_axes, RIGHT_TRIGGER_AXIS))
        takeoff_land_pressed = combo_pressed(r2_pressed, raw_buttons["y"], self._previous_takeoff_combo)
        flip_direction = combo_direction(l2_pressed, dpad_x, dpad_y, self._previous_flip_combo)
        right_y_value = process_axis(
            centered_axis_value(raw_axes, RIGHT_Y_AXIS, self._axis_offsets),
            current_speed,
            invert=True,
        )
        if l2_pressed:
            right_y_value = 0

        state = ControllerState(
            left_x=process_axis(centered_axis_value(raw_axes, LEFT_X_AXIS, self._axis_offsets), current_speed),
            left_y=process_axis(centered_axis_value(raw_axes, LEFT_Y_AXIS, self._axis_offsets), current_speed, invert=True),
            right_x=process_axis(centered_axis_value(raw_axes, RIGHT_X_AXIS, self._axis_offsets), current_speed),
            right_y=right_y_value,
            a_pressed=False,
            b_pressed=False,
            x_pressed=False,
            y_pressed=edges["y"],
            lb_pressed=False,
            rb_pressed=False,
            start_pressed=False,
            connected=True,
            speed_mode=self._speed_mode,
            takeoff_hold_progress=0.0,
            takeoff_ready=False,
            takeoff_land_pressed=takeoff_land_pressed,
            flip_direction=flip_direction,
            l2_pressed=l2_pressed,
            r2_pressed=r2_pressed,
            dpad_x=dpad_x,
            dpad_y=dpad_y,
            controller_name=joystick_name(self._joystick),
            raw_axes=tuple(round(value, 3) for value in raw_axes),
        )
        self._previous_buttons = raw_buttons
        self._previous_takeoff_combo = r2_pressed and raw_buttons["y"]
        self._previous_flip_combo = active_flip_direction(l2_pressed, dpad_x, dpad_y)
        self._state = state
        return state

    def _disconnected_state(self) -> ControllerState:
        return ControllerState(
            connected=False,
            speed_mode=self._speed_mode,
            takeoff_hold_progress=0.0,
            takeoff_ready=False,
        )

    def _handle_disconnect(self) -> None:
        self._joystick = None
        self._previous_buttons = dict(DEFAULT_PREVIOUS_BUTTONS)
        self._previous_takeoff_combo = False
        self._previous_flip_combo = None
        self._axis_offsets = {}

    def _read_raw_axes(self) -> list[float]:
        assert self._joystick is not None
        count = axis_count(self._joystick)
        values = []
        for index in range(count):
            try:
                values.append(float(self._joystick.get_axis(index)))
            except Exception:
                values.append(0.0)
        return values

    def _capture_axis_offsets(self) -> None:
        if self._joystick is None:
            self._axis_offsets = {}
            return
        raw_axes = self._read_raw_axes()
        self._axis_offsets = {
            LEFT_X_AXIS: axis_value(raw_axes, LEFT_X_AXIS),
            LEFT_Y_AXIS: axis_value(raw_axes, LEFT_Y_AXIS),
            RIGHT_X_AXIS: axis_value(raw_axes, RIGHT_X_AXIS),
            RIGHT_Y_AXIS: axis_value(raw_axes, RIGHT_Y_AXIS),
        }


def speed_mode_max(mode: str) -> int:
    if mode == "SLOW":
        return config.SPEED_SLOW
    if mode == "FAST":
        return config.SPEED_FAST
    return config.SPEED_NORMAL


def process_axis(raw_value: float, speed_limit: int, invert: bool = False) -> int:
    value = max(-1.0, min(1.0, raw_value))
    if abs(value) < config.DEADZONE:
        return 0

    sign = -1.0 if value < 0 else 1.0
    remapped = (abs(value) - config.DEADZONE) / (1.0 - config.DEADZONE)
    remapped = max(0.0, min(1.0, remapped))

    if config.SENSITIVITY_CURVE == "exponential":
        curved = math.pow(remapped, config.EXPONENTIAL_FACTOR)
    else:
        curved = remapped

    result = int(round(sign * curved * speed_limit))
    result = max(-100, min(100, result))
    if invert:
        result *= -1
    return result


def axis_count(joystick: Any) -> int:
    get_numaxes = getattr(joystick, "get_numaxes", None)
    if callable(get_numaxes):
        try:
            return int(get_numaxes())
        except Exception:
            return RIGHT_TRIGGER_AXIS + 1
    return RIGHT_TRIGGER_AXIS + 1


def axis_value(raw_axes: list[float], index: int) -> float:
    if 0 <= index < len(raw_axes):
        return raw_axes[index]
    return 0.0


def centered_axis_value(raw_axes: list[float], index: int, offsets: Dict[int, float]) -> float:
    return axis_value(raw_axes, index) - offsets.get(index, 0.0)


def trigger_pressed(raw_value: float) -> bool:
    normalized = (max(-1.0, min(1.0, raw_value)) + 1.0) / 2.0
    return normalized >= TRIGGER_THRESHOLD


def read_hat(joystick: Any) -> tuple[int, int]:
    get_hat = getattr(joystick, "get_hat", None)
    if callable(get_hat):
        try:
            x_value, y_value = get_hat(0)
            return int(x_value), int(y_value)
        except Exception:
            return 0, 0
    return 0, 0


def joystick_name(joystick: Any) -> str:
    get_name = getattr(joystick, "get_name", None)
    if callable(get_name):
        try:
            return str(get_name())
        except Exception:
            return ""
    return ""


def active_flip_direction(l2_pressed: bool, dpad_x: int, dpad_y: int) -> Optional[str]:
    if not l2_pressed:
        return None
    if dpad_y > 0:
        return "forward"
    if dpad_y < 0:
        return "back"
    if dpad_x < 0:
        return "left"
    if dpad_x > 0:
        return "right"
    return None


def combo_pressed(primary_active: bool, secondary_active: bool, previous_combo: bool) -> bool:
    combo_active = primary_active and secondary_active
    return combo_active and not previous_combo


def combo_direction(
    primary_active: bool,
    dpad_x: int,
    dpad_y: int,
    previous_direction: Optional[str],
) -> Optional[str]:
    direction = active_flip_direction(primary_active, dpad_x, dpad_y)
    if direction is None or direction == previous_direction:
        return None
    return direction
