from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import pygame
import config
from controller import Controller
from drone import Drone
from models import ControllerState, TelemetryData
from ui import UI
from utils import load_sound


LOGGER = logging.getLogger(__name__)


BUTTON_FLASH_SECONDS = 0.2
LOW_BATTERY_SOUND_INTERVAL = 30.0


@dataclass
class UIState:
    alert_text: Optional[str]
    alert_level: Optional[str]
    highlighted_buttons: Dict[str, bool]
    connection_label: str
    takeoff_prompt: Optional[str]
    busy_text: Optional[str]


@dataclass
class Runtime:
    screen: pygame.Surface
    clock: pygame.time.Clock
    controller: Controller
    drone: Drone
    ui: UI
    sounds: Dict[str, object]
    button_flash_until: Dict[str, float]
    low_battery_sound_at: float
    last_connection_state: Optional[bool]
    last_low_battery_state: bool
    last_error_state: bool
    action_threads: Dict[str, threading.Thread]
    action_lock: threading.Lock
    busy_action: Optional[str]


def init_pygame(headless: bool = False) -> None:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error as exc:
        LOGGER.warning("Audio disabled: %s", exc)


def create_runtime(headless: bool = False, auto_connect: bool = True) -> Runtime:
    init_pygame(headless=headless)
    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    drone = Drone()
    if auto_connect:
        drone.connect()
    return Runtime(
        screen=screen,
        clock=clock,
        controller=Controller(),
        drone=drone,
        ui=UI(),
        sounds=load_sounds(pygame),
        button_flash_until={},
        low_battery_sound_at=0.0,
        last_connection_state=None,
        last_low_battery_state=False,
        last_error_state=False,
        action_threads={},
        action_lock=threading.Lock(),
        busy_action=None,
    )


def shutdown(runtime: Runtime) -> None:
    with runtime.action_lock:
        active_threads = list(runtime.action_threads.values())
    for thread in active_threads:
        thread.join(timeout=1.0)
    if runtime.drone.is_airborne:
        runtime.drone.land()
    runtime.drone.disconnect()
    pygame.quit()


def run_app(frame_limit: Optional[int] = None, headless: bool = False, auto_connect: bool = True) -> int:
    runtime = create_runtime(headless=headless, auto_connect=auto_connect)
    frame_count = 0

    try:
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
            except pygame.error as exc:
                LOGGER.warning("Pygame event handling failed: %s", exc)

            controller_state = runtime.controller.update()
            handle_controller_actions(runtime, controller_state)
            telemetry = runtime.drone.get_telemetry()
            ui_state = build_ui_state(runtime, controller_state, telemetry)
            maybe_play_sounds(runtime, telemetry)
            runtime.ui.draw(runtime.screen, controller_state, telemetry, ui_state)
            pygame.display.flip()
            runtime.clock.tick(config.FPS)

            frame_count += 1
            if frame_limit is not None and frame_count >= frame_limit:
                running = False
    finally:
        shutdown(runtime)

    return 0


def load_sounds(pygame_module) -> Dict[str, object]:
    return {
        "connect": load_sound(pygame_module, "sounds/connect.wav"),
        "takeoff": load_sound(pygame_module, "sounds/takeoff.wav"),
        "land": load_sound(pygame_module, "sounds/land.wav"),
        "low_battery": load_sound(pygame_module, "sounds/low_battery.wav"),
        "error": load_sound(pygame_module, "sounds/error.wav"),
    }


def handle_controller_actions(runtime: Runtime, controller_state: ControllerState) -> None:
    now = time.monotonic()
    flash_map = {
        "r2_y": controller_state.takeoff_land_pressed,
        "l2_up": controller_state.flip_direction == "forward",
        "l2_down": controller_state.flip_direction == "back",
        "l2_left": controller_state.flip_direction == "left",
        "l2_right": controller_state.flip_direction == "right",
    }
    for name, active in flash_map.items():
        if active:
            runtime.button_flash_until[name] = now + BUTTON_FLASH_SECONDS

    if controller_state.takeoff_land_pressed:
        if runtime.drone.is_airborne:
            start_action(runtime, "land", runtime.drone.land, runtime.sounds.get("land"))
        else:
            start_action(runtime, "takeoff", runtime.drone.takeoff, runtime.sounds.get("takeoff"))
    if controller_state.flip_direction:
        direction = controller_state.flip_direction
        start_action(runtime, "flip", lambda: runtime.drone.flip(direction), None)

    if controller_state.connected:
        runtime.drone.send_rc(
            int(controller_state.right_x),
            int(controller_state.right_y),
            int(controller_state.left_y),
            int(controller_state.left_x),
        )
    else:
        runtime.drone.send_rc(0, 0, 0, 0)


def build_ui_state(runtime: Runtime, controller_state: ControllerState, telemetry: TelemetryData) -> UIState:
    now = time.monotonic()
    highlighted = {
        name: expiry > now
        for name, expiry in runtime.button_flash_until.items()
        if expiry > now
    }
    runtime.button_flash_until = {
        name: expiry for name, expiry in runtime.button_flash_until.items() if expiry > now
    }

    alert_text, alert_level = determine_alert(controller_state, telemetry)
    takeoff_prompt = None
    if controller_state.r2_pressed:
        takeoff_prompt = "Press Y while holding R2 to take off or land"
    elif controller_state.l2_pressed:
        takeoff_prompt = "Use D-pad while holding L2 to flip"

    connection_label = "CONNECTED" if telemetry.connected else "DISCONNECTED"
    return UIState(
        alert_text=alert_text,
        alert_level=alert_level,
        highlighted_buttons=highlighted,
        connection_label=connection_label,
        takeoff_prompt=takeoff_prompt,
        busy_text=runtime.busy_action,
    )


def determine_alert(
    controller_state: ControllerState,
    telemetry: TelemetryData,
) -> tuple[Optional[str], Optional[str]]:
    if telemetry.emergency_active:
        return "EMERGENCY STOP ACTIVATED", "danger"
    if not controller_state.connected:
        return "CONTROLLER DISCONNECTED - Reconnecting...", "danger"
    if not telemetry.connected:
        if telemetry.retry_exhausted:
            return "DRONE DISCONNECTED - Check Wi-Fi", "danger"
        return "DRONE DISCONNECTED - Reconnecting...", "danger"
    if telemetry.battery is not None and telemetry.battery < 10:
        return "CRITICAL BATTERY - LANDING RECOMMENDED", "danger"
    if telemetry.battery is not None and telemetry.battery < config.LOW_BATTERY_THRESHOLD:
        return "LOW BATTERY - LAND SOON", "warning"
    return None, None


def maybe_play_sounds(runtime: Runtime, telemetry: TelemetryData) -> None:
    now = time.monotonic()
    if runtime.last_connection_state is not None:
        if telemetry.connected and not runtime.last_connection_state:
            play_sound(runtime.sounds.get("connect"))
        elif not telemetry.connected and runtime.last_connection_state:
            play_sound(runtime.sounds.get("error"))
    runtime.last_connection_state = telemetry.connected

    low_battery = telemetry.battery is not None and telemetry.battery < config.LOW_BATTERY_THRESHOLD
    if low_battery and now >= runtime.low_battery_sound_at:
        play_sound(runtime.sounds.get("low_battery"))
        runtime.low_battery_sound_at = now + LOW_BATTERY_SOUND_INTERVAL
    elif not low_battery:
        runtime.low_battery_sound_at = 0.0
    runtime.last_low_battery_state = low_battery


def play_sound(sound: object) -> None:
    if sound is None:
        return
    try:
        sound.play()
    except Exception as exc:  # pragma: no cover - intentionally broad to avoid crashing the app
        LOGGER.warning("Sound playback failed: %s", exc)


def start_action(
    runtime: Runtime,
    name: str,
    action: Callable[[], bool],
    success_sound: object,
) -> bool:
    with runtime.action_lock:
        existing = runtime.action_threads.get(name)
        if existing is not None and existing.is_alive():
            return False

        def runner() -> None:
            try:
                runtime.busy_action = name.upper()
                if action():
                    play_sound(success_sound)
            finally:
                with runtime.action_lock:
                    runtime.action_threads.pop(name, None)
                    if runtime.busy_action == name.upper():
                        runtime.busy_action = None

        thread = threading.Thread(target=runner, name="action-{0}".format(name), daemon=True)
        runtime.action_threads[name] = thread
        thread.start()
        return True


if __name__ == "__main__":
    raise SystemExit(run_app())
