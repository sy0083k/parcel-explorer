from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services import web_stats_ingest
from app.services.service_models import RequestMetadata, WebVisitEventCommand


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
            metadata=RequestMetadata(
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
            metadata=RequestMetadata(
                user_agent=None,
                allowed_web_track_paths=("/",),
            ),
        ),
        RequestMetadata(
            user_agent=None,
            allowed_web_track_paths=("/",),
        ),
    )

    assert core.anon_id == "anon-1"
    assert core.session_id == "session-1"
    assert core.event_type == "visit_start"
    assert core.page_path == "/"
    assert core.page_query == "utm_source=google"
