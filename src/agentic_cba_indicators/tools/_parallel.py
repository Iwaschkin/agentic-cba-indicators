"""Internal tool for parallel tool execution."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from strands import ToolContext, tool

from agentic_cba_indicators.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

_DEFAULT_MAX_WORKERS = int(os.environ.get("TOOL_PARALLEL_MAX_WORKERS", "4"))


def _get_tools_from_context(
    tool_context: ToolContext | None,
) -> list[Callable[..., str]]:
    """Get tools from ToolContext.

    Inspects the ToolContext-provided agent for either `tool_registry`
    (preferred) or `tools`.

    Args:
        tool_context: Optional ToolContext provided by Strands runtime

    Returns:
        List of tool functions from agent context
    """
    if tool_context is None:
        return []

    try:
        agent = tool_context.agent
        if hasattr(agent, "tool_registry") and agent.tool_registry:
            # tool_registry is a dict mapping tool names to tool handlers
            return list(agent.tool_registry.values())
        if hasattr(agent, "tools") and agent.tools:
            return list(agent.tools)
    except (AttributeError, TypeError) as e:
        logger.debug(
            "Tool context access failed: %s: %s",
            type(e).__name__,
            e,
        )

    return []


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
        future_to_idx: dict[Any, int] = {}
        for idx, call in enumerate(calls):
            name = call.get("name", "")
            args = call.get("args", {}) or {}
            future = executor.submit(_invoke, idx, name, args)
            future_to_idx[future] = idx

        for future in as_completed(future_to_idx):
            future_idx = future_to_idx[future]
            try:
                _, result = future.result()
                results[future_idx] = result
            except Exception as exc:  # Best-effort aggregation
                logger.warning("Parallel tool call failed: %s", exc)
                results[future_idx] = f"Error executing tool: {exc}"

    output_lines = ["=== Parallel Tool Results ===\n"]
    for idx, call in enumerate(calls):
        name = call.get("name", f"tool_{idx}")
        output_lines.append(f"--- Result {idx + 1}: {name} ---")
        output_lines.append(results[idx])

    return "\n".join(output_lines)
