"""
Internal help tools for agent self-discovery.

These tools allow the agent to discover and understand available tools
at runtime without bloating the system prompt. They are internal-only
and should never be exposed to users.

Usage:
    1. CLI calls set_active_tools(tools) at startup
    2. Agent can call list_tools() to see available tools
    3. Agent can call describe_tool(name) for full documentation
    4. Agent can call list_tools_by_category() to browse by domain

ToolContext Integration:
    Tools use @tool(context=True) to access the agent's tool registry
    directly when available, falling back to module-level registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands import ToolContext, tool

from agentic_cba_indicators.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# Module logger for debugging tool discovery
logger = get_logger(__name__)

# Module-level registry for currently active tools
# Set by CLI at startup via set_active_tools()
_active_tools: list[Callable[..., str]] = []

# Tool categories for organized discovery
# Maps category name to list of tool name prefixes/keywords
# NOTE: Order matters for categorization - more specific categories should have
# unique keywords that don't overlap with broader categories
_TOOL_CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "weather": (
        "Weather & Climate",
        ["weather", "climate", "forecast", "evapotranspiration", "solar_radiation"],
    ),
    "agriculture": (
        "Agricultural Data",
        ["agricultural", "crop", "land_use", "forest_stat", "fao"],
    ),
    "soil": ("Soil Properties", ["soil"]),
    "biodiversity": ("Biodiversity & Species", ["species", "biodiversity"]),
    "forestry": (
        "Forestry & Forest Watch",
        ["tree_cover", "forest_carbon", "forest_extent"],
    ),
    "labor": ("Labor Statistics", ["labor", "employment"]),
    "gender": ("Gender Statistics", ["gender"]),
    "sdg": ("SDG Indicators", ["sdg"]),
    "commodities": ("Commodity Markets", ["commodity", "fas_"]),
    "socioeconomic": ("Socio-economic Data", ["country_indicators", "world_bank"]),
    "knowledge_base": (
        "CBA Knowledge Base",
        [
            "search_indicator",
            "search_method",
            "usecase",
            "principle",
            "find_indicators_by_class",  # CR-0017: Use full prefix to avoid false matches
            "list_indicators_by_component",  # CR-0017: Use full prefix
            "list_available_classes",  # CR-0017: Use full prefix
            "knowledge_base",
            "knowledge_version",  # Added for get_knowledge_version
            "get_indicator",
            "find_indicator",
            "find_feasible",
            "list_indicator",
            "compare_indicator",
            "export_indicator",
        ],
    ),
    "help": ("Internal Help", ["list_tools", "describe_tool", "search_tools"]),
}


def set_active_tools(tools: Sequence[Callable[..., str]]) -> None:
    """
    Set the active tools registry for the help system.

    Called by CLI at startup to register which tools are available
    to the agent. This allows list_tools() to reflect the actual
    tool set (reduced or full).

    Args:
        tools: Sequence of tool functions to register (list or tuple)
    """
    global _active_tools
    _active_tools = list(tools)


def _get_tool_name(t: Callable[..., str]) -> str:
    """Extract tool name from a tool function."""
    return getattr(t, "__name__", str(t))


def _get_tool_summary(t: Callable[..., str]) -> str:
    """Extract first line of docstring as summary."""
    doc = getattr(t, "__doc__", "") or ""
    for line in doc.split("\n"):
        stripped = line.strip()
        if stripped:
            return stripped
    return "No description available"


def _categorize_tool(name: str) -> str:
    """Determine which category a tool belongs to."""
    name_lower = name.lower()
    for cat_id, (_, keywords) in _TOOL_CATEGORIES.items():
        for keyword in keywords:
            if keyword in name_lower:
                return cat_id
    return "other"


def _get_tools_from_context(
    tool_context: ToolContext | None,
) -> list[Callable[..., str]]:
    """Get tools from ToolContext agent or fall back to module registry.

    This inspects the ToolContext-provided agent for either `tool_registry`
    (preferred) or `tools`. If neither is available, it falls back to the
    module-level registry set via `set_active_tools()`.

    Note: This relies on Strands agent internals, which may change. If a stable
    public API becomes available, prefer that over introspection.

    Args:
        tool_context: Optional ToolContext provided by Strands runtime

    Returns:
        List of tool functions from agent context or module registry
    """
    # Try to get tools from the agent's context first
    if tool_context is not None:
        try:
            agent = tool_context.agent
            if hasattr(agent, "tool_registry") and agent.tool_registry:
                # tool_registry is a dict mapping tool names to tool handlers
                return list(agent.tool_registry.values())
            if hasattr(agent, "tools") and agent.tools:
                return list(agent.tools)
        except (AttributeError, TypeError) as e:
            # Fall back to module registry if context access fails
            logger.debug(
                "Tool context access failed, falling back to module registry: %s: %s",
                type(e).__name__,
                e,
            )

    # Fall back to module-level registry
    return _active_tools


@tool(context=True)
def list_tools(tool_context: ToolContext) -> str:
    """
    List all available tools with one-line summaries.

    Use this when you need to discover what tools are available
    or find the right tool for a user's request.

    Returns:
        Tool names and brief descriptions (internal use only)
    """
    tools = _get_tools_from_context(tool_context)

    if not tools:
        return "No tools available."

    lines: list[str] = []
    for t in tools:
        name = _get_tool_name(t)
        summary = _get_tool_summary(t)
        lines.append(f"- {name}: {summary}")

    return "\n".join(lines)


@tool(context=True)
def list_tools_by_category(category: str = "", *, tool_context: ToolContext) -> str:
    """
    List tools organized by functional category.

    Use this to explore tools in a specific domain like weather,
    soil, forestry, knowledge_base, etc.

    Args:
        category: Category to filter by (optional). Valid categories:
            weather, agriculture, soil, biodiversity, forestry,
            labor, gender, sdg, commodities, socioeconomic,
            knowledge_base, help. Leave empty to list all categories.

    Returns:
        Tools in the specified category, or category overview if none specified
    """
    tools = _get_tools_from_context(tool_context)

    if not tools:
        return "No tools available."

    # Build category -> tools mapping
    categorized: dict[str, list[tuple[str, str]]] = {}
    for t in tools:
        name = _get_tool_name(t)
        summary = _get_tool_summary(t)
        cat = _categorize_tool(name)
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append((name, summary))

    # If no category specified, show overview
    if not category:
        lines = ["Available tool categories:\n"]
        for cat_id, (cat_name, _) in _TOOL_CATEGORIES.items():
            count = len(categorized.get(cat_id, []))
            if count > 0:
                lines.append(f"- {cat_id}: {cat_name} ({count} tools)")
        if "other" in categorized:
            lines.append(f"- other: Miscellaneous ({len(categorized['other'])} tools)")
        lines.append(
            "\nUse list_tools_by_category('category_name') to see tools in a category."
        )
        return "\n".join(lines)

    # Show tools in specified category
    cat_lower = category.lower().strip()
    if cat_lower not in categorized:
        # Check if it's a valid category with no tools
        if cat_lower in _TOOL_CATEGORIES:
            return f"No tools available in category '{category}'."
        return f"Unknown category '{category}'. Use list_tools_by_category() to see valid categories."

    cat_name = _TOOL_CATEGORIES.get(cat_lower, ("Other", []))[0]
    category_tools = categorized[cat_lower]

    lines = [f"{cat_name} tools ({len(category_tools)}):\n"]
    for name, summary in sorted(category_tools):
        lines.append(f"- {name}: {summary}")

    return "\n".join(lines)


@tool(context=True)
def search_tools(query: str, *, tool_context: ToolContext) -> str:
    """
    Search for tools by keyword in name or description.

    Use this when you know what you're looking for but don't
    know the exact tool name.

    Args:
        query: Search term to find in tool names or descriptions

    Returns:
        Matching tools with their descriptions
    """
    tools = _get_tools_from_context(tool_context)

    if not tools:
        return "No tools available."

    if not query or not query.strip():
        return "Please provide a search query."

    query_lower = query.lower().strip()
    matches: list[tuple[str, str]] = []

    for t in tools:
        name = _get_tool_name(t)
        doc = getattr(t, "__doc__", "") or ""

        # Search in name and docstring
        if query_lower in name.lower() or query_lower in doc.lower():
            summary = _get_tool_summary(t)
            matches.append((name, summary))

    if not matches:
        return f"No tools found matching '{query}'. Try list_tools() to see all available tools."

    lines = [f"Found {len(matches)} tool(s) matching '{query}':\n"]
    for name, summary in sorted(matches):
        lines.append(f"- {name}: {summary}")

    return "\n".join(lines)


@tool(context=True)
def describe_tool(name: str, *, tool_context: ToolContext) -> str:
    """
    Get detailed documentation for a specific tool.

    Use this when you need to understand how to use a tool,
    including its parameters, return values, and examples.

    Args:
        name: The tool function name (e.g., "get_current_weather")

    Returns:
        Full docstring with Args/Returns (internal use only)
    """
    tools = _get_tools_from_context(tool_context)

    for t in tools:
        tool_name = _get_tool_name(t)
        if tool_name == name:
            doc = getattr(t, "__doc__", None)
            if doc:
                return doc.strip()
            return f"No documentation available for '{name}'."

    if not tools:
        return f"Tool '{name}' not found. No tools are registered."
    return f"Tool '{name}' not found. Use list_tools() to see available tools."
