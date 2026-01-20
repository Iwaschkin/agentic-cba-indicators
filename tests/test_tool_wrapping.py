"""Tests for centralized tool wrapping (metrics + audit + timeout)."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_cba_indicators.observability import get_metrics, reset_metrics


def test_tools_are_wrapped() -> None:
    from agentic_cba_indicators.tools import REDUCED_TOOLS

    for tool in REDUCED_TOOLS:
        assert getattr(tool, "__agentic_tool_wrapped__", False) is True


def test_wrapped_tool_records_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_cba_indicators import tools

    reset_metrics()

    def sample_tool(x: int) -> str:
        return f"value={x}"

    wrapped = tools._wrap_tool(sample_tool)
    result = wrapped(5)
    assert result == "value=5"

    metrics = get_metrics().get_tool_metrics("sample_tool")
    assert metrics.call_count == 1
    assert metrics.success_count == 1
    assert metrics.failure_count == 0


def test_wrapped_tool_logs_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_cba_indicators import tools

    calls: list[dict[str, Any]] = []

    def fake_log_tool_invocation(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(tools, "log_tool_invocation", fake_log_tool_invocation)

    def sample_tool(x: int, *, tool_context: str | None = None) -> str:
        return f"ok:{x}"

    wrapped = tools._wrap_tool(sample_tool)
    result = wrapped(7, tool_context="ctx")
    assert result == "ok:7"

    assert len(calls) == 1
    assert calls[0]["tool_name"] == "sample_tool"
    assert calls[0]["params"] == {"x": 7}
    assert calls[0]["success"] is True


def test_wrapped_tool_logs_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_cba_indicators import tools

    calls: list[dict[str, Any]] = []

    def fake_log_tool_invocation(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(tools, "log_tool_invocation", fake_log_tool_invocation)

    def failing_tool() -> str:
        raise ValueError("bad")

    wrapped = tools._wrap_tool(failing_tool)
    with pytest.raises(ValueError):
        wrapped()

    assert len(calls) == 1
    assert calls[0]["success"] is False
    assert "validation" in (calls[0]["error"] or "")
