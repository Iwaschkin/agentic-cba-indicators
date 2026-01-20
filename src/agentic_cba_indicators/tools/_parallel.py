"""Internal tool for parallel tool execution."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from strands import ToolContext, tool

from agentic_cba_indicators.logging_config import get_logger

from ._help import _get_tools_from_context

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

_DEFAULT_MAX_WORKERS = int(os.environ.get("TOOL_PARALLEL_MAX_WORKERS", "4"))


def _resolve_tool_map(
    tool_context: ToolContext | None,
) -> dict[str, Callable[..., str]]:
    tools = _get_tools_from_context(tool_context)
    tool_map: dict[str, Callable[..., str]] = {}
    for t in tools:
        name = getattr(t, "__name__", str(t))
        tool_map[name] = t
    return tool_map


@tool(context=True)
def run_tools_parallel(
    calls: list[dict[str, Any]], *, tool_context: ToolContext
) -> str:
    """
    Execute multiple tools in parallel (internal use only).

    Args:
        calls: List of tool call objects. Each item must include:
            - name: Tool name
            - args: Dict of keyword arguments for the tool

    Returns:
        Combined results from each tool in call order
    """
    if not calls:
        return "No tool calls provided."

    tool_map = _resolve_tool_map(tool_context)
    missing = [c.get("name") for c in calls if c.get("name") not in tool_map]
    if missing:
        return f"Unknown tool(s): {', '.join([m for m in missing if m])}"

    results: list[str] = [""] * len(calls)

    def _invoke(index: int, name: str, args: dict[str, Any]) -> tuple[int, str]:
        tool_fn = tool_map[name]
        result = tool_fn(**args)
        return index, result

    max_workers = max(1, _DEFAULT_MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, call in enumerate(calls):
            name = call.get("name", "")
            args = call.get("args", {}) or {}
            futures.append(executor.submit(_invoke, idx, name, args))

        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
            except Exception as exc:  # Best-effort aggregation
                logger.warning("Parallel tool call failed: %s", exc)
                results[idx] = f"Error executing tool: {exc}"

    output_lines = ["=== Parallel Tool Results ===\n"]
    for idx, call in enumerate(calls):
        name = call.get("name", f"tool_{idx}")
        output_lines.append(f"--- Result {idx + 1}: {name} ---")
        output_lines.append(results[idx])

    return "\n".join(output_lines)
