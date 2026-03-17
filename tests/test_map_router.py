import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.routers import map_router
from app.services.service_errors import ServiceError


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


def test_build_web_visit_context_extracts_transport_primitives() -> None:
    request = type(
        "RequestStub",
        (),
        {
            "headers": {"user-agent": "Mozilla/5.0"},
            "app": type(
                "AppStub",
                (),
                {
                    "state": type(
                        "StateStub",
                        (),
                        {"config": type("ConfigStub", (), {"ALLOWED_WEB_TRACK_PATHS": ["/", "/map"]})()},
                    )()
                },
            )(),
        },
    )()

    context = map_router._build_web_visit_context(request)

    assert context.user_agent == "Mozilla/5.0"
    assert context.allowed_web_track_paths == ("/", "/map")
