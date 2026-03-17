from app.services.public_event_commands import (
    build_map_event_command,
    build_web_visit_event_command,
)
from app.services.service_models import (
    LandClickMapEventCommand,
    SearchMapEventCommand,
    UnknownMapEventCommand,
    WebVisitContext,
)


def test_build_map_event_command_ignores_unrelated_payload_keys() -> None:
    command = build_map_event_command(
        {
            "eventType": "search",
            "anonId": "anon-1",
            "minArea": 120,
            "searchTerm": "대산읍",
            "rawSearchTerm": " 대산읍 ",
            "unexpected": "ignored",
            "pagePath": "/admin",
        }
    )

    assert isinstance(command, SearchMapEventCommand)
    assert command.anon_id == "anon-1"
    assert command.min_area == 120
    assert command.search_term == "대산읍"


def test_build_map_event_command_builds_land_click_command() -> None:
    command = build_map_event_command(
        {
            "eventType": "land_click",
            "anonId": "anon-2",
            "landAddress": "충남 서산시 대산읍 독곶리 1-1",
            "landId": "99",
            "clickSource": "map_click",
        }
    )

    assert isinstance(command, LandClickMapEventCommand)
    assert command.land_address == "충남 서산시 대산읍 독곶리 1-1"
    assert command.land_id == "99"
    assert command.click_source == "map_click"


def test_build_map_event_command_builds_unknown_command() -> None:
    command = build_map_event_command({"eventType": "custom", "anonId": "anon-3"})

    assert isinstance(command, UnknownMapEventCommand)
    assert command.event_type == "custom"
    assert command.anon_id == "anon-3"


def test_build_web_visit_event_command_preserves_context_and_fields() -> None:
    context = WebVisitContext(user_agent="Mozilla/5.0", allowed_web_track_paths=("/", "/map"))

    command = build_web_visit_event_command(
        {
            "eventType": "visit_start",
            "anonId": "anon-web-1",
            "sessionId": "session-web-1",
            "pagePath": "/",
            "clientTs": 1763596800,
            "utmSource": "newsletter",
            "viewportWidth": 1280,
        },
        context=context,
    )

    assert command.context == context
    assert command.event_type == "visit_start"
    assert command.anon_id == "anon-web-1"
    assert command.session_id == "session-web-1"
    assert command.page_path == "/"
    assert command.client_ts == 1763596800
    assert command.utm_source == "newsletter"
    assert command.viewport_width == 1280
