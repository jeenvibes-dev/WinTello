from __future__ import annotations

from dataclasses import dataclass

import config
from drone import Drone


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class FakeBackend:
    connect_failures_remaining: int = 0
    telemetry_failure: bool = False
    battery: int = 80
    height: int = 0
    temperature: int = 65
    temperature_low: int = None
    temperature_high: int = None
    flight_time: int = 0
    connected: bool = False
    end_called: bool = False
    takeoff_called: int = 0
    land_called: int = 0
    emergency_called: int = 0
    flip_called: int = 0
    streamon_called: int = 0
    streamoff_called: int = 0
    video_frame: object = "frame"
    sent_rc: list = None

    def __post_init__(self) -> None:
        if self.sent_rc is None:
            self.sent_rc = []

    def connect(self) -> None:
        if self.connect_failures_remaining > 0:
            self.connect_failures_remaining -= 1
            raise RuntimeError("connect failed")
        self.connected = True

    def end(self) -> None:
        self.end_called = True
        self.connected = False

    def streamon(self) -> None:
        self.streamon_called += 1

    def streamoff(self) -> None:
        self.streamoff_called += 1

    def send_rc_control(self, left_right: int, forward_back: int, up_down: int, yaw: int) -> None:
        if not self.connected:
            raise RuntimeError("not connected")
        self.sent_rc.append((left_right, forward_back, up_down, yaw))

    def takeoff(self) -> None:
        self.takeoff_called += 1

    def land(self) -> None:
        self.land_called += 1

    def emergency(self) -> None:
        self.emergency_called += 1

    def flip_forward(self) -> None:
        self.flip_called += 1

    def flip_back(self) -> None:
        self.flip_called += 1

    def flip_left(self) -> None:
        self.flip_called += 1

    def flip_right(self) -> None:
        self.flip_called += 1

    def get_battery(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.battery

    def get_height(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.height

    def get_temperature(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.temperature

    def get_lowest_temperature(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.temperature if self.temperature_low is None else self.temperature_low

    def get_highest_temperature(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.temperature if self.temperature_high is None else self.temperature_high

    def get_flight_time(self) -> int:
        if self.telemetry_failure:
            raise RuntimeError("telemetry failed")
        return self.flight_time

    def get_video_frame(self):
        return self.video_frame


def test_connect_success_refreshes_telemetry():
    backend = FakeBackend(battery=77, height=42, temperature_low=60, temperature_high=62, flight_time=9)
    drone = Drone(backend=backend)

    assert drone.connect() is True
    telemetry = drone.get_telemetry()

    assert telemetry.connected is True
    assert telemetry.battery == 77
    assert telemetry.height == 42
    assert telemetry.temperature == 61
    assert telemetry.temperature_low == 60
    assert telemetry.temperature_high == 62
    assert telemetry.flight_time == 9
    assert backend.streamon_called == 1


def test_video_frame_available_after_connect_and_stops_on_disconnect():
    backend = FakeBackend(video_frame="latest")
    drone = Drone(backend=backend)

    assert drone.get_video_frame() is None
    assert drone.connect() is True
    assert drone.get_video_frame() == "latest"

    drone.disconnect()
    assert drone.get_video_frame() is None
    assert backend.streamoff_called == 1


def test_connect_failure_sets_retrying_state():
    clock = FakeClock()
    backend = FakeBackend(connect_failures_remaining=1)
    drone = Drone(backend=backend, time_fn=clock)

    assert drone.connect() is False
    telemetry = drone.get_telemetry()

    assert telemetry.connected is False
    assert telemetry.retrying is True
    assert telemetry.retries == 1
    assert telemetry.last_error == "connect failed"


def test_maybe_reconnect_honors_interval():
    clock = FakeClock()
    backend = FakeBackend(connect_failures_remaining=1)
    drone = Drone(backend=backend, time_fn=clock)

    assert drone.connect() is False
    assert drone.maybe_reconnect() is False
    clock.advance(config.RECONNECT_INTERVAL + 0.1)
    assert drone.maybe_reconnect() is True
    assert drone.is_connected is True


def test_takeoff_requires_connected_and_battery_above_minimum():
    backend = FakeBackend(battery=10)
    drone = Drone(backend=backend)
    drone.connect()

    assert drone.takeoff() is False
    assert backend.takeoff_called == 0


def test_takeoff_and_land_update_airborne_state():
    backend = FakeBackend(battery=80)
    drone = Drone(backend=backend)
    drone.connect()

    assert drone.takeoff() is True
    assert drone.is_airborne is True
    assert backend.takeoff_called == 1

    assert drone.land() is True
    assert drone.is_airborne is False
    assert backend.land_called == 1


def test_flip_requires_airborne_battery_and_height():
    backend = FakeBackend(battery=80, height=60)
    drone = Drone(backend=backend)
    drone.connect()

    assert drone.flip() is False
    drone.takeoff()
    assert drone.flip() is True
    assert backend.flip_called == 1


def test_flip_supports_all_directions():
    backend = FakeBackend(battery=80, height=60)
    drone = Drone(backend=backend)
    drone.connect()
    drone.takeoff()

    assert drone.flip("forward") is True
    assert drone.flip("back") is True
    assert drone.flip("left") is True
    assert drone.flip("right") is True
    assert backend.flip_called == 4


def test_send_rc_noops_when_disconnected_and_sends_when_connected():
    backend = FakeBackend()
    drone = Drone(backend=backend)

    drone.send_rc(1, 2, 3, 4)
    assert backend.sent_rc == []

    drone.connect()
    drone.send_rc(1, 2, 3, 4)
    assert backend.sent_rc == [(1, 2, 3, 4)]


def test_telemetry_failure_marks_connection_lost():
    backend = FakeBackend()
    drone = Drone(backend=backend)
    drone.connect()
    backend.telemetry_failure = True

    assert drone.refresh_telemetry() is False
    telemetry = drone.get_telemetry()
    assert telemetry.connected is False
    assert telemetry.retrying is True
    assert telemetry.last_error == "telemetry failed"


def test_manual_reconnect_resets_retry_count():
    clock = FakeClock()
    backend = FakeBackend(connect_failures_remaining=1)
    drone = Drone(backend=backend, time_fn=clock)
    drone.connect()

    backend.connect_failures_remaining = 0
    assert drone.manual_reconnect() is True
    telemetry = drone.get_telemetry()
    assert telemetry.connected is True
    assert telemetry.retries == 0


def test_emergency_sets_flag_for_short_duration():
    clock = FakeClock()
    backend = FakeBackend()
    drone = Drone(backend=backend, time_fn=clock)
    drone.connect()
    drone.takeoff()

    drone.emergency()
    assert drone.get_telemetry().emergency_active is True

    clock.advance(3.1)
    assert drone.get_telemetry().emergency_active is False
