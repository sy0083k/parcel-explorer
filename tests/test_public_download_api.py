import io
import re

import httpx
import pytest

CSRF_PATTERN = r'name="csrf_token" value="([^"]+)"'


async def _login_as_admin(client: httpx.AsyncClient) -> None:
    login_page = await client.get("/admin/login")
    match = re.search(CSRF_PATTERN, login_page.text)
    assert match is not None

    response = await client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin-password",
            "csrf_token": match.group(1),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


async def _get_admin_csrf(client: httpx.AsyncClient) -> str:
    admin_page = await client.get("/admin/")
    assert admin_page.status_code == 200
    match = re.search(r'id="csrfToken" value="([^"]+)"', admin_page.text)
    assert match is not None
    return match.group(1)


@pytest.mark.anyio
async def test_public_download_returns_404_when_missing(
    build_app: object,
    tmp_path: object,
) -> None:
    app = build_app()
    app.state.config.PUBLIC_DOWNLOAD_DIR = str(tmp_path / "public_download")
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/public-download")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_admin_upload_and_public_download_flow(
    build_app: object,
    tmp_path: object,
) -> None:
    app = build_app()
    app.state.config.PUBLIC_DOWNLOAD_DIR = str(tmp_path / "public_download")
    app.state.config.PUBLIC_DOWNLOAD_MAX_SIZE_MB = 5
    app.state.config.PUBLIC_DOWNLOAD_ALLOWED_EXTS = ("pdf", "csv", "xlsx")

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _login_as_admin(client)
        csrf_token = await _get_admin_csrf(client)

        file_bytes = io.BytesIO(b"%PDF-1.7\\nFake\\n")
        upload = await client.post(
            "/admin/public-download/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("prepared-list.pdf", file_bytes, "application/pdf")},
        )
        assert upload.status_code == 200
        payload = upload.json()
        assert payload["success"] is True
        assert payload["filename"] == "prepared-list.pdf"

        downloaded = await client.get("/api/public-download")
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-1.7")
        assert "attachment;" in downloaded.headers.get("content-disposition", "")


@pytest.mark.anyio
async def test_public_download_rate_limit_blocks_and_applies_on_v1_route(
    build_app: object,
    tmp_path: object,
) -> None:
    app = build_app()
    app.state.config.PUBLIC_DOWNLOAD_DIR = str(tmp_path / "public_download")
    app.state.config.PUBLIC_DOWNLOAD_MAX_SIZE_MB = 5
    app.state.config.PUBLIC_DOWNLOAD_ALLOWED_EXTS = ("pdf", "csv", "xlsx")
    app.state.config.PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE = 2

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _login_as_admin(client)
        csrf_token = await _get_admin_csrf(client)

        upload = await client.post(
            "/admin/public-download/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("prepared-list.pdf", io.BytesIO(b"%PDF-1.7\\nFake\\n"), "application/pdf")},
        )
        assert upload.status_code == 200

        response_1 = await client.get("/api/public-download")
        response_2 = await client.get("/api/v1/public-download")
        response_3 = await client.get("/api/public-download")

        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert response_3.status_code == 429
        assert int(response_3.headers.get("retry-after", "0")) >= 1


@pytest.mark.anyio
async def test_public_download_rate_limit_is_keyed_by_client_ip(
    build_app: object,
    tmp_path: object,
) -> None:
    app = build_app()
    app.state.config.PUBLIC_DOWNLOAD_DIR = str(tmp_path / "public_download")
    app.state.config.PUBLIC_DOWNLOAD_MAX_SIZE_MB = 5
    app.state.config.PUBLIC_DOWNLOAD_ALLOWED_EXTS = ("pdf", "csv", "xlsx")
    app.state.config.PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE = 1

    admin_transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=admin_transport, base_url="http://testserver") as admin_client:
        await _login_as_admin(admin_client)
        csrf_token = await _get_admin_csrf(admin_client)
        upload = await admin_client.post(
            "/admin/public-download/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("prepared-list.pdf", io.BytesIO(b"%PDF-1.7\\nFake\\n"), "application/pdf")},
        )
        assert upload.status_code == 200

    transport_a = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    transport_b = httpx.ASGITransport(app=app, client=("127.0.0.2", 50000))
    async with httpx.AsyncClient(transport=transport_a, base_url="http://testserver") as client_a:
        first = await client_a.get("/api/public-download")
        blocked = await client_a.get("/api/public-download")

    async with httpx.AsyncClient(transport=transport_b, base_url="http://testserver") as client_b:
        other_ip = await client_b.get("/api/public-download")

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert other_ip.status_code == 200


@pytest.mark.anyio
async def test_public_download_upload_rejects_disallowed_extension(
    build_app: object,
    tmp_path: object,
) -> None:
    app = build_app()
    app.state.config.PUBLIC_DOWNLOAD_DIR = str(tmp_path / "public_download")
    app.state.config.PUBLIC_DOWNLOAD_ALLOWED_EXTS = ("pdf", "csv", "xlsx")

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _login_as_admin(client)
        csrf_token = await _get_admin_csrf(client)

        bad_file = io.BytesIO(b"binary")
        response = await client.post(
            "/admin/public-download/upload",
            data={"csrf_token": csrf_token},
            files={"file": ("evil.exe", bad_file, "application/octet-stream")},
        )
        assert response.status_code == 400
