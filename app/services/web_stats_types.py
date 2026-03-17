from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UserAgentContext:
    user_agent: str | None
    is_bot: bool
    browser_family: str
    device_type: str
    os_family: str


@dataclass(frozen=True)
class NormalizedWebVisitEvent:
    anon_id: str
    session_id: str
    event_type: str
    page_path: str
    page_query: str | None
    occurred_at: str
    client_tz: str | None
    client_lang: str | None
    platform: str | None
    referrer_url: str | None
    referrer_domain: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None
    screen_width: int | None
    screen_height: int | None
    viewport_width: int | None
    viewport_height: int | None
    user_agent: UserAgentContext


@dataclass(frozen=True)
class NormalizedWebVisitCore:
    anon_id: str
    session_id: str
    event_type: str
    page_path: str
    page_query: str | None
    occurred_at: str


@dataclass(frozen=True)
class ClientContext:
    client_tz: str | None
    client_lang: str | None
    platform: str | None
    screen_width: int | None
    screen_height: int | None
    viewport_width: int | None
    viewport_height: int | None


@dataclass(frozen=True)
class MarketingContext:
    referrer_url: str | None
    referrer_domain: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None


@dataclass(frozen=True)
class WebStatsWindow:
    since_utc: str
    today_utc_start: str
    today_utc_end: str


@dataclass(frozen=True)
class WebStatsQueryResult:
    total_visitors: int
    daily_visitors: int
    session_rows: list[dict[str, Any]]
    visitor_trend_rows: list[dict[str, Any]]
    top_referrers: list[dict[str, Any]]
    top_utm_sources: list[dict[str, Any]]
    top_utm_campaigns: list[dict[str, Any]]
    device_breakdown: list[dict[str, Any]]
    browser_breakdown: list[dict[str, Any]]
    top_page_paths: list[dict[str, Any]]
    channel_breakdown: list[dict[str, Any]]


@dataclass(frozen=True)
class SessionSummary:
    session_count: int
    avg_dwell_minutes: float
    sessions_by_date: dict[str, int]
    durations_by_date: dict[str, list[int]]
