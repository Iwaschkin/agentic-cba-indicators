# Plan: MCP Server Migration for Tool Invocation

Replace direct tool-passing with MCP server/client architecture. Server wraps tools with timeout/audit/metrics. Client uses `tool_filters` for reduced mode. Help tools removed (MCP provides native discovery).

## Architecture

- **Single MCP server** exposes full tool set via stdio transport
- **Client-side filtering** via `tool_filters.allowed` for reduced mode
- **Config stays in client** — CLI/UI read config, server stays stateless
- **Wrapping in server** — timeout/audit/metrics applied before MCP registration

## Steps

### Step 1: Create MCP Server Module

**File:** `src/agentic_cba_indicators/mcp_server.py`

- Use `FastMCP` from `mcp.server.fastmcp` to expose all tools from `FULL_TOOLS_RAW` (excluding help tools)
- Apply `_wrap_tool()` before registration for timeout/audit/metrics
- Add `run_server()` entry point with `mcp.run(transport="stdio")`
- Include server instructions describing tool categories and indicator workflow

### Step 2: Delete Help Tools

**Files to modify:**
- `src/agentic_cba_indicators/tools/help.py` — DELETE entire file
- `src/agentic_cba_indicators/tools/__init__.py` — Remove help imports, remove from `REDUCED_TOOLS_RAW` and `FULL_TOOLS_RAW`
- `src/agentic_cba_indicators/cli.py` — Remove `register_tools_for_help()` call
- `src/agentic_cba_indicators/ui.py` — Remove `register_tools_for_help()` call

**Functions to remove:**
- `list_available_tools`
- `get_tool_help`
- `list_tool_categories`
- `get_category_tools`
- `search_tools`
- `register_tools_for_help()`

### Step 3: Add Tool Name Constants

**File:** `src/agentic_cba_indicators/tools/__init__.py`

Add name constants derived from tool tuples:

```python
REDUCED_TOOL_NAMES: list[str] = [
    "get_current_weather",
    "get_weather_forecast",
    "get_climate_data",
    "get_soil_properties",
    "get_soil_carbon",
    "get_country_indicators",
    "get_world_bank_data",
    "search_indicators",
    "search_methods",
    "get_indicator_details",
    "list_knowledge_base_stats",
    "get_knowledge_version",
    "find_indicators_by_principle",
    "find_indicators_by_class",
    "find_feasible_methods",
    "list_indicators_by_component",
    "list_available_classes",
    "compare_indicators",
    "export_indicator_selection",
    "search_usecases",
]

FULL_TOOL_NAMES: list[str] = [
    # All tool names from FULL_TOOLS_RAW (56 tools after help removal)
]
```

### Step 4: Add Entry Point

**File:** `pyproject.toml`

Add to `[project.scripts]`:

```toml
agentic-cba-mcp = "agentic_cba_indicators.mcp_server:run_server"
```

### Step 5: Refactor CLI

**File:** `src/agentic_cba_indicators/cli.py`

Replace direct tool passing with MCPClient:

```python
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from agentic_cba_indicators.tools import REDUCED_TOOL_NAMES

# Build tool filters based on config
tool_filters = None
if config.tool_set == "reduced":
    tool_filters = {"allowed": REDUCED_TOOL_NAMES}

mcp_client = MCPClient(
    lambda: stdio_client(StdioServerParameters(command="agentic-cba-mcp")),
    tool_filters=tool_filters,
)

with mcp_client:
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=mcp_client.list_tools_sync(),
    )
    # ... chat loop
```

**Also remove:**
- `_parse_fallback_tool_call` function and regex
- Fallback tool execution code in main loop
- `_CliCallbackHandler` (may keep if still useful for other output control)

### Step 6: Refactor UI

**File:** `src/agentic_cba_indicators/ui.py`

Same MCPClient pattern as CLI.

### Step 7: Simplify System Prompt

**File:** `src/agentic_cba_indicators/prompts/system_prompt_minimal.md`

Remove:
- Tool discovery instructions (MCP provides native discovery)
- "Never say Calling tool" rule (MCP handles tool calls properly)
- Explicit tool lists

Keep:
- Indicator Selection Workflow (the domain logic)
- Response formatting guidelines
- Citation requirements

### Step 8: Config Cleanup

**Files:**
- `src/agentic_cba_indicators/config/schema.py` — Remove `include_help_tools` field
- `src/agentic_cba_indicators/config/defaults.yaml` — Remove `include_help_tools` default
- Any sample configs — Remove `include_help_tools`

### Step 9: Update Tests

**Delete:** `tests/test_tools_help.py`

**Create:** `tests/test_mcp_server.py`
- Verify server starts via subprocess
- Verify `tools/list` returns expected tool count (56 tools)
- Verify specific tool names are present
- Test tool invocation via MCP protocol

**Update:** `tests/test_tool_wrapping.py`
- Adjust for help tool removal
- Verify wrapping still applied in MCP context

## Verification Checklist

- [ ] `agentic-cba-mcp` starts and responds to `tools/list`
- [ ] `agentic-cba` CLI works with full tool set
- [ ] `agentic-cba` CLI works with `tool_set: reduced` config
- [ ] `agentic-cba-ui` works with MCPClient
- [ ] All tests pass
- [ ] `ruff check` passes
- [ ] `pyright` passes

## Rollback Plan

If issues arise, revert to direct tool passing by:
1. Restore help tools
2. Remove MCPClient usage from CLI/UI
3. Restore `tools=list(tools)` pattern
