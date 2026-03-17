from typing import Any

from fastapi import FastAPI
from starlette.requests import Request

from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services import web_stats_ingest


def _make_request(
    app: FastAPI,
    *,
    user_agent: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/web-events",
        "headers": [(b"user-agent", user_agent.encode())],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "query_string": b"",
        "app": app,
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_web_stats_ingest_persists_normalized_and_derived_fields(
    build_app: Any,
    db_path: object,
) -> None:
    app = build_app()
    with db_connection(row_factory=True) as conn:
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()

    request = _make_request(app)
    web_stats_ingest.record_web_visit_event(
        {
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
        request,
        allowed_paths=("/",),
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
