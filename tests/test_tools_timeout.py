"""Tests for tool timeout decorator."""

import time

import pytest

from agentic_cba_indicators.tools._timeout import ToolTimeoutError, timeout


def test_timeout_raises() -> None:
    @timeout(0.01)
    def slow() -> str:
        time.sleep(0.05)
        return "ok"

    with pytest.raises(ToolTimeoutError):
        slow()


def test_timeout_returns_value() -> None:
    @timeout(0.1)
    def fast() -> str:
        return "ok"

    assert fast() == "ok"
