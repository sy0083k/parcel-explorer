from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services import web_stats_ingest
from app.services.service_models import WebVisitContext, WebVisitEventCommand
from app.services.web_stats_types import (
    ClientContext,
    MarketingContext,
    NormalizedWebVisitCore,
    UserAgentContext,
)


def test_web_stats_ingest_persists_normalized_and_derived_fields(
    db_path: object,
) -> None:
    with db_connection(row_factory=True) as conn:
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()

    web_stats_ingest.record_web_visit_event(
        WebVisitEventCommand(
            event_type="visit_start",
            anon_id=" anon-1 ",
            session_id=" session-1 ",
            page_path="/",
            page_query="?utm_source=google",
            client_ts=1763596800,
            client_tz=" Asia/Seoul ",
            client_lang=" ko-KR ",
            platform=" iPhone ",
            referrer_url="https://Example.com/search?q=test",
            screen_width=1170,
            screen_height=2532,
            viewport_width=430,
            viewport_height=932,
            context=WebVisitContext(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                allowed_web_track_paths=("/",),
            ),
        )
    )

    with db_connection(row_factory=True) as conn:
        row = conn.execute("SELECT * FROM web_visit_event").fetchone()

    assert row is not None
    assert row["anon_id"] == "anon-1"
    assert row["session_id"] == "session-1"
    assert row["page_query"] == "utm_source=google"
    assert row["client_tz"] == "Asia/Seoul"
    assert row["referrer_url"] == "https://Example.com/search"
    assert row["referrer_domain"] == "example.com"
    assert row["browser_family"] == "safari"
    assert row["device_type"] == "mobile"
    assert row["os_family"] == "macos"


def test_web_stats_ingest_normalize_web_visit_core() -> None:
    core = web_stats_ingest.normalize_web_visit_core(
        WebVisitEventCommand(
            event_type="visit_start",
            anon_id=" anon-1 ",
            session_id=" session-1 ",
            page_path="/",
            page_query="?utm_source=google",
            client_ts=1763596800,
            context=WebVisitContext(
                user_agent=None,
                allowed_web_track_paths=("/",),
            ),
        ),
        WebVisitContext(
            user_agent=None,
            allowed_web_track_paths=("/",),
        ),
    )

    assert core.anon_id == "anon-1"
    assert core.session_id == "session-1"
    assert core.event_type == "visit_start"
    assert core.page_path == "/"
    assert core.page_query == "utm_source=google"


def test_web_stats_ingest_normalize_client_context() -> None:
    context = web_stats_ingest.normalize_client_context(
        WebVisitEventCommand(
            event_type="visit_start",
            anon_id="anon-1",
            session_id="session-1",
            page_path="/",
            client_tz=" Asia/Seoul ",
            client_lang=" ko-KR ",
            platform=" Linux ",
            screen_width="1920",
            screen_height="1080",
            viewport_width="1280",
            viewport_height="800",
            context=WebVisitContext(),
        )
    )

    assert context.client_tz == "Asia/Seoul"
    assert context.client_lang == "ko-KR"
    assert context.platform == "Linux"
    assert context.screen_width == 1920
    assert context.viewport_height == 800


def test_web_stats_ingest_normalize_marketing_context() -> None:
    context = web_stats_ingest.normalize_marketing_context(
        WebVisitEventCommand(
            event_type="visit_start",
            anon_id="anon-1",
            session_id="session-1",
            page_path="/",
            referrer_url="https://Example.com/path?q=1",
            referrer_domain=None,
            utm_source=" newsletter ",
            utm_medium=" email ",
            context=WebVisitContext(),
        )
    )

    assert context.referrer_url == "https://Example.com/path"
    assert context.referrer_domain == "example.com"
    assert context.utm_source == "newsletter"
    assert context.utm_medium == "email"


def test_web_stats_ingest_derive_user_agent_context() -> None:
    context = web_stats_ingest.derive_user_agent_context(
        WebVisitContext(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1",
            allowed_web_track_paths=("/",),
        )
    )

    assert context.user_agent is not None
    assert context.is_bot is False
    assert context.device_type == "mobile"


def test_web_stats_ingest_assemble_normalized_web_visit_event() -> None:
    event = web_stats_ingest.assemble_normalized_web_visit_event(
        NormalizedWebVisitCore(
            anon_id="anon-1",
            session_id="session-1",
            event_type="visit_start",
            page_path="/",
            page_query="utm_source=google",
            occurred_at="2026-02-20 00:00:00",
        ),
        ClientContext(
            client_tz="Asia/Seoul",
            client_lang="ko-KR",
            platform="Linux",
            screen_width=1920,
            screen_height=1080,
            viewport_width=1280,
            viewport_height=800,
        ),
        MarketingContext(
            referrer_url="https://google.com/search",
            referrer_domain="google.com",
            utm_source="google",
            utm_medium="search",
            utm_campaign=None,
            utm_term=None,
            utm_content=None,
        ),
        UserAgentContext(
            user_agent="Mozilla/5.0",
            is_bot=False,
            browser_family="chrome",
            device_type="desktop",
            os_family="linux",
        ),
    )

    assert event.anon_id == "anon-1"
    assert event.referrer_domain == "google.com"
    assert event.user_agent.browser_family == "chrome"
