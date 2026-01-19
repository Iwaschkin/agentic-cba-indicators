"""Tests for internal help tools."""

from unittest.mock import MagicMock

import pytest

from agentic_cba_indicators.tools import REDUCED_TOOLS
from agentic_cba_indicators.tools._help import (
    _TOOL_CATEGORIES,
    _get_tools_from_context,
    describe_tool,
    list_tools,
    list_tools_by_category,
    search_tools,
    set_active_tools,
)


@pytest.fixture
def mock_tool_context() -> MagicMock:
    """Create a mock ToolContext that falls back to module registry.

    The mock has no agent.tool_registry so _get_tools_from_context
    will use the module-level _active_tools registry set by set_active_tools().
    """
    mock = MagicMock()
    # Make agent.tool_registry and agent.tools return None/empty
    # so _get_tools_from_context falls back to module registry
    mock.agent.tool_registry = None
    mock.agent.tools = None
    return mock


@pytest.fixture
def context_with_tools() -> MagicMock:
    """Create a mock ToolContext with tools in agent.tools."""
    mock = MagicMock()
    mock.agent.tool_registry = None
    mock.agent.tools = REDUCED_TOOLS
    return mock


@pytest.fixture
def context_with_tool_registry() -> MagicMock:
    """Create a mock ToolContext with tools in agent.tool_registry."""
    mock = MagicMock()
    mock.agent.tool_registry = {t.__name__: t for t in REDUCED_TOOLS}
    mock.agent.tools = None
    return mock


class TestGetToolsFromContext:
    """Tests for _get_tools_from_context() helper function."""

    def test_returns_module_registry_when_context_none(self) -> None:
        """Verify fallback to module registry when context is None."""
        set_active_tools(REDUCED_TOOLS)
        tools = _get_tools_from_context(None)
        assert len(tools) == len(REDUCED_TOOLS)

    def test_returns_module_registry_when_agent_has_no_tools(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify fallback when agent has no tool_registry or tools."""
        set_active_tools(REDUCED_TOOLS)
        tools = _get_tools_from_context(mock_tool_context)
        assert len(tools) == len(REDUCED_TOOLS)

    def test_returns_agent_tools_when_available(
        self, context_with_tools: MagicMock
    ) -> None:
        """Verify returns agent.tools when available."""
        set_active_tools([])  # Empty module registry
        tools = _get_tools_from_context(context_with_tools)
        assert len(tools) == len(REDUCED_TOOLS)

    def test_returns_tool_registry_when_available(
        self, context_with_tool_registry: MagicMock
    ) -> None:
        """Verify returns agent.tool_registry values when available."""
        set_active_tools([])
        tools = _get_tools_from_context(context_with_tool_registry)
        assert len(tools) == len(REDUCED_TOOLS)


class TestListTools:
    """Tests for list_tools() function."""

    def test_list_tools_returns_names_and_summaries(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify list_tools returns tool names with first docstring line."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools(mock_tool_context)

        # Should contain known tool names
        assert "get_current_weather" in result
        assert "search_indicators" in result

        # Should be formatted as bullet list
        assert result.startswith("-")
        assert "\n-" in result

    def test_list_tools_empty_registry(self, mock_tool_context: MagicMock) -> None:
        """Verify list_tools handles empty registry."""
        set_active_tools([])
        result = list_tools(mock_tool_context)

        assert result == "No tools available."

    def test_list_tools_includes_all_tools(self, mock_tool_context: MagicMock) -> None:
        """Verify list_tools includes all registered tools."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools(mock_tool_context)

        # Count bullet points
        bullet_count = result.count("\n-") + 1  # +1 for first line
        assert bullet_count == len(REDUCED_TOOLS)

    def test_list_tools_uses_context_tools(self, context_with_tools: MagicMock) -> None:
        """Verify list_tools uses tools from context when available."""
        set_active_tools([])  # Empty module registry
        result = list_tools(context_with_tools)

        # Should still get tools from context
        assert "get_current_weather" in result


class TestListToolsByCategory:
    """Tests for list_tools_by_category() function."""

    def test_list_tools_by_category_overview(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify overview shows all categories with counts."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools_by_category(tool_context=mock_tool_context)

        # Should show category overview
        assert "Available tool categories" in result
        assert "weather" in result.lower()
        assert "knowledge_base" in result.lower()

    def test_list_tools_by_category_weather(self, mock_tool_context: MagicMock) -> None:
        """Verify filtering by weather category works."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools_by_category("weather", tool_context=mock_tool_context)

        # Should show weather tools
        assert "get_current_weather" in result
        assert "get_weather_forecast" in result
        # Should not show non-weather tools
        assert "search_indicators" not in result

    def test_list_tools_by_category_knowledge_base(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify filtering by knowledge_base category works."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools_by_category(
            "knowledge_base", tool_context=mock_tool_context
        )

        # Should show knowledge base tools
        assert "search_indicators" in result
        assert "get_indicator_details" in result

    def test_list_tools_by_category_invalid(self, mock_tool_context: MagicMock) -> None:
        """Verify invalid category returns error message."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools_by_category(
            "invalid_category", tool_context=mock_tool_context
        )

        assert "Unknown category" in result

    def test_list_tools_by_category_empty_registry(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify handles empty registry."""
        set_active_tools([])
        result = list_tools_by_category(tool_context=mock_tool_context)

        assert result == "No tools available."


class TestToolCategoryKeywords:
    """Tests for tool category keyword uniqueness."""

    def test_category_keywords_unique(self) -> None:
        seen: dict[str, str] = {}
        for cat_id, (_, keywords) in _TOOL_CATEGORIES.items():
            for keyword in keywords:
                assert keyword not in seen, (
                    f"Keyword '{keyword}' duplicated in {seen[keyword]} and {cat_id}"
                )
                seen[keyword] = cat_id


class TestSearchTools:
    """Tests for search_tools() function."""

    def test_search_tools_by_name(self, mock_tool_context: MagicMock) -> None:
        """Verify search by tool name works."""
        set_active_tools(REDUCED_TOOLS)
        result = search_tools("weather", tool_context=mock_tool_context)

        assert "get_current_weather" in result
        assert "get_weather_forecast" in result
        assert "Found" in result

    def test_search_tools_by_description(self, mock_tool_context: MagicMock) -> None:
        """Verify search in docstrings works."""
        set_active_tools(REDUCED_TOOLS)
        result = search_tools("temperature", tool_context=mock_tool_context)

        # Should find weather tools that mention temperature
        assert "Found" in result
        assert len(result) > 0

    def test_search_tools_no_match(self, mock_tool_context: MagicMock) -> None:
        """Verify no match returns helpful message."""
        set_active_tools(REDUCED_TOOLS)
        result = search_tools("xyznonexistent123", tool_context=mock_tool_context)

        assert "No tools found" in result
        assert "list_tools()" in result

    def test_search_tools_empty_query(self, mock_tool_context: MagicMock) -> None:
        """Verify empty query returns error."""
        set_active_tools(REDUCED_TOOLS)
        result = search_tools("", tool_context=mock_tool_context)

        assert "provide a search query" in result.lower()

    def test_search_tools_empty_registry(self, mock_tool_context: MagicMock) -> None:
        """Verify handles empty registry."""
        set_active_tools([])
        result = search_tools("weather", tool_context=mock_tool_context)

        assert result == "No tools available."


class TestDescribeTool:
    """Tests for describe_tool() function."""

    def test_describe_tool_returns_docstring(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify describe_tool returns full docstring for known tool."""
        set_active_tools(REDUCED_TOOLS)
        result = describe_tool("get_current_weather", tool_context=mock_tool_context)

        # Should contain docstring content
        assert "weather" in result.lower()
        # Should have Args section (Google-style docstring)
        assert "Args:" in result or "city" in result.lower()

    def test_describe_tool_not_found(self, mock_tool_context: MagicMock) -> None:
        """Verify describe_tool returns error for unknown tool."""
        set_active_tools(REDUCED_TOOLS)
        result = describe_tool("nonexistent_tool", tool_context=mock_tool_context)

        assert "not found" in result.lower()
        assert "list_tools()" in result

    def test_describe_tool_empty_registry(self, mock_tool_context: MagicMock) -> None:
        """Verify describe_tool handles empty registry."""
        set_active_tools([])
        result = describe_tool("get_current_weather", tool_context=mock_tool_context)

        assert "not found" in result.lower()
        assert "No tools are registered" in result


class TestSetActiveTools:
    """Tests for set_active_tools() function."""

    def test_set_active_tools_updates_registry(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify set_active_tools updates the registry."""
        # Start with empty
        set_active_tools([])
        assert list_tools(mock_tool_context) == "No tools available."

        # Set tools
        set_active_tools(REDUCED_TOOLS)
        result = list_tools(mock_tool_context)
        assert "get_current_weather" in result

    def test_set_active_tools_replaces_previous(
        self, mock_tool_context: MagicMock
    ) -> None:
        """Verify set_active_tools replaces previous registry."""
        set_active_tools(REDUCED_TOOLS)
        full_result = list_tools(mock_tool_context)

        # Set to subset
        subset = REDUCED_TOOLS[:3]
        set_active_tools(subset)
        subset_result = list_tools(mock_tool_context)

        # Should have fewer tools now
        assert len(subset_result) < len(full_result)
