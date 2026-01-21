"""Tests for MCP server module."""

from __future__ import annotations

from agentic_cba_indicators import mcp_server


class TestMcpServerModule:
    """Test MCP server module structure and configuration."""

    def test_all_tools_list_not_empty(self) -> None:
        """Verify _ALL_TOOLS contains tools."""
        assert len(mcp_server._ALL_TOOLS) > 0, "_ALL_TOOLS should not be empty"

    def test_all_tools_count(self) -> None:
        """Verify expected tool count (58 tools after removing 4 help tools)."""
        assert len(mcp_server._ALL_TOOLS) == 58, (
            f"Expected 58 tools, got {len(mcp_server._ALL_TOOLS)}"
        )

    def test_all_tools_are_callable(self) -> None:
        """Verify all tools in _ALL_TOOLS are callable."""
        for tool in mcp_server._ALL_TOOLS:
            assert callable(tool), f"Tool {tool} is not callable"

    def test_all_tools_have_names(self) -> None:
        """Verify all tools have __name__ attribute."""
        for tool in mcp_server._ALL_TOOLS:
            assert hasattr(tool, "__name__"), f"Tool {tool} missing __name__"
            assert tool.__name__, f"Tool {tool} has empty __name__"

    def test_no_help_tools_in_all_tools(self) -> None:
        """Verify help tools are not included (MCP provides native discovery)."""
        tool_names = {t.__name__ for t in mcp_server._ALL_TOOLS}
        help_tool_names = {
            "list_tools",
            "describe_tool",
            "search_tools",
            "list_tools_by_category",
            "set_active_tools",
        }
        found_help_tools = tool_names & help_tool_names
        assert not found_help_tools, f"Found help tools: {found_help_tools}"

    def test_mcp_instance_exists(self) -> None:
        """Verify FastMCP instance is created."""
        assert mcp_server.mcp is not None, "mcp instance should exist"
        assert mcp_server.mcp.name == "Agentic CBA Indicators"

    def test_server_instructions_present(self) -> None:
        """Verify server instructions are defined."""
        assert mcp_server._SERVER_INSTRUCTIONS, "Instructions should not be empty"
        assert "Tool Categories" in mcp_server._SERVER_INSTRUCTIONS
        assert "Indicator Selection Workflow" in mcp_server._SERVER_INSTRUCTIONS


class TestMcpToolConsistency:
    """Test tool consistency between MCP server and tools module."""

    def test_tools_match_full_tools_constant(self) -> None:
        """Verify _ALL_TOOLS matches FULL_TOOL_NAMES count."""
        from agentic_cba_indicators.tools import FULL_TOOL_NAMES

        mcp_tool_names = {t.__name__ for t in mcp_server._ALL_TOOLS}
        # Both should have 58 tools
        assert len(mcp_tool_names) == len(FULL_TOOL_NAMES), (
            f"MCP has {len(mcp_tool_names)} tools, "
            f"FULL_TOOL_NAMES has {len(FULL_TOOL_NAMES)}"
        )

    def test_tools_names_match_full_tools(self) -> None:
        """Verify tool names match between MCP server and FULL_TOOL_NAMES."""
        from agentic_cba_indicators.tools import FULL_TOOL_NAMES

        mcp_tool_names = {t.__name__ for t in mcp_server._ALL_TOOLS}
        full_tool_names_set = set(FULL_TOOL_NAMES)
        missing_in_mcp = full_tool_names_set - mcp_tool_names
        extra_in_mcp = mcp_tool_names - full_tool_names_set

        assert not missing_in_mcp, f"Missing in MCP: {missing_in_mcp}"
        assert not extra_in_mcp, f"Extra in MCP: {extra_in_mcp}"


class TestMcpRegistration:
    """Test MCP tool registration."""

    def test_register_tools_succeeds(self) -> None:
        """Verify _register_tools completes without error."""
        from mcp.server.fastmcp import FastMCP

        test_mcp = FastMCP("Test Server")

        original_mcp = mcp_server.mcp
        mcp_server.mcp = test_mcp

        try:
            mcp_server._register_tools()
        finally:
            mcp_server.mcp = original_mcp


class TestMcpServerEntryPoint:
    """Test MCP server entry point configuration."""

    def test_run_server_function_exists(self) -> None:
        """Verify run_server function exists and is callable."""
        assert hasattr(mcp_server, "run_server")
        assert callable(mcp_server.run_server)

    def test_entry_point_in_pyproject(self) -> None:
        """Verify entry point is configured in pyproject.toml."""
        import tomllib
        from pathlib import Path

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)

        scripts = pyproject.get("project", {}).get("scripts", {})
        assert "agentic-cba-mcp" in scripts, "agentic-cba-mcp entry point missing"
        assert (
            scripts["agentic-cba-mcp"] == "agentic_cba_indicators.mcp_server:run_server"
        )
