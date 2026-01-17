"""Tests for internal help tools."""

from agentic_cba_indicators.tools import REDUCED_TOOLS
from agentic_cba_indicators.tools._help import (
    describe_tool,
    list_tools,
    set_active_tools,
)


class TestListTools:
    """Tests for list_tools() function."""

    def test_list_tools_returns_names_and_summaries(self) -> None:
        """Verify list_tools returns tool names with first docstring line."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools()

        # Should contain known tool names
        assert "get_current_weather" in result
        assert "search_indicators" in result

        # Should be formatted as bullet list
        assert result.startswith("-")
        assert "\n-" in result

    def test_list_tools_empty_registry(self) -> None:
        """Verify list_tools handles empty registry."""
        set_active_tools([])
        result = list_tools()

        assert result == "No tools available."

    def test_list_tools_includes_all_tools(self) -> None:
        """Verify list_tools includes all registered tools."""
        set_active_tools(REDUCED_TOOLS)
        result = list_tools()

        # Count bullet points
        bullet_count = result.count("\n-") + 1  # +1 for first line
        assert bullet_count == len(REDUCED_TOOLS)


class TestDescribeTool:
    """Tests for describe_tool() function."""

    def test_describe_tool_returns_docstring(self) -> None:
        """Verify describe_tool returns full docstring for known tool."""
        set_active_tools(REDUCED_TOOLS)
        result = describe_tool("get_current_weather")

        # Should contain docstring content
        assert "weather" in result.lower()
        # Should have Args section (Google-style docstring)
        assert "Args:" in result or "city" in result.lower()

    def test_describe_tool_not_found(self) -> None:
        """Verify describe_tool returns error for unknown tool."""
        set_active_tools(REDUCED_TOOLS)
        result = describe_tool("nonexistent_tool")

        assert "not found" in result.lower()
        assert "list_tools()" in result

    def test_describe_tool_empty_registry(self) -> None:
        """Verify describe_tool handles empty registry."""
        set_active_tools([])
        result = describe_tool("get_current_weather")

        assert "not found" in result.lower()


class TestSetActiveTools:
    """Tests for set_active_tools() function."""

    def test_set_active_tools_updates_registry(self) -> None:
        """Verify set_active_tools updates the registry."""
        # Start with empty
        set_active_tools([])
        assert list_tools() == "No tools available."

        # Set tools
        set_active_tools(REDUCED_TOOLS)
        result = list_tools()
        assert "get_current_weather" in result

    def test_set_active_tools_replaces_previous(self) -> None:
        """Verify set_active_tools replaces previous registry."""
        set_active_tools(REDUCED_TOOLS)
        full_result = list_tools()

        # Set to subset
        subset = REDUCED_TOOLS[:3]
        set_active_tools(subset)
        subset_result = list_tools()

        # Should have fewer tools now
        assert len(subset_result) < len(full_result)
