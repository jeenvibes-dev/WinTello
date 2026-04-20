from __future__ import annotations

import pygame
from dataclasses import dataclass
from typing import Optional

import config
from models import ControllerState, TelemetryData


@dataclass
class ButtonLegend:
    label: str
    caption: str
    key: str


class UI:
    """Phase 3 dashboard renderer."""

    def __init__(self) -> None:
        pygame.font.init()
        self._title_font = pygame.font.SysFont("bahnschrift", 44)
        self._body_font = pygame.font.SysFont("bahnschrift", 26)
        self._small_font = pygame.font.SysFont("consolas", 18)
        self._button_font = pygame.font.SysFont("bahnschrift", 26)

        self._button_legends = [
            ButtonLegend("R2+Y", "Takeoff/Land", "r2_y"),
            ButtonLegend("L2+Up", "Flip Fwd", "l2_up"),
            ButtonLegend("L2+Down", "Flip Back", "l2_down"),
            ButtonLegend("L2+Left", "Flip Left", "l2_left"),
            ButtonLegend("L2+Right", "Flip Right", "l2_right"),
        ]

    def draw(
        self,
        surface: pygame.Surface,
        controller_state: ControllerState,
        telemetry: TelemetryData,
        ui_state,
        video_frame=None,
    ) -> None:
        self._draw_background(surface)
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
        video_rect = pygame.Rect(
            left_panel.right + gap,
            content_top,
            right_panel.left - left_panel.right - gap * 2,
            content_height,
        )
        alert_bar = pygame.Rect(video_rect.x, video_rect.bottom - 34, video_rect.width, 28)

        pygame.draw.rect(surface, config.COLOR_PANEL, header_rect, border_radius=8)
        pygame.draw.rect(surface, config.COLOR_PANEL, left_panel, border_radius=8)
        pygame.draw.rect(surface, config.COLOR_PANEL, right_panel, border_radius=8)
        pygame.draw.rect(surface, config.COLOR_PANEL, bottom_bar, border_radius=8)

        self._draw_header(surface, header_rect, telemetry, ui_state)
        self._draw_drone_status(surface, left_panel, telemetry)
        self._draw_media_panel(surface, left_panel, ui_state)
        self._draw_camera_view(surface, video_rect, video_frame, telemetry.connected, ui_state)
        self._draw_controller_panel(surface, right_panel, controller_state, ui_state.takeoff_prompt)
        self._draw_bottom_bar(surface, bottom_bar, ui_state.highlighted_buttons)
        self._draw_alert_bar(surface, alert_bar, ui_state.alert_text, ui_state.alert_level)

    def playback_button_hit(self, surface: pygame.Surface, position: tuple[int, int]) -> bool:
        return self._playback_button_rect(surface).collidepoint(position)

    def _draw_header(
        self,
        surface: pygame.Surface,
        header_rect: pygame.Rect,
        telemetry: TelemetryData,
        ui_state,
    ) -> None:
        title = self._title_font.render("DJI TELLO DRONE", True, config.COLOR_TEXT)
        surface.blit(title, (header_rect.x + 20, header_rect.y + 14))

        connection_color = config.COLOR_SUCCESS if telemetry.connected else config.COLOR_DANGER
        pill = pygame.Rect(header_rect.right - 220, header_rect.y + 16, 190, 42)
        pygame.draw.rect(surface, connection_color, pill, border_radius=8)
        pill_text = self._body_font.render(ui_state.connection_label, True, (255, 255, 255))
        surface.blit(pill_text, pill_text.get_rect(center=pill.center))
        if ui_state.busy_text:
            busy_text = self._small_font.render("BUSY: {0}".format(ui_state.busy_text), True, config.COLOR_ACCENT)
            surface.blit(busy_text, (pill.x - busy_text.get_width() - 22, header_rect.y + 29))

    def _draw_drone_status(
        self,
        surface: pygame.Surface,
        panel_rect: pygame.Rect,
        telemetry: TelemetryData,
    ) -> None:
        self._draw_lines(
            surface,
            panel_rect.x + 18,
            panel_rect.y + 20,
            [
                "Drone Status",
                f"Battery: {self._format_optional_percent(telemetry.battery)}",
                f"Height: {self._format_optional_distance(telemetry.height)}",
                f"Flight: {self._format_optional_time(telemetry.flight_time)}",
                f"Signal: {telemetry.signal_strength.upper()}",
            ],
        )

    def _draw_media_panel(self, surface: pygame.Surface, panel_rect: pygame.Rect, ui_state) -> None:
        button_rect = self._playback_button_rect(surface)
        section_y = max(panel_rect.y + 300, button_rect.y - 98)
        title = self._body_font.render("Media", True, config.COLOR_TEXT)
        surface.blit(title, (panel_rect.x + 18, section_y))

        mode = "VIDEO" if ui_state.capture_mode == "video" else "PHOTO"
        recording = "REC" if ui_state.recording else "READY"
        mode_text = self._small_font.render(f"Mode: {mode}  {recording}", True, config.COLOR_TEXT_DIM)
        surface.blit(mode_text, (panel_rect.x + 18, section_y + 42))

        hint = "L1 mode  |  R1 capture"
        hint_text = self._small_font.render(hint, True, config.COLOR_TEXT_DIM)
        surface.blit(hint_text, (panel_rect.x + 18, section_y + 70))

        pygame.draw.rect(surface, config.COLOR_ACCENT, button_rect, border_radius=8)
        button_text = self._small_font.render("Playback", True, (255, 255, 255))
        surface.blit(button_text, button_text.get_rect(center=button_rect.center))

        if ui_state.media_text:
            message = self._small_font.render(ui_state.media_text, True, config.COLOR_TEXT)
            surface.blit(message, (panel_rect.x + 18, button_rect.bottom + 14))

    def _playback_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        width, height = surface.get_size()
        margin = 24
        header_bottom = 20 + 74
        content_top = header_bottom + 18
        content_bottom = (height - 122) - 18
        content_height = max(420, content_bottom - content_top)
        left_width = min(330, max(285, int(width * 0.21)))
        left_panel = pygame.Rect(margin, content_top, left_width, content_height)
        return pygame.Rect(left_panel.x + 18, left_panel.bottom - 86, left_panel.width - 36, 42)

    def _draw_camera_view(
        self,
        surface: pygame.Surface,
        camera_rect: pygame.Rect,
        video_frame,
        connected: bool,
        ui_state,
    ) -> None:
        pygame.draw.rect(surface, (10, 10, 12), camera_rect, border_radius=8)
        pygame.draw.rect(surface, (72, 72, 82), camera_rect, width=2, border_radius=8)

        frame_surface = self._frame_to_surface(video_frame)
        if frame_surface is not None:
            scaled = self._scale_to_cover(frame_surface, camera_rect.size)
            source_rect = scaled.get_rect()
            crop_rect = pygame.Rect(
                max(0, (source_rect.width - camera_rect.width) // 2),
                max(0, (source_rect.height - camera_rect.height) // 2),
                camera_rect.width,
                camera_rect.height,
            )
            surface.blit(scaled, camera_rect.topleft, crop_rect)
            pygame.draw.rect(surface, (245, 245, 245), camera_rect, width=2, border_radius=8)
            self._draw_capture_indicator(surface, camera_rect, ui_state)
            return

        label = "Camera waiting for drone stream" if connected else "Connect to drone for live camera"
        title = self._title_font.render(label, True, config.COLOR_TEXT)
        detail = self._body_font.render("Live Tello video will appear here.", True, config.COLOR_TEXT_DIM)
        surface.blit(title, title.get_rect(center=(camera_rect.centerx, camera_rect.centery - 18)))
        surface.blit(detail, detail.get_rect(center=(camera_rect.centerx, camera_rect.centery + 34)))

        self._draw_capture_indicator(surface, camera_rect, ui_state)

    def _draw_capture_indicator(self, surface: pygame.Surface, camera_rect: pygame.Rect, ui_state) -> None:
        center = (camera_rect.right - 34, camera_rect.y + 34)
        if ui_state.capture_mode == "video" and ui_state.recording:
            rec_rect = pygame.Rect(0, 0, 20, 20)
            rec_rect.center = center
            pygame.draw.rect(surface, config.COLOR_DANGER, rec_rect, border_radius=3)
            rec_text = self._small_font.render("REC", True, config.COLOR_DANGER)
            surface.blit(rec_text, (rec_rect.x - rec_text.get_width() - 10, rec_rect.y - 1))
            return

        if ui_state.capture_mode == "video":
            pygame.draw.circle(surface, config.COLOR_DANGER, center, 11)
            return

        pygame.draw.circle(surface, (255, 255, 255), center, 11)
        pygame.draw.circle(surface, (30, 30, 34), center, 11, width=2)

    def _frame_to_surface(self, video_frame) -> Optional[pygame.Surface]:
        if video_frame is None:
            return None
        try:
            # djitellopy provides frames as RGB arrays through PyAV/Pillow.
            return pygame.surfarray.make_surface(video_frame.swapaxes(0, 1))
        except Exception:
            return None

    @staticmethod
    def _scale_to_cover(source: pygame.Surface, target_size: tuple[int, int]) -> pygame.Surface:
        target_width, target_height = target_size
        source_width, source_height = source.get_size()
        if source_width <= 0 or source_height <= 0:
            return source
        scale = max(target_width / source_width, target_height / source_height)
        scaled_size = (max(1, int(source_width * scale)), max(1, int(source_height * scale)))
        return pygame.transform.smoothscale(source, scaled_size)

    def _draw_lines(self, surface: pygame.Surface, x: int, y: int, lines: list[str]) -> None:
        for index, line in enumerate(lines):
            color = config.COLOR_TEXT if index == 0 else config.COLOR_TEXT_DIM
            font = self._title_font if index == 0 else self._body_font
            rendered = font.render(line, True, color)
            offset = 0 if index == 0 else 74 + (index - 1) * 64
            surface.blit(rendered, (x, y + offset))

    def _draw_controller_panel(
        self,
        surface: pygame.Surface,
        panel_rect: pygame.Rect,
        controller_state: ControllerState,
        takeoff_prompt: Optional[str],
    ) -> None:
        title = self._title_font.render("Controller", True, config.COLOR_TEXT)
        surface.blit(title, (panel_rect.x + 16, panel_rect.y + 18))
        status = self._body_font.render(
            "Connected" if controller_state.connected else "Waiting for controller",
            True,
            config.COLOR_TEXT_DIM,
        )
        surface.blit(status, (panel_rect.x + 16, panel_rect.y + 72))

        if panel_rect.width >= 720:
            left_center = (panel_rect.x + 170, panel_rect.y + 185)
            right_center = (panel_rect.x + 520, panel_rect.y + 185)
        else:
            left_center = (panel_rect.centerx, panel_rect.y + 205)
            right_center = (panel_rect.centerx, panel_rect.y + 420)
        self._draw_stick(
            surface,
            left_center,
            controller_state.left_x,
            controller_state.left_y,
            "YAW / THROTTLE",
        )
        self._draw_stick(
            surface,
            right_center,
            controller_state.right_x,
            controller_state.right_y,
            "ROLL / PITCH",
        )

        prompt = takeoff_prompt or self._hold_text(controller_state)
        font = self._body_font if panel_rect.width >= 620 else self._small_font
        prompt_text = font.render(prompt, True, config.COLOR_ACCENT)
        prompt_x = panel_rect.x + 24
        if prompt_text.get_width() > panel_rect.width - 48:
            prompt = "R2+Y takeoff/land. L2+D-pad flips."
            prompt_text = self._small_font.render(prompt, True, config.COLOR_ACCENT)
        surface.blit(prompt_text, (prompt_x, panel_rect.bottom - 54))

    def _draw_stick(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        x_value: float,
        y_value: float,
        label: str,
    ) -> None:
        radius = 54
        pygame.draw.circle(surface, (50, 50, 74), center, radius)
        pygame.draw.circle(surface, (95, 95, 130), center, radius, width=2)
        dot_x = int(center[0] + (x_value / 100.0) * 28)
        dot_y = int(center[1] - (y_value / 100.0) * 28)
        pygame.draw.circle(surface, config.COLOR_ACCENT, (dot_x, dot_y), 9)
        label_text = self._small_font.render(label, True, config.COLOR_TEXT)
        values_text = self._small_font.render(
            "X: {0:.0f}  Y: {1:.0f}".format(x_value, y_value),
            True,
            config.COLOR_TEXT_DIM,
        )
        surface.blit(label_text, (center[0] - label_text.get_width() // 2, center[1] + 78))
        surface.blit(values_text, (center[0] - values_text.get_width() // 2, center[1] + 106))

    def _draw_bottom_bar(
        self,
        surface: pygame.Surface,
        bar_rect: pygame.Rect,
        highlighted_buttons,
    ) -> None:
        gap = 16
        width = min(205, max(132, (bar_rect.width - 52 - gap * (len(self._button_legends) - 1)) // len(self._button_legends)))
        start_x = bar_rect.x + 26
        for index, legend in enumerate(self._button_legends):
            x = start_x + index * (width + gap)
            button_rect = pygame.Rect(x, bar_rect.y + 18, width, 64)
            active = highlighted_buttons.get(legend.key, False)
            fill = config.COLOR_ACCENT if active else (46, 46, 70)
            pygame.draw.rect(surface, fill, button_rect, border_radius=8)
            label = self._body_font.render(legend.label, True, (255, 255, 255))
            caption = self._small_font.render(legend.caption, True, config.COLOR_TEXT)
            surface.blit(label, (button_rect.x + 14, button_rect.y + 6))
            surface.blit(caption, (button_rect.x + 14, button_rect.y + 38))

    def _draw_alert_bar(
        self,
        surface: pygame.Surface,
        alert_rect: pygame.Rect,
        alert_text: Optional[str],
        alert_level: Optional[str],
    ) -> None:
        if not alert_text:
            return
        color = config.COLOR_DANGER if alert_level == "danger" else config.COLOR_WARNING
        pygame.draw.rect(surface, color, alert_rect, border_radius=10)
        text = self._small_font.render(alert_text, True, (20, 20, 20))
        surface.blit(text, (alert_rect.x + 12, alert_rect.y + 6))

    def _draw_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill(config.COLOR_BG)
        for x in range(0, width + 240, 120):
            pygame.draw.line(surface, (18, 18, 18), (x, 0), (x - 180, height), 1)

    @staticmethod
    def _format_optional_percent(value: Optional[int]) -> str:
        return "--" if value is None else f"{value}%"

    @staticmethod
    def _format_optional_distance(value: Optional[int]) -> str:
        return "--" if value is None else f"{value / 100:.1f} m"

    @staticmethod
    def _format_optional_time(value: Optional[int]) -> str:
        if value is None:
            return "--:--"
        minutes, seconds = divmod(value, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _hold_text(controller_state: ControllerState) -> str:
        if controller_state.r2_pressed:
            return "R2 armed. Tap Y to take off or land."
        if controller_state.l2_pressed:
            return "L2 armed. Use D-pad to trigger a flip."
        return "Sticks control flight. Combo actions are armed by triggers."
