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
            payload={
                "eventType": "visit_start",
                "anonId": " anon-1 ",
                "sessionId": " session-1 ",
                "pagePath": "/",
                "pageQuery": "?utm_source=google",
                "clientTs": 1763596800,
                "clientTz": " Asia/Seoul ",
                "clientLang": " ko-KR ",
                "platform": " iPhone ",
                "referrerUrl": "https://Example.com/search?q=test",
                "screenWidth": 1170,
                "screenHeight": 2532,
                "viewportWidth": 430,
                "viewportHeight": 932,
            },
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
