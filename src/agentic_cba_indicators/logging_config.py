"""
Logging configuration for Agentic CBA Indicators.

Provides a consistent logging setup for the package and scripts.
Use `setup_logging()` at the entry point to configure logging.

Usage:
    from agentic_cba_indicators.logging_config import get_logger, setup_logging

    # At entry point (e.g., cli.py or script main)
    setup_logging(level=logging.INFO)

    # In any module
    logger = get_logger(__name__)
    logger.info("Processing started")
    logger.debug("Detailed info: %s", data)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO

# Default log level (can be overridden via environment variable)
DEFAULT_LOG_LEVEL = os.environ.get("AGENTIC_CBA_LOG_LEVEL", "WARNING")

# Package-level logger name
LOGGER_NAME = "agentic_cba_indicators"

# Default format for log messages
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)s: %(message)s"

_logging_configured = False


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
) -> None:
    """
    Configure logging for the package.

    Should be called once at application startup (e.g., in cli.py main()).
    Subsequent calls are no-ops unless force=True.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Default: WARNING
               Can also be set via AGENTIC_CBA_LOG_LEVEL environment variable.
        stream: Output stream for logs. Default: sys.stderr
        format_string: Custom format string. Default uses timestamp format for verbose.
        verbose: If True, use detailed format with timestamps. If False, use simple format.
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

    # Resolve format
    if format_string is None:
        format_string = LOG_FORMAT if verbose else LOG_FORMAT_SIMPLE

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
        handler.setFormatter(logging.Formatter(format_string))
        package_logger.addHandler(handler)

    # Prevent propagation to root logger (avoids duplicate messages)
    package_logger.propagate = False

    _logging_configured = True


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
