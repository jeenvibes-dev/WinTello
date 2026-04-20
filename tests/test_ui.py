from __future__ import annotations

import numpy as np
import pygame

import config
import main
from models import ControllerState, TelemetryData
from ui import UI


def test_video_frame_preserves_rgb_channels():
    pygame.init()
    surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:, :, 0] = 255

    UI().draw(
        surface,
        ControllerState(connected=True),
        TelemetryData(connected=True),
        main.UIState(None, None, {}, "CONNECTED", None, None, "photo", False, None),
        frame,
    )

    center_color = surface.get_at((config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2))
    assert center_color.r == 255
    assert center_color.g == 0
    assert center_color.b == 0


def test_capture_indicator_shows_photo_video_and_recording_states():
    pygame.init()
    surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    ui = UI()
    camera_rect = _camera_rect(surface)

    ui.draw(
        surface,
        ControllerState(connected=True),
        TelemetryData(connected=True),
        main.UIState(None, None, {}, "CONNECTED", None, None, "photo", False, None),
        None,
    )
    photo_color = surface.get_at((camera_rect.right - 34, camera_rect.y + 34))
    assert photo_color.r == 255
    assert photo_color.g == 255
    assert photo_color.b == 255

    ui.draw(
        surface,
        ControllerState(connected=True),
        TelemetryData(connected=True),
        main.UIState(None, None, {}, "CONNECTED", None, None, "video", False, None),
        None,
    )
    video_color = surface.get_at((camera_rect.right - 34, camera_rect.y + 34))
    assert video_color.r == config.COLOR_DANGER[0]
    assert video_color.g == config.COLOR_DANGER[1]
    assert video_color.b == config.COLOR_DANGER[2]

    ui.draw(
        surface,
        ControllerState(connected=True),
        TelemetryData(connected=True),
        main.UIState(None, None, {}, "CONNECTED", None, None, "video", True, None),
        None,
    )
    recording_corner = surface.get_at((camera_rect.right - 40, camera_rect.y + 28))
    assert recording_corner.r == config.COLOR_DANGER[0]
    assert recording_corner.g == config.COLOR_DANGER[1]
    assert recording_corner.b == config.COLOR_DANGER[2]


def _camera_rect(surface: pygame.Surface) -> pygame.Rect:
    width, height = surface.get_size()
    margin = 24
    gap = 18
    header_rect = pygame.Rect(margin, 20, width - margin * 2, 74)
    bottom_bar = pygame.Rect(margin, height - 122, width - margin * 2, 96)
    content_top = header_rect.bottom + gap
    content_bottom = bottom_bar.top - gap
    content_height = max(420, content_bottom - content_top)
    left_width = min(330, max(285, int(width * 0.21)))
    right_width = min(470, max(390, int(width * 0.28)))
    left_panel = pygame.Rect(margin, content_top, left_width, content_height)
    right_panel = pygame.Rect(width - margin - right_width, content_top, right_width, content_height)
    return pygame.Rect(
        left_panel.right + gap,
        content_top,
        right_panel.left - left_panel.right - gap * 2,
        content_height,
    )
