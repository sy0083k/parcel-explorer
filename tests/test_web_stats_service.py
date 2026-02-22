from app.services import web_stats_service


def test_web_stats_service_helpers() -> None:
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is True
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False
    assert web_stats_service.normalize_required_token(" anon-1 ", "anonId") == "anon-1"
    assert web_stats_service.normalize_optional_string(" Asia/Seoul ", max_length=64) == "Asia/Seoul"


def test_web_stats_service_parse_client_ts_returns_sql_datetime() -> None:
    parsed = web_stats_service.parse_client_ts(1763596800)
    assert len(parsed) == 19
    assert parsed.count(":") == 2
