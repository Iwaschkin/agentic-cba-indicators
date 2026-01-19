"""Tests for audit logging module (TASK105).

Validates audit entry creation, sanitization, and file output.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from agentic_cba_indicators.audit import (
    AUDIT_LOG_ENV_VAR,
    AuditEntry,
    AuditLogger,
    get_audit_logger,
    log_tool_invocation,
    reset_audit_logger,
    sanitize_value,
    truncate_result,
)
from agentic_cba_indicators.logging_config import set_correlation_id


class TestSanitizeValue:
    """Test parameter sanitization."""

    def test_sanitize_api_key(self) -> None:
        """API keys should be redacted."""
        value = "api_key=secret123"
        result = sanitize_value(value)
        assert "secret123" not in result
        assert "REDACTED" in result

    def test_sanitize_password(self) -> None:
        """Passwords should be redacted."""
        value = "password=mysecretpass"
        result = sanitize_value(value)
        assert "mysecretpass" not in result
        assert "REDACTED" in result

    def test_sanitize_bearer_token(self) -> None:
        """Bearer tokens should be redacted."""
        value = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_value(value)
        assert "eyJ" not in result
        assert "REDACTED" in result

    def test_sanitize_dict_with_sensitive_keys(self) -> None:
        """Dictionary values with sensitive keys should be redacted."""
        value = {
            "query": "test",
            "api_key": "secret123",
            "password": "pass",
        }
        result = sanitize_value(value)
        assert result["query"] == "test"
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"

    def test_sanitize_nested_dict(self) -> None:
        """Nested dictionaries should be sanitized."""
        value = {
            "outer": {
                "api_key": "secret",
                "data": "safe",
            }
        }
        result = sanitize_value(value)
        assert result["outer"]["api_key"] == "***REDACTED***"
        assert result["outer"]["data"] == "safe"

    def test_sanitize_list(self) -> None:
        """Lists should have elements sanitized."""
        value = ["safe", "api_key=secret", "more safe"]
        result = sanitize_value(value)
        assert result[0] == "safe"
        assert "secret" not in result[1]
        assert result[2] == "more safe"

    def test_sanitize_none(self) -> None:
        """None should return None."""
        assert sanitize_value(None) is None

    def test_sanitize_preserves_safe_values(self) -> None:
        """Safe values should be preserved."""
        assert sanitize_value("hello world") == "hello world"
        assert sanitize_value(123) == 123
        assert sanitize_value(True) is True


class TestTruncateResult:
    """Test result truncation."""

    def test_short_result_not_truncated(self) -> None:
        """Short results should not be truncated."""
        result = "Short result"
        assert truncate_result(result) == result

    def test_long_result_truncated(self) -> None:
        """Long results should be truncated."""
        result = "x" * 2000
        truncated = truncate_result(result, max_length=100)
        assert truncated is not None
        assert len(truncated) < len(result)
        assert "truncated" in truncated

    def test_truncate_none(self) -> None:
        """None should return None."""
        assert truncate_result(None) is None

    def test_truncation_shows_original_length(self) -> None:
        """Truncation should indicate original length."""
        result = "x" * 500
        truncated = truncate_result(result, max_length=100)
        assert truncated is not None
        assert "500 chars" in truncated


class TestAuditEntry:
    """Test AuditEntry dataclass."""

    def test_create_entry(self) -> None:
        """Create a basic audit entry."""
        entry = AuditEntry(
            timestamp="2026-01-18T12:00:00Z",
            event_type="tool_invocation",
            tool_name="test_tool",
            success=True,
        )
        assert entry.timestamp == "2026-01-18T12:00:00Z"
        assert entry.event_type == "tool_invocation"
        assert entry.tool_name == "test_tool"
        assert entry.success is True

    def test_entry_to_json(self) -> None:
        """Entry should serialize to JSON."""
        entry = AuditEntry(
            timestamp="2026-01-18T12:00:00Z",
            event_type="tool_invocation",
            tool_name="test_tool",
        )
        json_str = entry.to_json()
        data = json.loads(json_str)
        assert data["timestamp"] == "2026-01-18T12:00:00Z"
        assert data["tool_name"] == "test_tool"

    def test_entry_from_json(self) -> None:
        """Entry should deserialize from JSON."""
        json_str = '{"timestamp": "2026-01-18T12:00:00Z", "event_type": "test", "tool_name": "my_tool", "success": true, "params": {}, "result_summary": null, "latency_ms": 0.0, "error": null, "session_id": null, "metadata": {}}'
        entry = AuditEntry.from_json(json_str)
        assert entry.timestamp == "2026-01-18T12:00:00Z"
        assert entry.tool_name == "my_tool"

    def test_entry_roundtrip(self) -> None:
        """Entry should survive JSON roundtrip."""
        original = AuditEntry(
            timestamp="2026-01-18T12:00:00Z",
            event_type="tool_invocation",
            tool_name="test_tool",
            params={"query": "test"},
            result_summary="Found 5 results",
            success=True,
            latency_ms=150.5,
        )
        json_str = original.to_json()
        restored = AuditEntry.from_json(json_str)
        assert restored.timestamp == original.timestamp
        assert restored.tool_name == original.tool_name
        assert restored.params == original.params
        assert restored.result_summary == original.result_summary
        assert restored.latency_ms == original.latency_ms


class TestAuditLogger:
    """Test AuditLogger class."""

    def test_log_creates_file(self) -> None:
        """Logging should create the log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            entry = AuditEntry(
                timestamp="2026-01-18T12:00:00Z",
                event_type="test",
            )
            logger.log(entry)

            assert log_path.exists()

    def test_log_appends_entries(self) -> None:
        """Multiple logs should append entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            for i in range(3):
                entry = AuditEntry(
                    timestamp=f"2026-01-18T12:0{i}:00Z",
                    event_type="test",
                )
                logger.log(entry)

            # Count lines in file
            with log_path.open() as f:
                lines = [line for line in f if line.strip()]
            assert len(lines) == 3

    def test_log_tool_invocation(self) -> None:
        """log_tool_invocation should create proper entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            logger.log_tool_invocation(
                tool_name="search_indicators",
                params={"query": "soil carbon"},
                result="Found 5 indicators",
                success=True,
                latency=0.5,
            )

            entries = logger.read_entries()
            assert len(entries) == 1
            assert entries[0].tool_name == "search_indicators"
            assert entries[0].params == {"query": "soil carbon"}
            assert entries[0].latency_ms == 500.0

    def test_log_sanitizes_params(self) -> None:
        """log_tool_invocation should sanitize parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            logger.log_tool_invocation(
                tool_name="test",
                params={"query": "test", "api_key": "secret123"},
            )

            entries = logger.read_entries()
            assert entries[0].params["api_key"] == "***REDACTED***"
            assert entries[0].params["query"] == "test"

    def test_read_entries(self) -> None:
        """read_entries should return logged entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            for i in range(5):
                entry = AuditEntry(
                    timestamp=f"2026-01-18T12:0{i}:00Z",
                    event_type="test",
                    tool_name=f"tool_{i}",
                )
                logger.log(entry)

            entries = logger.read_entries()
            assert len(entries) == 5

    def test_read_entries_with_limit(self) -> None:
        """read_entries should respect limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            for i in range(10):
                entry = AuditEntry(
                    timestamp=f"2026-01-18T12:0{i}:00Z",
                    event_type="test",
                )
                logger.log(entry)

            entries = logger.read_entries(limit=3)
            assert len(entries) == 3

    def test_entry_count(self) -> None:
        """entry_count should track logged entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            assert logger.entry_count == 0

            for i in range(3):
                entry = AuditEntry(
                    timestamp=f"2026-01-18T12:0{i}:00Z",
                    event_type="test",
                )
                logger.log(entry)

            assert logger.entry_count == 3


class TestGlobalAuditLogger:
    """Test global audit logger functions."""

    def test_get_audit_logger_returns_none_when_disabled(self) -> None:
        """get_audit_logger returns None when env var not set."""
        reset_audit_logger()

        # Ensure env var is not set
        old_value = os.environ.pop(AUDIT_LOG_ENV_VAR, None)
        try:
            logger = get_audit_logger()
            assert logger is None
        finally:
            if old_value:
                os.environ[AUDIT_LOG_ENV_VAR] = old_value
            reset_audit_logger()

    def test_get_audit_logger_returns_logger_when_enabled(self) -> None:
        """get_audit_logger returns logger when env var is set."""
        reset_audit_logger()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            old_value = os.environ.get(AUDIT_LOG_ENV_VAR)

            try:
                os.environ[AUDIT_LOG_ENV_VAR] = str(log_path)
                reset_audit_logger()  # Force re-initialization

                logger = get_audit_logger()
                assert logger is not None
                assert logger.log_path == log_path
            finally:
                if old_value:
                    os.environ[AUDIT_LOG_ENV_VAR] = old_value
                else:
                    os.environ.pop(AUDIT_LOG_ENV_VAR, None)
                reset_audit_logger()

    def test_log_tool_invocation_noop_when_disabled(self) -> None:
        """log_tool_invocation should do nothing when audit disabled."""
        reset_audit_logger()

        old_value = os.environ.pop(AUDIT_LOG_ENV_VAR, None)
        try:
            # This should not raise even when logging is disabled
            log_tool_invocation(
                tool_name="test",
                params={"query": "test"},
                success=True,
            )
        finally:
            if old_value:
                os.environ[AUDIT_LOG_ENV_VAR] = old_value
            reset_audit_logger()

    def test_log_tool_invocation_writes_when_enabled(self) -> None:
        """log_tool_invocation should write when audit enabled."""
        reset_audit_logger()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            old_value = os.environ.get(AUDIT_LOG_ENV_VAR)

            try:
                os.environ[AUDIT_LOG_ENV_VAR] = str(log_path)
                reset_audit_logger()

                set_correlation_id("corr-abc")
                log_tool_invocation(
                    tool_name="search_indicators",
                    params={"query": "test"},
                    success=True,
                )
                set_correlation_id(None)

                # Verify file was created and has content
                assert log_path.exists()
                with log_path.open() as f:
                    content = f.read()
                assert "search_indicators" in content
                assert "corr-abc" in content
            finally:
                if old_value:
                    os.environ[AUDIT_LOG_ENV_VAR] = old_value
                else:
                    os.environ.pop(AUDIT_LOG_ENV_VAR, None)
                reset_audit_logger()
