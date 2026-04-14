from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ControllerState:
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    a_pressed: bool = False
    b_pressed: bool = False
    x_pressed: bool = False
    y_pressed: bool = False
    lb_pressed: bool = False
    rb_pressed: bool = False
    start_pressed: bool = False
    connected: bool = False
    speed_mode: str = "NORMAL"
    takeoff_hold_progress: float = 0.0
    takeoff_ready: bool = False
    takeoff_land_pressed: bool = False
    flip_direction: Optional[str] = None
    l2_pressed: bool = False
    r2_pressed: bool = False
    dpad_x: int = 0
    dpad_y: int = 0
    controller_name: str = ""
    raw_axes: Tuple[float, ...] = ()


@dataclass
class TelemetryData:
    connected: bool = False
    battery: Optional[int] = None
    height: Optional[int] = None
    temperature: Optional[int] = None
    flight_time: Optional[int] = None
    speed: Optional[float] = None
    airborne: bool = False
    signal_strength: str = "none"
    retrying: bool = False
    retry_exhausted: bool = False
    retries: int = 0
    last_error: Optional[str] = None
    emergency_active: bool = False
