from app.schemas.request import LoginRequest, UploadRequestMeta
from app.schemas.response import ApiErrorResponse, LoginResponse, UploadResponse, MapConfigResponse


def test_request_schemas_defaults():
    login = LoginRequest(username="user", password="pw")
    assert login.csrf_token == ""
    upload = UploadRequestMeta()
    assert upload.csrf_token == ""


def test_response_schemas():
    resp = LoginResponse(success=True)
    assert resp.success is True
    upload = UploadResponse(success=True, total=1, message="ok")
    assert upload.total == 1
    err = ApiErrorResponse(detail="err")
    assert err.detail == "err"
    cfg = MapConfigResponse(vworldKey="k", center=(1.0, 2.0), zoom=10)
    assert cfg.vworldKey == "k"
