from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceError(Exception):
    status_code: int
    message: str
    log_reason: str | None = None

    def __str__(self) -> str:
        return self.message


class ValidationError(ServiceError):
    pass


class AuthError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass
