"""
Logging configuration for Agentic CBA Indicators.

Provides a consistent logging setup for the package and scripts.
Use `setup_logging()` at the entry point to configure logging.

Supports two output formats:
- **text** (default): Human-readable format suitable for development
- **json**: Machine-parseable JSON Lines format for production/aggregation

Configuration via environment variables:
- AGENTIC_CBA_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR)
- AGENTIC_CBA_LOG_FORMAT: Output format ("text" or "json")

Usage:
    from agentic_cba_indicators.logging_config import get_logger, setup_logging

    # At entry point (e.g., cli.py or script main)
    setup_logging(level=logging.INFO)

    # In any module
    logger = get_logger(__name__)
    logger.info("Processing started")
    logger.debug("Detailed info: %s", data)

    # With structured context (JSON format)
    logger.info("User action", extra={"user_id": 123, "action": "search"})
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import TextIO

# Default log level (can be overridden via environment variable)
DEFAULT_LOG_LEVEL = os.environ.get("AGENTIC_CBA_LOG_LEVEL", "WARNING")

# Default log format (can be overridden via environment variable)
# Valid values: "text" (default), "json"
DEFAULT_LOG_FORMAT_TYPE = os.environ.get("AGENTIC_CBA_LOG_FORMAT", "text").lower()

# Package-level logger name
LOGGER_NAME = "agentic_cba_indicators"

# Default format for log messages (text mode)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)s: %(message)s"

_logging_configured = False

# Correlation ID context (per request/tool call)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(value: str | None) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current context."""
    return _correlation_id.get()


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into log records when present."""

    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging output.

    Outputs one JSON object per log line (JSON Lines format), suitable for
    log aggregation systems like ELK, Splunk, CloudWatch Logs, etc.

    Standard fields:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level name (DEBUG, INFO, etc.)
    - logger: Logger name
    - message: Formatted log message

    Optional fields (when present):
    - exc_info: Exception traceback if an exception was logged
    - extra: Any additional context passed via logger.info(..., extra={...})

    Example output:
        {"timestamp": "2026-01-18T12:34:56.789Z", "level": "INFO", "logger": "module", "message": "Hello"}
    """

    # Fields that are part of standard LogRecord (not user-provided extra)
    RESERVED_ATTRS = frozenset(
        {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        # Build base record
        log_dict: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add source location for debugging
        if record.levelno >= logging.DEBUG:
            log_dict["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_dict["exc_info"] = "".join(
                traceback.format_exception(*record.exc_info)
            ).strip()

        # Add correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_dict["correlation_id"] = correlation_id

        # Add any extra fields (user-provided context)
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.RESERVED_ATTRS and not key.startswith("_")
        }

        if extra:
            log_dict["extra"] = extra

        # Serialize to JSON (single line, no pretty-print)
        return json.dumps(log_dict, default=str, ensure_ascii=False)


def get_json_formatter() -> JSONFormatter:
    """
    Get a JSON formatter instance for structured logging.

    Returns:
        JSONFormatter instance
    """
    return JSONFormatter()


def get_text_formatter(verbose: bool = False) -> logging.Formatter:
    """
    Get a text formatter instance for human-readable logging.

    Args:
        verbose: If True, use detailed format with timestamps

    Returns:
        Standard Formatter instance
    """
    format_string = LOG_FORMAT if verbose else LOG_FORMAT_SIMPLE
    return logging.Formatter(format_string)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Operation complete")
    """
    return logging.getLogger(name)


def setup_logging(
    level: int | str | None = None,
    stream: TextIO | None = None,
    format_string: str | None = None,
    verbose: bool = False,
    log_format: str | None = None,
) -> None:
    """
    Configure logging for the package.

    Should be called once at application startup (e.g., in cli.py main()).
    Subsequent calls are no-ops by default.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Default: WARNING
               Can also be set via AGENTIC_CBA_LOG_LEVEL environment variable.
        stream: Output stream for logs. Default: sys.stderr
        format_string: Custom format string (only applies to text format).
                       Default uses timestamp format for verbose.
        verbose: If True, use detailed format with timestamps (text mode only).
        log_format: Output format - "text" (default) or "json".
                    Can also be set via AGENTIC_CBA_LOG_FORMAT environment variable.
    """
    global _logging_configured

    if _logging_configured:
        return

    # Resolve log level
    if level is None:
        level_str = DEFAULT_LOG_LEVEL
    elif isinstance(level, int):
        level_str = logging.getLevelName(level)
    else:
        level_str = level.upper()

    numeric_level = getattr(logging, level_str, logging.WARNING)

    # Resolve format type
    if log_format is None:
        log_format = DEFAULT_LOG_FORMAT_TYPE

    log_format = log_format.lower()

    # Resolve stream
    if stream is None:
        stream = sys.stderr

    # Configure the root logger for our package
    package_logger = logging.getLogger(LOGGER_NAME)
    package_logger.setLevel(numeric_level)

    # Only add handler if none exist
    if not package_logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setLevel(numeric_level)
        handler.addFilter(CorrelationIdFilter())

        # Select formatter based on format type
        if log_format == "json":
            handler.setFormatter(get_json_formatter())
        else:
            # Text format (default)
            if format_string is not None:
                handler.setFormatter(logging.Formatter(format_string))
            else:
                handler.setFormatter(get_text_formatter(verbose=verbose))

        package_logger.addHandler(handler)

    # Prevent propagation to root logger (avoids duplicate messages)
    package_logger.propagate = False

    _logging_configured = True

    # Prevent propagation to root logger (avoids duplicate messages)
    package_logger.propagate = False

    _logging_configured = True


def reset_logging() -> None:
    """
    Reset logging configuration state.

    Primarily for testing purposes. Removes all handlers from the package logger
    and allows setup_logging() to be called again.
    """
    global _logging_configured

    package_logger = logging.getLogger(LOGGER_NAME)
    package_logger.handlers.clear()
    _logging_configured = False


def set_log_level(level: int | str) -> None:
    """
    Change the log level at runtime.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR)
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.WARNING)

    package_logger = logging.getLogger(LOGGER_NAME)
    package_logger.setLevel(level)

    for handler in package_logger.handlers:
        handler.setLevel(level)


def set_log_format(log_format: str) -> None:
    """
    Change the log format at runtime.

    Args:
        log_format: Format type - "text" or "json"
    """
    package_logger = logging.getLogger(LOGGER_NAME)

    # Update formatter on all handlers
    for handler in package_logger.handlers:
        if log_format.lower() == "json":
            handler.setFormatter(get_json_formatter())
        else:
            handler.setFormatter(get_text_formatter(verbose=True))
