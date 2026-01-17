"""
Internal help tools for agent self-discovery.

These tools allow the agent to discover and understand available tools
at runtime without bloating the system prompt. They are internal-only
and should never be exposed to users.

Usage:
    1. CLI calls set_active_tools(tools) at startup
    2. Agent can call list_tools() to see available tools
    3. Agent can call describe_tool(name) for full documentation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands import tool

if TYPE_CHECKING:
    from collections.abc import Callable

# Module-level registry for currently active tools
# Set by CLI at startup via set_active_tools()
_active_tools: list[Callable[..., str]] = []


def set_active_tools(tools: list[Callable[..., str]]) -> None:
    """
    Set the active tools registry for the help system.

    Called by CLI at startup to register which tools are available
    to the agent. This allows list_tools() to reflect the actual
    tool set (reduced or full).

    Args:
        tools: List of tool functions to register
    """
    global _active_tools
    _active_tools = list(tools)


@tool
def list_tools() -> str:
    """
    List all available tools with one-line summaries.

    Use this when you need to discover what tools are available
    or find the right tool for a user's request.

    Returns:
        Tool names and brief descriptions (internal use only)
    """
    if not _active_tools:
        return "No tools available."

    lines: list[str] = []
    for t in _active_tools:
        name = getattr(t, "__name__", str(t))
        doc = getattr(t, "__doc__", "") or ""
        # Extract first non-empty line as summary
        first_line = ""
        for line in doc.split("\n"):
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break
        lines.append(f"- {name}: {first_line}")

    return "\n".join(lines)


@tool
def describe_tool(name: str) -> str:
    """
    Get detailed documentation for a specific tool.

    Use this when you need to understand how to use a tool,
    including its parameters, return values, and examples.

    Args:
        name: The tool function name (e.g., "get_current_weather")

    Returns:
        Full docstring with Args/Returns (internal use only)
    """
    for t in _active_tools:
        tool_name = getattr(t, "__name__", "")
        if tool_name == name:
            doc = getattr(t, "__doc__", None)
            if doc:
                return doc.strip()
            return f"No documentation available for '{name}'."

    return f"Tool '{name}' not found. Use list_tools() to see available tools."
