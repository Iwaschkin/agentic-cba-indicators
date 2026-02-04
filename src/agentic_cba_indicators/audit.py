"""
Audit logging module for the Agentic CBA Indicators chatbot.

Provides structured audit logging for tool invocations and agent decisions.
Logs are written in JSON Lines format for easy parsing and analysis.

Security:
    - Parameters are sanitized before logging (credentials redacted)
    - Output paths are validated to prevent path traversal (via paths._validate_path)
    - Result summaries are truncated to prevent log bloat

Configuration:
    Set AGENTIC_CBA_AUDIT_LOG environment variable to specify the log file path.
    If not set, audit logging is disabled by default.

Usage:
    from agentic_cba_indicators.audit import get_audit_logger, log_tool_invocation

    # Log a tool invocation
    log_tool_invocation(
        tool_name="search_indicators",
        params={"query": "soil carbon"},
        result="Found 5 indicators...",
        success=True,
        latency=0.5,
    )

    # Get current audit log path
    logger = get_audit_logger()
    if logger:
        print(f"Audit log: {logger.log_path}")
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003  # Used at runtime in doctest
from typing import Any

from agentic_cba_indicators.logging_config import get_correlation_id, get_logger

# Module logger
logger = get_logger(__name__)

# Environment variable for audit log path
AUDIT_LOG_ENV_VAR = "AGENTIC_CBA_AUDIT_LOG"

# Maximum result length to log (prevents unbounded log growth)
MAX_RESULT_LENGTH = 1000

# Patterns for sensitive data to redact
_SENSITIVE_PATTERNS = [
    (
        re.compile(r"(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I),
        r"\1=***REDACTED***",
    ),
    (
        re.compile(r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I),
        r"\1=***REDACTED***",
    ),
    (
        re.compile(r"(secret|token)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I),
        r"\1=***REDACTED***",
    ),
    (
        re.compile(r"(authorization|auth)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.I), "Bearer ***REDACTED***"),
    (re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.I), "Basic ***REDACTED***"),
]

# Sensitive parameter names to completely redact
_SENSITIVE_PARAM_NAMES = {
    "api_key",
    "apikey",
    "api-key",
    "password",
    "passwd",
    "pwd",
    "secret",
    "secret_key",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "credentials",
    "creds",
}


def sanitize_value(value: Any) -> Any:
    """Sanitize a value for audit logging.

    Redacts sensitive information like API keys, passwords, and tokens.

    Args:
        value: The value to sanitize

    Returns:
        Sanitized value safe for logging
    """
    if value is None:
        return None

    if isinstance(value, str):
        result = value
        for pattern, replacement in _SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    if isinstance(value, dict):
        return {
            k: (
                "***REDACTED***"
                if k.lower() in _SENSITIVE_PARAM_NAMES
                else sanitize_value(v)
            )
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [sanitize_value(v) for v in value]

    # For other types (int, float, bool), return as-is
    return value


def truncate_result(
    result: str | None, max_length: int = MAX_RESULT_LENGTH
) -> str | None:
    """Truncate a result string to prevent log bloat.

    Args:
        result: The result string to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated result with indicator if truncated
    """
    if result is None:
        return None

    result_str = str(result)
    if len(result_str) <= max_length:
        return result_str

    return result_str[:max_length] + f"... [truncated, total {len(result_str)} chars]"


@dataclass
class AuditEntry:
    """A single audit log entry.

    Attributes:
        timestamp: ISO 8601 timestamp when the event occurred
        event_type: Type of event (e.g., "tool_invocation", "agent_decision")
        tool_name: Name of the tool that was invoked (if applicable)
        params: Sanitized parameters passed to the tool
        result_summary: Truncated summary of the result
        success: Whether the operation succeeded
        latency_ms: Latency in milliseconds
        error: Error message if operation failed
        session_id: Optional session identifier for correlation
        metadata: Additional metadata
    """

    timestamp: str
    event_type: str
    tool_name: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    result_summary: str | None = None
    success: bool = True
    latency_ms: float = 0.0
    error: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> AuditEntry:
        """Create entry from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class AuditLogger:
    """Thread-safe audit logger that writes JSON Lines to a file.

    Thread Safety:
        All writes are protected by a threading.Lock to ensure
        safe concurrent access from multiple threads.

    Example:
        logger = AuditLogger(Path("audit.jsonl"))
        logger.log(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="tool_invocation",
            tool_name="search_indicators",
            params={"query": "soil"},
            success=True,
        ))
    """

    def __init__(self, log_path: Path) -> None:
        """Initialize the audit logger.

        Args:
            log_path: Path to the audit log file (JSON Lines format)
        """
        self._log_path = log_path
        self._lock = threading.Lock()
        self._entry_count = 0

        # Ensure parent directory exists
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        """Path to the audit log file."""
        return self._log_path

    @property
    def entry_count(self) -> int:
        """Number of entries logged in this session."""
        return self._entry_count

    def log(self, entry: AuditEntry) -> None:
        """Write an audit entry to the log file.

        Args:
            entry: The audit entry to log
        """
        with self._lock:
            try:
                with self._log_path.open("a", encoding="utf-8") as f:
                    f.write(entry.to_json() + "\n")
                self._entry_count += 1
            except OSError as e:
                logger.warning("Failed to write audit entry: %s", e)

    def log_tool_invocation(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        result: str | None = None,
        success: bool = True,
        latency: float = 0.0,
        error: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Log a tool invocation event.

        Args:
            tool_name: Name of the tool that was invoked
            params: Parameters passed to the tool (will be sanitized)
            result: Result returned by the tool (will be truncated)
            success: Whether the tool call succeeded
            latency: Call latency in seconds
            error: Error message if tool call failed
            session_id: Optional session ID for correlation
        """
        entry = AuditEntry(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="tool_invocation",
            tool_name=tool_name,
            params=sanitize_value(params or {}),
            result_summary=truncate_result(result),
            success=success,
            latency_ms=latency * 1000,
            error=sanitize_value(error) if error else None,
            session_id=session_id,
        )
        self.log(entry)

    def read_entries(self, limit: int | None = None) -> list[AuditEntry]:
        """Read audit entries from the log file.

        Args:
            limit: Maximum number of entries to read (None for all)

        Returns:
            List of AuditEntry objects
        """
        entries: list[AuditEntry] = []

        if not self._log_path.exists():
            return entries

        try:
            with self._log_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(AuditEntry.from_json(line))
                            if limit and len(entries) >= limit:
                                break
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning("Failed to parse audit entry: %s", e)
        except OSError as e:
            logger.warning("Failed to read audit log: %s", e)

        return entries


# Global singleton audit logger
_audit_logger: AuditLogger | None = None
_audit_logger_lock = threading.Lock()
_audit_logger_initialized = False


def get_audit_logger() -> AuditLogger | None:
    """Get the global audit logger singleton.

    Returns None if audit logging is not configured (AGENTIC_CBA_AUDIT_LOG not set).

    Returns:
        The global AuditLogger instance, or None if not configured
    """
    global _audit_logger, _audit_logger_initialized

    if _audit_logger_initialized:
        return _audit_logger

    with _audit_logger_lock:
        if _audit_logger_initialized:
            return _audit_logger

        # Check for environment variable
        log_path_str = os.environ.get(AUDIT_LOG_ENV_VAR)

        if not log_path_str:
            # Default: disabled unless explicitly configured
            _audit_logger_initialized = True
            logger.debug("Audit logging disabled (set %s to enable)", AUDIT_LOG_ENV_VAR)
            return None

        # Validate path (security: prevent path traversal)
        # Import here to avoid circular imports
        from agentic_cba_indicators.paths import _validate_path

        try:
            log_path = _validate_path(log_path_str, AUDIT_LOG_ENV_VAR)
            _audit_logger = AuditLogger(log_path)
            logger.info("Audit logging enabled: %s", log_path)
        except Exception as e:
            logger.warning("Failed to initialize audit logger: %s", e)
            _audit_logger = None

        _audit_logger_initialized = True
        return _audit_logger


def reset_audit_logger() -> None:
    """Reset the audit logger singleton.

    Primarily for testing purposes.
    """
    global _audit_logger, _audit_logger_initialized
    with _audit_logger_lock:
        _audit_logger = None
        _audit_logger_initialized = False


def log_tool_invocation(
    tool_name: str,
    params: dict[str, Any] | None = None,
    result: str | None = None,
    success: bool = True,
    latency: float = 0.0,
    error: str | None = None,
    session_id: str | None = None,
) -> None:
    """Log a tool invocation to the audit log.

    Convenience function that uses the global audit logger.
    Does nothing if audit logging is not configured.

    Args:
        tool_name: Name of the tool that was invoked
        params: Parameters passed to the tool (will be sanitized)
        result: Result returned by the tool (will be truncated)
        success: Whether the tool call succeeded
        latency: Call latency in seconds
        error: Error message if tool call failed
        session_id: Optional session ID for correlation
    """
    audit_logger = get_audit_logger()
    if audit_logger:
        if session_id is None:
            session_id = get_correlation_id()
        audit_logger.log_tool_invocation(
            tool_name=tool_name,
            params=params,
            result=result,
            success=success,
            latency=latency,
            error=error,
            session_id=session_id,
        )
