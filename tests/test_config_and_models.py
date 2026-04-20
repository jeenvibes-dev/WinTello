import config
from models import ControllerState, TelemetryData


def test_window_defaults_are_defined():
    assert config.WINDOW_WIDTH == 1600
    assert config.WINDOW_HEIGHT == 900
    assert config.MIN_WINDOW_WIDTH == 960
    assert config.MIN_WINDOW_HEIGHT == 620
    assert config.WINDOW_SCREEN_WIDTH_RATIO == 0.92
    assert config.WINDOW_SCREEN_HEIGHT_RATIO == 0.86
    assert config.FPS == 60


def test_controller_state_defaults_are_safe():
    state = ControllerState()
    assert state.connected is False
    assert state.speed_mode == "NORMAL"
    assert state.takeoff_ready is False
    assert state.left_x == 0.0
    assert state.right_y == 0.0


def test_telemetry_defaults_indicate_no_connection():
    telemetry = TelemetryData()
    assert telemetry.connected is False
    assert telemetry.airborne is False
    assert telemetry.battery is None
    assert telemetry.signal_strength == "none"
