from app.services import web_stats_service


def test_web_stats_service_helpers() -> None:
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is True
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False
    assert web_stats_service.normalize_required_token(" anon-1 ", "anonId") == "anon-1"
    assert web_stats_service.normalize_optional_string(" Asia/Seoul ", max_length=64) == "Asia/Seoul"
    assert web_stats_service.classify_device_type("Mozilla/5.0 (iPhone)", is_bot=False) == "mobile"
    assert web_stats_service.classify_browser_family("Mozilla/5.0 Chrome/130.0.0.0") == "chrome"
    assert web_stats_service.classify_os_family("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "windows"


def test_web_stats_service_parse_client_ts_returns_sql_datetime() -> None:
    parsed = web_stats_service.parse_client_ts(1763596800)
    assert len(parsed) == 19
    assert parsed.count(":") == 2


def test_web_stats_service_page_path_and_referrer_normalization() -> None:
    assert web_stats_service.normalize_page_path("/readme", allowed_paths=("/", "/readme")) == "/readme"
    assert web_stats_service.normalize_query_string("?utm_source=google", max_length=1024) == "utm_source=google"
    assert web_stats_service.normalize_referrer_url("https://example.com/path?a=1#x") == "https://example.com/path"
    assert (
        web_stats_service.normalize_referrer_domain(None, "https://Example.COM/path")
        == "example.com"
    )
