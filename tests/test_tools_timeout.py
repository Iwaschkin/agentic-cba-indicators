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


def test_timeout_sets_metadata() -> None:
    @timeout(0.1)
    def fast() -> str:
        return "ok"

    assert getattr(fast, "__tool_timeout_wrapped__", False) is True
    assert fast.__tool_timeout_seconds__ == 0.1  # type: ignore[attr-defined]
    assert fast() == "ok"


def test_timeout_resets_executor_on_threshold(monkeypatch) -> None:
    import agentic_cba_indicators.tools._timeout as timeout_module

    monkeypatch.setattr(timeout_module, "_MAX_TIMEOUT_FAILURES", 1)

    @timeout_module.timeout(0.01)
    def slow() -> str:
        time.sleep(0.05)
        return "ok"

    executor_before = timeout_module._get_executor()

    with pytest.raises(timeout_module.ToolTimeoutError):
        slow()

    executor_after = timeout_module._get_executor()

    assert executor_before is not executor_after
