"""Error taxonomy and handler — log and skip, never crash."""

import logging
from enum import Enum

logger = logging.getLogger("sweep")


class ErrorCategory(Enum):
    PERMISSION = "PERMISSION"
    SYMLINK = "SYMLINK"
    LOCKED = "LOCKED"
    NETWORK = "NETWORK"
    PATH_TOO_LONG = "PATH_TOO_LONG"
    ENCODING = "ENCODING"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


def classify_error(exc: Exception, path: str) -> ErrorCategory:
    """Classify an exception into an error category."""
    msg = str(exc).lower()

    if isinstance(exc, PermissionError):
        return ErrorCategory.PERMISSION
    if isinstance(exc, OSError):
        errno = getattr(exc, "errno", None)
        # Windows: ERROR_ACCESS_DENIED
        if errno == 5:
            return ErrorCategory.PERMISSION
        # Windows: ERROR_SHARING_VIOLATION
        if errno == 32:
            return ErrorCategory.LOCKED
        # Network errors
        if errno in (51, 64, 65, 67, 121):
            return ErrorCategory.NETWORK
        if "network" in msg:
            return ErrorCategory.NETWORK
        # Path too long
        if errno == 63 or "name too long" in msg or len(path) > 260:
            return ErrorCategory.PATH_TOO_LONG
    if isinstance(exc, UnicodeError):
        return ErrorCategory.ENCODING
    if isinstance(exc, TimeoutError):
        return ErrorCategory.TIMEOUT

    return ErrorCategory.UNKNOWN


def log_error(exc: Exception, path: str) -> ErrorCategory:
    """Classify and log an error. Returns the category."""
    category = classify_error(exc, path)
    logger.warning("ERROR [%s] %s — %s", category.value, path, exc)
    return category
