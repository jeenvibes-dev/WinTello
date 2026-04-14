from __future__ import annotations

import logging
import threading
import time
from dataclasses import replace
from typing import Optional

import config
from models import TelemetryData


LOGGER = logging.getLogger(__name__)


class TelloBackend:
    """Small adapter around djitellopy so the Drone wrapper stays testable."""

    def __init__(self) -> None:
        from djitellopy import Tello

        self._tello = Tello()

    def connect(self) -> None:
        self._tello.connect()

    def end(self) -> None:
        self._tello.end()

    def send_rc_control(self, left_right: int, forward_back: int, up_down: int, yaw: int) -> None:
        self._tello.send_rc_control(left_right, forward_back, up_down, yaw)

    def takeoff(self) -> None:
        self._tello.takeoff()

    def land(self) -> None:
        self._tello.land()

    def emergency(self) -> None:
        self._tello.emergency()

    def flip_forward(self) -> None:
        self._tello.flip_forward()

    def flip_back(self) -> None:
        self._tello.flip_back()

    def flip_left(self) -> None:
        self._tello.flip_left()

    def flip_right(self) -> None:
        self._tello.flip_right()

    def get_battery(self) -> int:
        return int(self._tello.get_battery())

    def get_height(self) -> int:
        return int(self._tello.get_height())

    def get_temperature(self) -> int:
        return int(self._tello.get_temperature())

    def get_flight_time(self) -> int:
        return int(self._tello.get_flight_time())


class Drone:
    """Fault-tolerant Tello wrapper with retry logic and telemetry polling."""

    def __init__(
        self,
        backend: Optional[object] = None,
        time_fn=time.monotonic,
        telemetry_poll_interval: float = config.TELEMETRY_POLL_INTERVAL,
    ) -> None:
        self._backend = backend
        self._time_fn = time_fn
        self._telemetry_poll_interval = telemetry_poll_interval
        self._telemetry = TelemetryData()
        self._connected = False
        self._airborne = False
        self._retry_count = 0
        self._last_retry_at: Optional[float] = None
        self._telemetry_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._telemetry_thread: Optional[threading.Thread] = None
        self._emergency_until = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_airborne(self) -> bool:
        return self._airborne

    def connect(self) -> bool:
        backend = self._ensure_backend()
        if backend is None:
            self._set_disconnected_state("Drone backend unavailable")
            return False

        try:
            LOGGER.info("Connecting to Tello")
            backend.connect()
        except Exception as exc:
            self._retry_count += 1
            self._last_retry_at = self._time_fn()
            self._set_disconnected_state(str(exc), retrying=self._retry_count < config.MAX_RECONNECT_RETRIES)
            LOGGER.warning("Tello connect failed: %s", exc)
            return False

        with self._telemetry_lock:
            self._connected = True
            self._retry_count = 0
            self._last_retry_at = None
            self._telemetry.connected = True
            self._telemetry.retrying = False
            self._telemetry.retry_exhausted = False
            self._telemetry.retries = 0
            self._telemetry.last_error = None
        self.refresh_telemetry()
        self._ensure_telemetry_thread()
        return True

    def maybe_reconnect(self) -> bool:
        if self._connected:
            return True
        if self._retry_count >= config.MAX_RECONNECT_RETRIES:
            with self._telemetry_lock:
                self._telemetry.retrying = False
                self._telemetry.retry_exhausted = True
            return False

        now = self._time_fn()
        if self._last_retry_at is not None and (now - self._last_retry_at) < config.RECONNECT_INTERVAL:
            return False
        return self.connect()

    def manual_reconnect(self) -> bool:
        self._retry_count = 0
        self._last_retry_at = None
        return self.connect()

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._telemetry_thread is not None and self._telemetry_thread.is_alive():
            self._telemetry_thread.join(timeout=1.0)
        self._connected = False
        self._airborne = False
        if self._backend is not None:
            try:
                self._backend.end()
            except Exception as exc:
                LOGGER.warning("Tello end failed: %s", exc)
        with self._telemetry_lock:
            self._telemetry.connected = False
            self._telemetry.airborne = False

    def send_rc(self, left_right: int, forward_back: int, up_down: int, yaw: int) -> None:
        if not self._connected or self._backend is None:
            return
        try:
            self._backend.send_rc_control(left_right, forward_back, up_down, yaw)
        except Exception as exc:
            LOGGER.warning("send_rc failed: %s", exc)
            self._mark_connection_lost(str(exc))

    def takeoff(self) -> bool:
        telemetry = self.get_telemetry()
        if not self._connected or self._airborne:
            return False
        if telemetry.battery is not None and telemetry.battery <= 10:
            return False
        try:
            assert self._backend is not None
            self._backend.takeoff()
            self._airborne = True
            with self._telemetry_lock:
                self._telemetry.airborne = True
            return True
        except Exception as exc:
            LOGGER.warning("takeoff failed: %s", exc)
            self._mark_connection_lost(str(exc))
            return False

    def land(self) -> bool:
        if not self._connected or not self._airborne:
            return False
        try:
            assert self._backend is not None
            self._backend.land()
            self._airborne = False
            with self._telemetry_lock:
                self._telemetry.airborne = False
            return True
        except Exception as exc:
            LOGGER.warning("land failed: %s", exc)
            self._mark_connection_lost(str(exc))
            return False

    def emergency(self) -> None:
        if self._backend is not None:
            try:
                self._backend.emergency()
            except Exception as exc:
                LOGGER.warning("emergency failed: %s", exc)
        self._airborne = False
        with self._telemetry_lock:
            self._telemetry.airborne = False
            self._telemetry.emergency_active = True
        self._emergency_until = self._time_fn() + 3.0

    def flip(self, direction: str = "forward") -> bool:
        telemetry = self.get_telemetry()
        if not self._connected or not self._airborne:
            return False
        if direction not in {"forward", "back", "left", "right"}:
            return False
        if telemetry.battery is None or telemetry.battery <= config.FLIP_MIN_BATTERY:
            return False
        if telemetry.height is None or telemetry.height <= config.FLIP_MIN_HEIGHT:
            return False
        try:
            assert self._backend is not None
            if direction == "forward":
                self._backend.flip_forward()
            elif direction == "back":
                self._backend.flip_back()
            elif direction == "left":
                self._backend.flip_left()
            else:
                self._backend.flip_right()
            return True
        except Exception as exc:
            LOGGER.warning("flip failed: %s", exc)
            self._mark_connection_lost(str(exc))
            return False

    def get_telemetry(self) -> TelemetryData:
        with self._telemetry_lock:
            telemetry = replace(self._telemetry)
        if telemetry.emergency_active and self._time_fn() >= self._emergency_until:
            telemetry.emergency_active = False
            with self._telemetry_lock:
                self._telemetry.emergency_active = False
        return telemetry

    def refresh_telemetry(self) -> bool:
        if not self._connected or self._backend is None:
            return False
        try:
            battery = self._backend.get_battery()
            height = self._backend.get_height()
            temperature = self._backend.get_temperature()
            flight_time = self._backend.get_flight_time()
        except Exception as exc:
            LOGGER.warning("telemetry refresh failed: %s", exc)
            self._mark_connection_lost(str(exc))
            return False

        with self._telemetry_lock:
            self._telemetry.connected = True
            self._telemetry.battery = battery
            self._telemetry.height = height
            self._telemetry.temperature = temperature
            self._telemetry.flight_time = flight_time
            self._telemetry.airborne = self._airborne
            self._telemetry.signal_strength = "strong"
            self._telemetry.retrying = False
            self._telemetry.retry_exhausted = False
            self._telemetry.retries = self._retry_count
            self._telemetry.last_error = None
        return True

    def _ensure_backend(self) -> Optional[object]:
        if self._backend is not None:
            return self._backend
        try:
            self._backend = TelloBackend()
        except Exception as exc:
            LOGGER.warning("Unable to create Tello backend: %s", exc)
            return None
        return self._backend

    def _ensure_telemetry_thread(self) -> None:
        if self._telemetry_thread is not None and self._telemetry_thread.is_alive():
            return
        self._stop_event.clear()
        self._telemetry_thread = threading.Thread(
            target=self._telemetry_loop,
            name="tello-telemetry",
            daemon=True,
        )
        self._telemetry_thread.start()

    def _telemetry_loop(self) -> None:
        while not self._stop_event.wait(self._telemetry_poll_interval):
            if self._connected:
                self.refresh_telemetry()
            else:
                self.maybe_reconnect()

    def _mark_connection_lost(self, message: str) -> None:
        self._retry_count += 1
        self._last_retry_at = self._time_fn()
        self._set_disconnected_state(
            message,
            retrying=self._retry_count < config.MAX_RECONNECT_RETRIES,
        )

    def _set_disconnected_state(self, message: str, retrying: bool = False) -> None:
        self._connected = False
        self._airborne = False
        with self._telemetry_lock:
            self._telemetry.connected = False
            self._telemetry.airborne = False
            self._telemetry.signal_strength = "none"
            self._telemetry.retrying = retrying
            self._telemetry.retry_exhausted = self._retry_count >= config.MAX_RECONNECT_RETRIES
            self._telemetry.retries = self._retry_count
            self._telemetry.last_error = message
