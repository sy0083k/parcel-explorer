from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from app.dependencies import validate_csrf_token


def handle_public_download_upload(
    request: Request,
    *,
    csrf_token: str,
    file: UploadFile,
) -> dict[str, Any]:
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    config = request.app.state.config
    target_dir = _target_dir(config.BASE_DIR, config.PUBLIC_DOWNLOAD_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = (file.filename or "").strip()
    if not original_name:
        raise HTTPException(status_code=400, detail="업로드 파일명이 비어 있습니다.")

    ext = _file_extension(original_name)
    allowed_exts = {entry.lower().lstrip(".") for entry in config.PUBLIC_DOWNLOAD_ALLOWED_EXTS}
    if ext not in allowed_exts:
        allow_text = ", ".join(sorted(f".{item}" for item in allowed_exts))
        raise HTTPException(status_code=400, detail=f"허용되지 않은 파일 형식입니다. 허용: {allow_text}")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size_bytes = int(config.PUBLIC_DOWNLOAD_MAX_SIZE_MB) * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"파일 용량 제한({config.PUBLIC_DOWNLOAD_MAX_SIZE_MB}MB)을 초과했습니다.",
        )

    stored_name = f"current.{ext}"
    target_path = target_dir / stored_name

    # Write to temp file first, then replace atomically.
    with tempfile.NamedTemporaryFile(delete=False, dir=target_dir, prefix="upload-", suffix=f".{ext}") as tmp:
        tmp_path = Path(tmp.name)
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)

    tmp_path.replace(target_path)

    meta = {
        "original_filename": original_name,
        "stored_filename": stored_name,
        "content_type": (file.content_type or "").strip(),
        "uploaded_at": datetime.now(UTC).isoformat(),
        "size_bytes": file_size,
    }
    _meta_path(target_dir).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "success": True,
        "message": "공개 다운로드 파일이 업데이트되었습니다.",
        "filename": original_name,
        "uploadedAt": meta["uploaded_at"],
        "sizeBytes": file_size,
    }


def get_public_download_file_response(request: Request) -> Response:
    config = request.app.state.config
    target_dir = _target_dir(config.BASE_DIR, config.PUBLIC_DOWNLOAD_DIR)
    meta_file = _meta_path(target_dir)
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="다운로드 가능한 파일이 없습니다.")

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="다운로드 메타데이터가 손상되었습니다.") from exc

    stored_name = str(meta.get("stored_filename", "")).strip()
    original_name = str(meta.get("original_filename", "")).strip() or stored_name
    if not stored_name:
        raise HTTPException(status_code=404, detail="다운로드 가능한 파일이 없습니다.")

    file_path = target_dir / stored_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="다운로드 파일을 찾을 수 없습니다.")

    content_type = str(meta.get("content_type", "")).strip() or "application/octet-stream"
    quoted = quote(original_name)
    return FileResponse(
        path=file_path,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


def get_public_download_meta(request: Request) -> dict[str, Any]:
    config = request.app.state.config
    target_dir = _target_dir(config.BASE_DIR, config.PUBLIC_DOWNLOAD_DIR)
    meta_file = _meta_path(target_dir)
    if not meta_file.exists():
        return {"exists": False}
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return {"exists": False}
    meta["exists"] = True
    return meta


def _target_dir(base_dir: str, config_path: str) -> Path:
    raw = Path(config_path)
    if raw.is_absolute():
        return raw
    return Path(base_dir) / raw


def _meta_path(target_dir: Path) -> Path:
    return target_dir / "current.json"


def _file_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if not suffix:
        raise HTTPException(status_code=400, detail="파일 확장자가 필요합니다.")
    return suffix
