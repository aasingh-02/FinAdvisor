"""
app/utils/logger.py
───────────────────
Centralized application logging configuration and secure server-side exception logging (SEC-VULN-011).

Security & Privacy Guarantees:
- Captures essential debugging context: timestamp, exception type, request method,
  request path, and full stack trace.
- Zero sensitive data exposure:
  * NEVER logs request or response bodies (passwords, financial profile amounts).
  * NEVER logs headers (Authorization, Cookie, API keys).
  * NEVER logs cookies or session tokens.
  * Strictly uses request.url.path to prevent query string secret leakage.
- Non-fatal logging: failures in the logging system (e.g., I/O or formatter errors)
  never crash the application or alter HTTP responses.
- Standard Python library: uses python standard `logging` module.
"""

import logging
import sys
from typing import Optional

from starlette.requests import Request

# Standard log format with ISO-style timestamp
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("app.exceptions")


def setup_logging(level: int = logging.INFO) -> None:
    """
    Initialize standard library logging with consistent format and timestamp.
    Idempotent: will not duplicate existing handlers.
    """
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
    else:
        for handler in root_logger.handlers:
            if not handler.formatter:
                handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))


def log_unexpected_exception(
    request: Optional[Request],
    exc: Exception,
    custom_logger: Optional[logging.Logger] = None,
) -> None:
    """
    Safely record an unhandled exception to server-side logs with stack trace.

    Includes:
    - Timestamp (via logging formatter)
    - Exception type
    - Request method
    - Request path
    - Full stack trace (via exc_info)

    Excludes (strictly prohibited):
    - Passwords
    - Session tokens / token hashes
    - Authorization headers
    - Cookies
    - API keys
    - Financial profile values
    - Full request or response bodies
    """
    target_logger = custom_logger or logger
    try:
        method = "UNKNOWN"
        path = "UNKNOWN"
        if request is not None:
            method = getattr(request, "method", "UNKNOWN")
            url = getattr(request, "url", None)
            if url and hasattr(url, "path"):
                # Use request.url.path strictly (excludes query strings which might contain secrets)
                path = url.path

        exc_type = type(exc).__name__

        target_logger.error(
            "Unhandled server exception: method=%s path=%s exception_type=%s",
            method,
            path,
            exc_type,
            exc_info=exc,
            extra={
                "request_method": method,
                "request_path": path,
                "exception_type": exc_type,
            },
        )
    except Exception as log_err:
        # Non-fatal fallback to sys.stderr if logging infrastructure encounters an error
        try:
            sys.stderr.write(
                f"[LOGGING_ERROR] Failed to record unexpected exception: {log_err}\n"
            )
        except Exception:
            pass
