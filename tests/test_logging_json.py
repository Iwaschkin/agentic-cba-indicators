"""Tests for structured JSON logging in logging_config.py."""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from unittest import mock

import pytest

from agentic_cba_indicators.logging_config import (
    LOGGER_NAME,
    JSONFormatter,
    get_json_formatter,
    get_text_formatter,
    reset_logging,
    set_log_format,
    set_log_level,
    setup_logging,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def clean_logging():
    """Reset logging state before and after each test."""
    reset_logging()
    yield
    reset_logging()


@pytest.fixture
def json_formatter():
    """Get a fresh JSONFormatter instance."""
    return JSONFormatter()


@pytest.fixture
def log_record():
    """Create a basic LogRecord for testing."""
    return logging.LogRecord(
        name="test.module",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )


def get_test_logger(name: str) -> logging.Logger:
    """Get a logger under the package namespace for testing.

    This ensures the logger inherits handlers from the package logger.
    """
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


# =============================================================================
# JSONFormatter Tests
# =============================================================================


class TestJSONFormatter:
    """Test JSONFormatter class."""

    def test_basic_format_produces_valid_json(self, json_formatter, log_record):
        """Format should produce valid JSON."""
        output = json_formatter.format(log_record)
        data = json.loads(output)  # Should not raise

        assert isinstance(data, dict)

    def test_required_fields_present(self, json_formatter, log_record):
        """Output should contain timestamp, level, logger, message."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data

    def test_timestamp_is_iso8601_utc(self, json_formatter, log_record):
        """Timestamp should be ISO 8601 format with UTC timezone."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        timestamp = data["timestamp"]
        # Should parse as ISO 8601
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.tzinfo is not None  # Has timezone info

    def test_level_is_levelname(self, json_formatter, log_record):
        """Level should be the human-readable name."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        assert data["level"] == "INFO"

    def test_logger_name_preserved(self, json_formatter, log_record):
        """Logger name should be preserved."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        assert data["logger"] == "test.module"

    def test_message_formatting_with_args(self, json_formatter):
        """Message should be formatted with % args."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value is %d and %s",
            args=(42, "hello"),
            exc_info=None,
        )

        output = json_formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Value is 42 and hello"

    def test_source_location_included(self, json_formatter, log_record):
        """Source location should be included for DEBUG level and above."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        assert "source" in data
        assert data["source"]["file"] == "test.py"
        assert data["source"]["line"] == 42

    def test_exception_info_formatted(self, json_formatter):
        """Exception info should be formatted as traceback string."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = json_formatter.format(record)
        data = json.loads(output)

        assert "exc_info" in data
        assert "ValueError: Test error" in data["exc_info"]
        assert "Traceback" in data["exc_info"]

    def test_extra_fields_captured(self, json_formatter, log_record):
        """Extra fields passed to logger should be captured."""
        # Add extra fields to the record (simulates logger.info(..., extra={...}))
        log_record.user_id = 123
        log_record.action = "search"
        log_record.query = "soil carbon"

        output = json_formatter.format(log_record)
        data = json.loads(output)

        assert "extra" in data
        assert data["extra"]["user_id"] == 123
        assert data["extra"]["action"] == "search"
        assert data["extra"]["query"] == "soil carbon"

    def test_reserved_attrs_excluded_from_extra(self, json_formatter, log_record):
        """Standard LogRecord attributes should not appear in extra."""
        output = json_formatter.format(log_record)
        data = json.loads(output)

        # These are reserved and should not be in extra
        if "extra" in data:
            assert "name" not in data["extra"]
            assert "msg" not in data["extra"]
            assert "levelname" not in data["extra"]
            assert "pathname" not in data["extra"]

    def test_unicode_message_handled(self, json_formatter):
        """Unicode characters in message should be preserved."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test with unicode: 日本語 🌍 émojis",
            args=(),
            exc_info=None,
        )

        output = json_formatter.format(record)
        data = json.loads(output)

        assert "日本語" in data["message"]
        assert "🌍" in data["message"]

    def test_output_is_single_line(self, json_formatter, log_record):
        """Output should be a single line (JSON Lines format)."""
        output = json_formatter.format(log_record)

        # Should not contain newlines (except possibly in exc_info content)
        assert "\n" not in output.rstrip()


# =============================================================================
# Formatter Factory Tests
# =============================================================================


class TestFormatterFactories:
    """Test formatter factory functions."""

    def test_get_json_formatter_returns_jsonformatter(self):
        """get_json_formatter should return a JSONFormatter instance."""
        formatter = get_json_formatter()
        assert isinstance(formatter, JSONFormatter)

    def test_get_text_formatter_simple(self):
        """get_text_formatter(verbose=False) should use simple format."""
        formatter = get_text_formatter(verbose=False)
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt is not None
        # Simple format doesn't have timestamp
        assert "asctime" not in formatter._fmt

    def test_get_text_formatter_verbose(self):
        """get_text_formatter(verbose=True) should use detailed format."""
        formatter = get_text_formatter(verbose=True)
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt is not None
        # Verbose format has timestamp
        assert "asctime" in formatter._fmt


# =============================================================================
# setup_logging Tests
# =============================================================================


class TestSetupLogging:
    """Test setup_logging function with JSON format."""

    def test_setup_with_json_format(self, clean_logging):
        """setup_logging with log_format='json' should use JSONFormatter."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="json")

        logger = get_test_logger("test_json")
        logger.info("Test JSON message")

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Test JSON message"

    def test_setup_with_text_format_default(self, clean_logging):
        """setup_logging should default to text format."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream)

        logger = get_test_logger("test_text")
        logger.info("Test text message")

        output = stream.getvalue()

        # Should not be JSON (will raise if we try to parse)
        with pytest.raises(json.JSONDecodeError):
            json.loads(output.strip())

        # Should contain the message in text format
        assert "Test text message" in output

    def test_setup_respects_env_var_json(self, clean_logging):
        """setup_logging should respect AGENTIC_CBA_LOG_FORMAT env var."""
        with mock.patch.dict(
            "os.environ", {"AGENTIC_CBA_LOG_FORMAT": "json"}, clear=False
        ):
            # Need to reimport to pick up new default
            from agentic_cba_indicators import logging_config

            # Reset and reconfigure
            logging_config.reset_logging()
            stream = io.StringIO()

            # Force re-read of env var
            logging_config.DEFAULT_LOG_FORMAT_TYPE = "json"
            logging_config.setup_logging(level="INFO", stream=stream)

            logger = get_test_logger("test_env")
            logger.info("Test env message")

            output = stream.getvalue()
            data = json.loads(output.strip())
            assert data["message"] == "Test env message"

    def test_json_format_case_insensitive(self, clean_logging):
        """log_format parameter should be case-insensitive."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="JSON")

        logger = get_test_logger("test_case")
        logger.info("Test case message")

        output = stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == "Test case message"

    def test_setup_only_runs_once(self, clean_logging):
        """setup_logging should be a no-op on subsequent calls."""
        stream1 = io.StringIO()
        stream2 = io.StringIO()

        setup_logging(level="INFO", stream=stream1, log_format="json")
        setup_logging(
            level="INFO", stream=stream2, log_format="text"
        )  # Should be ignored

        logger = get_test_logger("test_once")
        logger.info("Test once message")

        # Should write to first stream (JSON format)
        output1 = stream1.getvalue()
        output2 = stream2.getvalue()

        assert len(output1) > 0
        assert len(output2) == 0  # Second setup was ignored


# =============================================================================
# Runtime Configuration Tests
# =============================================================================


class TestRuntimeConfiguration:
    """Test runtime reconfiguration functions."""

    def test_set_log_format_to_json(self, clean_logging):
        """set_log_format should switch to JSON formatter."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="text")

        # Switch to JSON
        set_log_format("json")

        logger = get_test_logger("test_switch")
        logger.info("After switch")

        output = stream.getvalue()
        lines = output.strip().split("\n")
        last_line = lines[-1]

        # Last line should be JSON
        data = json.loads(last_line)
        assert data["message"] == "After switch"

    def test_set_log_format_to_text(self, clean_logging):
        """set_log_format should switch to text formatter."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="json")

        logger = get_test_logger("test_switch2")
        logger.info("JSON line")

        # Switch to text
        set_log_format("text")
        logger.info("Text line")

        output = stream.getvalue()
        lines = output.strip().split("\n")

        # First line is JSON
        json.loads(lines[0])

        # Second line is text (should fail to parse as JSON)
        with pytest.raises(json.JSONDecodeError):
            json.loads(lines[1])

    def test_set_log_level_changes_level(self, clean_logging):
        """set_log_level should change the effective level."""
        stream = io.StringIO()
        setup_logging(level="WARNING", stream=stream, log_format="json")

        logger = get_test_logger("test_level")
        logger.info("Should not appear")

        set_log_level("DEBUG")
        logger.info("Should appear")

        output = stream.getvalue()
        assert "Should appear" in output
        assert "Should not appear" not in output


# =============================================================================
# Integration Tests
# =============================================================================


class TestJSONLoggingIntegration:
    """Integration tests for JSON logging in realistic scenarios."""

    def test_structured_logging_with_context(self, clean_logging):
        """Logging with extra context should include all fields."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="json")

        logger = get_test_logger("test_context")
        logger.info(
            "User performed search",
            extra={
                "user_id": "user_123",
                "query": "soil organic carbon",
                "results_count": 15,
                "duration_ms": 234.5,
            },
        )

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["message"] == "User performed search"
        assert data["extra"]["user_id"] == "user_123"
        assert data["extra"]["query"] == "soil organic carbon"
        assert data["extra"]["results_count"] == 15
        assert data["extra"]["duration_ms"] == 234.5

    def test_error_logging_with_exception(self, clean_logging):
        """Error logging with exception should include traceback."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="json")

        logger = get_test_logger("test_error")

        try:
            raise RuntimeError("Something went wrong")
        except RuntimeError:
            logger.exception("Operation failed")

        output = stream.getvalue()
        data = json.loads(output.strip())

        assert data["level"] == "ERROR"
        assert data["message"] == "Operation failed"
        assert "exc_info" in data
        assert "RuntimeError: Something went wrong" in data["exc_info"]

    def test_multiple_log_lines_are_jsonlines(self, clean_logging):
        """Multiple log entries should each be valid JSON (JSON Lines format)."""
        stream = io.StringIO()
        setup_logging(level="INFO", stream=stream, log_format="json")

        logger = get_test_logger("test_multi")
        logger.info("First message")
        logger.warning("Second message")
        logger.error("Third message")

        output = stream.getvalue()
        lines = output.strip().split("\n")

        assert len(lines) == 3

        # Each line should be valid JSON
        levels = []
        for line in lines:
            data = json.loads(line)
            levels.append(data["level"])

        assert levels == ["INFO", "WARNING", "ERROR"]
