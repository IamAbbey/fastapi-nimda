from __future__ import annotations

from dataclasses import dataclass, field


class FastAPINimdaError(Exception):
    """Base exception for package-specific errors."""


class AdminConfigurationError(FastAPINimdaError):
    """Raised when admin configuration cannot be supported safely."""


class PermissionDeniedError(FastAPINimdaError):
    """Raised when a model admin denies the requested operation."""


class UnknownAdminActionError(FastAPINimdaError):
    """Raised when a submitted admin action is not registered."""


class UnsupportedPrimaryKeyError(AdminConfigurationError):
    """Raised when a model primary key shape is unsupported."""


class UnsupportedRelationshipError(AdminConfigurationError):
    """Raised when a relationship shape is unsupported."""


class UnsupportedFileUploadError(FastAPINimdaError):
    """Raised when a form submits files but file handling is not implemented."""


@dataclass(frozen=True)
class DatabaseErrorSummary:
    message: str
    field_names: list[str] = field(default_factory=list)
