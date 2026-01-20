"""Tests for parallel tool execution helper."""

from __future__ import annotations

from unittest.mock import MagicMock

from agentic_cba_indicators.tools._help import set_active_tools
from agentic_cba_indicators.tools._parallel import run_tools_parallel


def test_run_tools_parallel_executes_in_order() -> None:
    def tool_a(value: int) -> str:
        return f"A:{value}"

    def tool_b(text: str) -> str:
        return f"B:{text}"

    set_active_tools([tool_a, tool_b])

    mock_context = MagicMock()
    mock_context.agent.tool_registry = None
    mock_context.agent.tools = None

    result = run_tools_parallel(
        [
            {"name": "tool_a", "args": {"value": 1}},
            {"name": "tool_b", "args": {"text": "x"}},
        ],
        tool_context=mock_context,
    )

    first = result.find("A:1")
    second = result.find("B:x")

    assert first != -1
    assert second != -1
    assert first < second
