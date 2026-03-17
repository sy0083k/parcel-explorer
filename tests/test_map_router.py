import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.routers import map_router
from app.services.service_errors import ServiceError
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


def test_rate_limited_response_shape() -> None:
    response = map_router._rate_limited_response(7)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"


def test_raise_http_from_service_error_preserves_status_and_detail() -> None:
    with pytest.raises(HTTPException) as exc:
        map_router._raise_http_from_service_error(ServiceError(status_code=418, message="teapot"))

    assert exc.value.status_code == 418
    assert exc.value.detail == "teapot"
