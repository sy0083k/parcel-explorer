from app.routers import map_router
from app.services.service_models import LandClickMapEventCommand, SearchMapEventCommand


def test_build_map_event_command_ignores_unrelated_payload_keys() -> None:
    command = map_router._build_map_event_command(
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
    command = map_router._build_map_event_command(
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
