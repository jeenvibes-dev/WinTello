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
    ) -> None:
        self._draw_background(surface)
        header_rect = pygame.Rect(28, 24, config.WINDOW_WIDTH - 56, 90)
        left_panel = pygame.Rect(28, 140, 310, 430)
        right_panel = pygame.Rect(362, 140, config.WINDOW_WIDTH - 390, 430)
        bottom_bar = pygame.Rect(28, 592, config.WINDOW_WIDTH - 56, 104)
        alert_bar = pygame.Rect(28, 708, config.WINDOW_WIDTH - 56, 28)

        pygame.draw.rect(surface, config.COLOR_PANEL, header_rect, border_radius=12)
        pygame.draw.rect(surface, config.COLOR_PANEL, left_panel, border_radius=12)
        pygame.draw.rect(surface, config.COLOR_PANEL, right_panel, border_radius=12)
        pygame.draw.rect(surface, config.COLOR_PANEL, bottom_bar, border_radius=12)

        title = self._title_font.render("DJI TELLO DRONE", True, config.COLOR_TEXT)
        surface.blit(title, (48, 42))

        connection_label = ui_state.connection_label
        connection_color = config.COLOR_SUCCESS if telemetry.connected else config.COLOR_DANGER
        pill = pygame.Rect(config.WINDOW_WIDTH - 250, 42, 190, 42)
        pygame.draw.rect(surface, connection_color, pill, border_radius=18)
        pill_text = self._body_font.render(connection_label, True, (255, 255, 255))
        surface.blit(pill_text, pill_text.get_rect(center=pill.center))
        if ui_state.busy_text:
            busy_text = self._small_font.render("BUSY: {0}".format(ui_state.busy_text), True, config.COLOR_ACCENT)
            surface.blit(busy_text, (config.WINDOW_WIDTH - 250, 92))

        self._draw_lines(
            surface,
            left_panel.x + 16,
            left_panel.y + 18,
            [
                "Drone Status",
                f"Battery: {self._format_optional_percent(telemetry.battery)}",
                f"Height: {self._format_optional_distance(telemetry.height)}",
                f"Temp: {self._format_optional_temp(telemetry.temperature)}",
                f"Flight: {self._format_optional_time(telemetry.flight_time)}",
                f"Signal: {telemetry.signal_strength.upper()}",
            ],
        )
        self._draw_controller_panel(surface, right_panel, controller_state, ui_state.takeoff_prompt)
        self._draw_bottom_bar(surface, bottom_bar, ui_state.highlighted_buttons)
        self._draw_alert_bar(surface, alert_bar, ui_state.alert_text, ui_state.alert_level)

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

        left_center = (panel_rect.x + 170, panel_rect.y + 185)
        right_center = (panel_rect.x + 520, panel_rect.y + 185)
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
        prompt_text = self._body_font.render(prompt, True, config.COLOR_ACCENT)
        surface.blit(prompt_text, (panel_rect.x + 24, panel_rect.bottom - 54))

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
        start_x = bar_rect.x + 26
        for index, legend in enumerate(self._button_legends):
            width = 205
            x = start_x + index * 222
            button_rect = pygame.Rect(x, bar_rect.y + 18, width, 64)
            active = highlighted_buttons.get(legend.key, False)
            fill = config.COLOR_ACCENT if active else (46, 46, 70)
            pygame.draw.rect(surface, fill, button_rect, border_radius=10)
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
        surface.fill(config.COLOR_BG)
        for x in range(0, config.WINDOW_WIDTH, 120):
            pygame.draw.line(surface, (18, 18, 18), (x, 0), (x - 180, config.WINDOW_HEIGHT), 1)

    @staticmethod
    def _format_optional_percent(value: Optional[int]) -> str:
        return "--" if value is None else f"{value}%"

    @staticmethod
    def _format_optional_distance(value: Optional[int]) -> str:
        return "--" if value is None else f"{value / 100:.1f} m"

    @staticmethod
    def _format_optional_temp(value: Optional[int]) -> str:
        return "--" if value is None else f"{value} C"

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
