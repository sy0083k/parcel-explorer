from app.services import web_stats_normalizers


def test_web_stats_normalizers_basic_helpers() -> None:
    assert web_stats_normalizers.normalize_required_token(" anon-1 ", "anonId") == "anon-1"
    assert web_stats_normalizers.normalize_optional_string(" Asia/Seoul ", max_length=64) == "Asia/Seoul"
    assert web_stats_normalizers.normalize_optional_int("320", min_value=0, max_value=20000) == 320
    assert web_stats_normalizers.normalize_query_string("?utm_source=google", max_length=1024) == "utm_source=google"


def test_web_stats_normalizers_page_and_referrer_handling() -> None:
    assert web_stats_normalizers.normalize_page_path("/readme", allowed_paths=("/", "/readme")) == "/readme"
    assert web_stats_normalizers.normalize_referrer_url("https://example.com/path?a=1#x") == "https://example.com/path"
    assert (
        web_stats_normalizers.normalize_referrer_domain(None, "https://Example.COM/path")
        == "example.com"
    )


def test_web_stats_normalizers_user_agent_classifiers() -> None:
    assert web_stats_normalizers.is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is True
    assert web_stats_normalizers.classify_device_type("Mozilla/5.0 (iPhone)", is_bot=False) == "mobile"
    assert web_stats_normalizers.classify_browser_family("Mozilla/5.0 Chrome/130.0.0.0") == "chrome"
    assert web_stats_normalizers.classify_os_family("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "windows"


def test_web_stats_normalizers_extract_utm_from_query() -> None:
    payload = web_stats_normalizers.extract_utm_from_query("utm_source=newsletter&utm_medium=email")
    assert payload == {
        "utmSource": "newsletter",
        "utmMedium": "email",
        "utmCampaign": None,
        "utmTerm": None,
        "utmContent": None,
    }
