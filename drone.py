from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import replace
from typing import Optional

import config
from models import TelemetryData


LOGGER = logging.getLogger(__name__)


class LowLatencyVideoReader:
    """Continuously drains the Tello UDP stream and keeps only the newest frame."""

    def __init__(self, address: str) -> None:
        self._address = address
        self._frame = None
        self._failed = False
        self._frame_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._capture = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, name="tello-video", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def get_frame(self):
        with self._frame_lock:
            return self._frame

    @property
    def failed(self) -> bool:
        return self._failed

    def _read_loop(self) -> None:
        try:
            capture = self._open_capture()
        except Exception as exc:
            self._failed = True
            LOGGER.warning("Unable to open low-latency video stream: %s", exc)
            return

        self._capture = capture
        while not self._stop_event.is_set():
            ok, frame = capture.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            rgb_frame = frame[:, :, [2, 1, 0]]
            with self._frame_lock:
                self._frame = rgb_frame

    def _open_capture(self):
        # These FFmpeg flags tell OpenCV to favor live playback over buffered playback.
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            "fflags;nobuffer|flags;low_delay|probesize;32|analyzeduration;0",
        )
        import cv2

        api_preference = getattr(cv2, "CAP_FFMPEG", 0)
        capture = cv2.VideoCapture(self._address, api_preference)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("video stream did not open")
        return capture


class TelloBackend:
    """Small adapter around djitellopy so the Drone wrapper stays testable."""

    def __init__(self) -> None:
        from djitellopy import Tello

        self._tello = Tello()
        self._frame_read = None
        self._video_reader: Optional[LowLatencyVideoReader] = None

    def connect(self) -> None:
        self._tello.connect()

    def end(self) -> None:
        self._tello.end()

    def streamon(self) -> None:
        self._tello.streamon()
        address = self._tello.get_udp_video_address()
        self._video_reader = LowLatencyVideoReader(address)
        self._video_reader.start()

    def streamoff(self) -> None:
        if self._video_reader is not None:
            self._video_reader.stop()
            self._video_reader = None
        self._tello.streamoff()
        self._frame_read = None

    def get_video_frame(self):
        if self._video_reader is not None:
            frame = self._video_reader.get_frame()
            if frame is not None:
                return frame
            if not self._video_reader.failed:
                return None
        if self._frame_read is None:
            self._frame_read = self._tello.get_frame_read(with_queue=True, max_queue_len=1)
        return self._frame_read.frame

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

    def get_lowest_temperature(self) -> int:
        return int(self._tello.get_lowest_temperature())

    def get_highest_temperature(self) -> int:
        return int(self._tello.get_highest_temperature())

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
        self._video_enabled = False

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
        self._start_video_stream()
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
            self._stop_video_stream()
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

    def get_video_frame(self):
        if not self._connected or self._backend is None or not self._video_enabled:
            return None
        if not hasattr(self._backend, "get_video_frame"):
            return None
        try:
            return self._backend.get_video_frame()
        except Exception as exc:
            LOGGER.warning("video frame read failed: %s", exc)
            return None

    def refresh_telemetry(self) -> bool:
        if not self._connected or self._backend is None:
            return False
        try:
            battery = self._backend.get_battery()
            height = self._backend.get_height()
            temperature, temperature_low, temperature_high = self._read_temperature()
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
            self._telemetry.temperature_low = temperature_low
            self._telemetry.temperature_high = temperature_high
            self._telemetry.flight_time = flight_time
            self._telemetry.airborne = self._airborne
            self._telemetry.signal_strength = "strong"
            self._telemetry.retrying = False
            self._telemetry.retry_exhausted = False
            self._telemetry.retries = self._retry_count
            self._telemetry.last_error = None
        return True

    def _read_temperature(self) -> tuple[int, Optional[int], Optional[int]]:
        assert self._backend is not None
        if hasattr(self._backend, "get_lowest_temperature") and hasattr(self._backend, "get_highest_temperature"):
            low = int(self._backend.get_lowest_temperature())
            high = int(self._backend.get_highest_temperature())
            return round((low + high) / 2), low, high
        temperature = int(self._backend.get_temperature())
        return temperature, None, None

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

    def _start_video_stream(self) -> None:
        if self._backend is None or not hasattr(self._backend, "streamon"):
            return
        try:
            self._backend.streamon()
            self._video_enabled = True
        except Exception as exc:
            self._video_enabled = False
            LOGGER.warning("Tello video stream failed to start: %s", exc)

    def _stop_video_stream(self) -> None:
        if self._backend is None or not self._video_enabled or not hasattr(self._backend, "streamoff"):
            self._video_enabled = False
            return
        try:
            self._backend.streamoff()
        except Exception as exc:
            LOGGER.warning("Tello video stream failed to stop: %s", exc)
        finally:
            self._video_enabled = False

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
        self._stop_video_stream()
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
