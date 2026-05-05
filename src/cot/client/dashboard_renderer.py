from __future__ import annotations

from time import monotonic

import pygame

from cot.client.dashboard_state import DashboardAlert
from cot.client.dashboard_state import DashboardState
from cot.client.dashboard_state import DEFAULT_ALERT_DURATION_S
from cot.client.dashboard_state import RECENT_EVENT_LIMIT

ALERT_BANNERS_VISIBLE = 2


def _truncate_middle(value: str, keep: int = 8) -> str:
    if len(value) <= keep * 2 + 3:
        return value
    return f"{value[:keep]}...{value[-keep:]}"


def _draw_panel(screen: pygame.Surface, rect: pygame.Rect, border_color: tuple[int, int, int]) -> None:
    pygame.draw.rect(screen, (27, 33, 44), rect, border_radius=8)
    pygame.draw.rect(screen, border_color, rect, width=1, border_radius=8)


def _draw_kv_rows(
    screen: pygame.Surface,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    rect: pygame.Rect,
    rows: list[tuple[str, str]],
    label_color: tuple[int, int, int] = (150, 164, 186),
    value_color: tuple[int, int, int] = (228, 233, 241),
    row_height: int = 22,
) -> None:
    label_x = rect.left
    value_x = rect.left + 172
    y = rect.top
    for label, value in rows:
        label_surface = label_font.render(label, True, label_color)
        value_surface = value_font.render(value, True, value_color)
        screen.blit(label_surface, (label_x, y))
        screen.blit(value_surface, (value_x, y))
        y += row_height


def _draw_alerts(
    screen: pygame.Surface,
    alert_font: pygame.font.Font,
    alerts: list[DashboardAlert],
) -> None:
    if not alerts:
        return
    now = monotonic()
    banner_y = 46
    banner_height = 20
    max_visible = min(len(alerts), ALERT_BANNERS_VISIBLE)
    for index in range(max_visible):
        alert = alerts[index]
        remaining = max(0.0, alert.expires_at - now)
        alpha_ratio = min(1.0, remaining / DEFAULT_ALERT_DURATION_S)
        alpha = int(60 + 150 * alpha_ratio)
        text_surface = alert_font.render(alert.text, True, alert.color)
        banner_width = min(screen.get_width() - 24, text_surface.get_width() + 20)
        banner_x = (screen.get_width() - banner_width) // 2
        y = banner_y + index * (banner_height + 4)
        banner_surface = pygame.Surface((banner_width, banner_height), pygame.SRCALPHA)
        border_surface = pygame.Surface((banner_width, banner_height), pygame.SRCALPHA)
        banner_surface.fill((24, 30, 40, alpha))
        border_surface.fill((0, 0, 0, 0))
        pygame.draw.rect(
            border_surface,
            (*alert.color, min(220, alpha + 40)),
            border_surface.get_rect(),
            width=1,
            border_radius=5,
        )
        screen.blit(banner_surface, (banner_x, y))
        screen.blit(border_surface, (banner_x, y))
        text_x = banner_x + max(10, (banner_width - text_surface.get_width()) // 2)
        screen.blit(text_surface, (text_x, y + 2))


def _draw_header(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    label_font: pygame.font.Font,
) -> None:
    title_surface = title_font.render("CARLA Observability Toolkit", True, (228, 233, 241))
    subtitle_surface = label_font.render("Client Telemetry Dashboard", True, (150, 164, 186))
    screen.blit(title_surface, (14, 10))
    screen.blit(subtitle_surface, (14, 34))


def _draw_run_panel(
    screen: pygame.Surface,
    section_font: pygame.font.Font,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    run_panel: pygame.Rect,
    status: str,
    status_color: tuple[int, int, int],
    short_run_id: str,
    experiment_id: str,
    config_name: str,
    scenario_label: str,
    seed: str,
) -> None:
    _draw_panel(screen, run_panel, (49, 61, 79))
    section_color = (174, 188, 211)
    run_title = section_font.render("RUN INFO", True, section_color)
    screen.blit(run_title, (run_panel.left + 12, run_panel.top + 10))

    status_label = label_font.render("Run Status", True, (150, 164, 186))
    status_value = section_font.render(status, True, status_color)
    screen.blit(status_label, (run_panel.left + 12, run_panel.top + 38))
    screen.blit(status_value, (run_panel.left + 172, run_panel.top + 36))
    _draw_kv_rows(
        screen,
        label_font,
        value_font,
        pygame.Rect(run_panel.left + 12, run_panel.top + 64, run_panel.width - 24, 84),
        [
            ("Run ID", short_run_id),
            ("Experiment", experiment_id),
            ("Config", config_name),
            ("Scenario", scenario_label),
            ("Seed", seed),
        ],
        row_height=19,
    )


def _draw_metrics_panel(
    screen: pygame.Surface,
    section_font: pygame.font.Font,
    label_font: pygame.font.Font,
    metric_font: pygame.font.Font,
    speed_metric_font: pygame.font.Font,
    metrics_panel: pygame.Rect,
    speed_kmh: float,
    accel_mag: float,
    steering: float,
    high_speed_warning: bool,
) -> None:
    _draw_panel(screen, metrics_panel, (49, 61, 79))
    section_color = (174, 188, 211)
    metrics_title = section_font.render("VEHICLE METRICS", True, section_color)
    screen.blit(metrics_title, (metrics_panel.left + 12, metrics_panel.top + 10))

    metric_y = metrics_panel.top + 38
    speed_label = label_font.render("Speed", True, (150, 164, 186))
    accel_label = label_font.render("Acceleration (|a|)", True, (150, 164, 186))
    steer_label = label_font.render("Steering", True, (150, 164, 186))
    speed_value_color = (255, 182, 74) if high_speed_warning else (236, 242, 252)
    speed_value = speed_metric_font.render(f"{speed_kmh:.1f} km/h", True, speed_value_color)
    accel_value = metric_font.render(f"{accel_mag:.2f} m/s^2", True, (228, 233, 241))
    steer_value = metric_font.render(f"{steering:.3f}", True, (228, 233, 241))

    speed_x = metrics_panel.left + 12
    accel_x = metrics_panel.left + metrics_panel.width // 3 + 8
    steer_x = metrics_panel.left + (2 * metrics_panel.width) // 3 + 8
    screen.blit(speed_label, (speed_x, metric_y))
    screen.blit(accel_label, (accel_x, metric_y))
    screen.blit(steer_label, (steer_x, metric_y))
    screen.blit(speed_value, (speed_x, metric_y + 14))
    screen.blit(accel_value, (accel_x, metric_y + 16))
    screen.blit(steer_value, (steer_x, metric_y + 16))


def _draw_events_panel(
    screen: pygame.Surface,
    section_font: pygame.font.Font,
    value_font: pygame.font.Font,
    events_panel: pygame.Rect,
    events: list[str],
) -> None:
    _draw_panel(screen, events_panel, (49, 61, 79))
    section_color = (174, 188, 211)
    events_title = section_font.render("EVENTS", True, section_color)
    screen.blit(events_title, (events_panel.left + 12, events_panel.top + 10))

    event_start_x = events_panel.left + 12
    event_start_y = events_panel.top + 34
    event_lines = events[:RECENT_EVENT_LIMIT] if events else ["(none)"]
    for index, event_line in enumerate(event_lines):
        event_surface = value_font.render(event_line, True, (211, 219, 233))
        screen.blit(event_surface, (event_start_x, event_start_y + index * 20))


def render_dashboard(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    section_font: pygame.font.Font,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    metric_font: pygame.font.Font,
    speed_metric_font: pygame.font.Font,
    dashboard: DashboardState,
) -> None:
    screen.fill((19, 24, 32))
    (
        status,
        run_id,
        experiment_id,
        config_name,
        scenario_label,
        seed,
        speed_kmh,
        accel_mag,
        steering,
        high_speed_warning,
        events,
        alerts,
    ) = dashboard.snapshot()

    status_color = (86, 214, 128) if status == "RUNNING" else (235, 98, 98) if status == "STOPPED" else (229, 233, 240)
    short_run_id = _truncate_middle(run_id) if run_id != "-" else run_id
    _draw_header(screen, title_font, label_font)

    panel_width = screen.get_width() - 24
    run_panel = pygame.Rect(12, 70, panel_width, 156)
    metrics_panel = pygame.Rect(12, 244, panel_width, 94)
    events_panel = pygame.Rect(12, 356, panel_width, 98)

    _draw_run_panel(
        screen=screen,
        section_font=section_font,
        label_font=label_font,
        value_font=value_font,
        run_panel=run_panel,
        status=status,
        status_color=status_color,
        short_run_id=short_run_id,
        experiment_id=experiment_id,
        config_name=config_name,
        scenario_label=scenario_label,
        seed=seed,
    )
    _draw_metrics_panel(
        screen=screen,
        section_font=section_font,
        label_font=label_font,
        metric_font=metric_font,
        speed_metric_font=speed_metric_font,
        metrics_panel=metrics_panel,
        speed_kmh=speed_kmh,
        accel_mag=accel_mag,
        steering=steering,
        high_speed_warning=high_speed_warning,
    )
    _draw_events_panel(
        screen=screen,
        section_font=section_font,
        value_font=value_font,
        events_panel=events_panel,
        events=events,
    )
    _draw_alerts(screen, value_font, alerts)
    pygame.display.flip()
