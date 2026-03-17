from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.service_errors import AuthError, NotFoundError, ValidationError
from app.services.service_models import RequestContext, UploadedFileInput


@dataclass(frozen=True)
class PublicDownloadConfig:
    base_dir: str
    public_download_dir: str
    allowed_exts: tuple[str, ...]
    max_size_mb: int


@dataclass(frozen=True)
class PublicDownloadUploadCommand:
    context: RequestContext
    config: PublicDownloadConfig


@dataclass(frozen=True)
class PublicDownloadUploadResult:
    success: bool
    message: str
    filename: str
    uploaded_at: str
    size_bytes: int


@dataclass(frozen=True)
class PublicDownloadFileResult:
    path: Path
    media_type: str
    download_filename: str


def handle_public_download_upload(
    command: PublicDownloadUploadCommand,
    *,
    file_input: UploadedFileInput,
) -> PublicDownloadUploadResult:
    if not command.context.csrf_valid:
        raise AuthError(status_code=403, message="CSRF 토큰 검증에 실패했습니다.")

    target_dir = _target_dir(command.config.base_dir, command.config.public_download_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = file_input.filename.strip()
    if not original_name:
        raise ValidationError(status_code=400, message="업로드 파일명이 비어 있습니다.")

    ext = _file_extension(original_name)
    allowed_exts = {entry.lower().lstrip(".") for entry in command.config.allowed_exts}
    if ext not in allowed_exts:
        allow_text = ", ".join(sorted(f".{item}" for item in allowed_exts))
        raise ValidationError(
            status_code=400,
            message=f"허용되지 않은 파일 형식입니다. 허용: {allow_text}",
        )

    file_input.file.seek(0, os.SEEK_END)
    file_size = file_input.file.tell()
    file_input.file.seek(0)
    max_size_bytes = int(command.config.max_size_mb) * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValidationError(
            status_code=400,
            message=f"파일 용량 제한({command.config.max_size_mb}MB)을 초과했습니다.",
        )

    stored_name = f"current.{ext}"
    target_path = target_dir / stored_name
    sha256 = hashlib.sha256()
    with tempfile.NamedTemporaryFile(delete=False, dir=target_dir, prefix="upload-", suffix=f".{ext}") as tmp:
        tmp_path = Path(tmp.name)
        while True:
            chunk = file_input.file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
            sha256.update(chunk)

    tmp_path.replace(target_path)
    meta = {
        "original_filename": original_name,
        "stored_filename": stored_name,
        "content_type": file_input.content_type.strip(),
        "uploaded_at": datetime.now(UTC).isoformat(),
        "size_bytes": file_size,
        "sha256": sha256.hexdigest(),
    }
    _meta_path(target_dir).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return PublicDownloadUploadResult(
        success=True,
        message="공개 다운로드 파일이 업데이트되었습니다.",
        filename=original_name,
        uploaded_at=str(meta["uploaded_at"]),
        size_bytes=file_size,
    )


def get_public_download_file(config: PublicDownloadConfig) -> PublicDownloadFileResult:
    target_dir = _target_dir(config.base_dir, config.public_download_dir)
    meta_file = _meta_path(target_dir)
    if not meta_file.exists():
        raise NotFoundError(status_code=404, message="다운로드 가능한 파일이 없습니다.")

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(status_code=500, message="다운로드 메타데이터가 손상되었습니다.") from exc

    stored_name = str(meta.get("stored_filename", "")).strip()
    original_name = str(meta.get("original_filename", "")).strip() or stored_name
    if not stored_name:
        raise NotFoundError(status_code=404, message="다운로드 가능한 파일이 없습니다.")

    file_path = target_dir / stored_name
    if not file_path.exists():
        raise NotFoundError(status_code=404, message="다운로드 파일을 찾을 수 없습니다.")

    content_type = str(meta.get("content_type", "")).strip() or "application/octet-stream"
    return PublicDownloadFileResult(
        path=file_path,
        media_type=content_type,
        download_filename=original_name,
    )


def get_public_download_meta(config: PublicDownloadConfig) -> dict[str, Any]:
    target_dir = _target_dir(config.base_dir, config.public_download_dir)
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
        raise ValidationError(status_code=400, message="파일 확장자가 필요합니다.")
    return suffix
