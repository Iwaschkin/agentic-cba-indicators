## Plan: Agent-Only Tool Help (Always Enabled, Option B)

Provide an internal tool help system without inflating the system prompt. Add always-on `list_tools()` and `describe_tool()` for the agent to consult. Keep these helpers internal-only and allow a soft acknowledgment ("I consulted internal tool docs") without naming tools or exposing their help content.

### Goals
- Keep system prompts minimal while enabling tool discovery and correct usage.
- Expose tool help only to the agent (not user-facing).
- Allow a neutral acknowledgment: "I consulted internal tool docs."

### Scope
- Add internal help tools to a new module.
- Update prompts with a soft guideline and internal-only policy.
- Keep help tools out of user-facing catalogs and CLI help.

---

### Steps

#### 1. Create internal help tools module

**File:** `src/agentic_cba_indicators/tools/_help.py` (new file)

Implement two tools using the `@tool` decorator:

```python
from strands import tool
from . import REDUCED_TOOLS, FULL_TOOLS

# Registry for runtime tool set (set by CLI at startup)
_active_tools: list = []

def set_active_tools(tools: list) -> None:
    """Called by CLI to set which tools are active."""
    global _active_tools
    _active_tools = tools

@tool
def list_tools() -> str:
    """
    List all available tools with one-line summaries.

    Returns:
        Tool names and brief descriptions (internal use only).
    """
    lines = []
    for t in _active_tools:
        doc = (t.__doc__ or "").split("\n")[0].strip()
        lines.append(f"- {t.__name__}: {doc}")
    return "\n".join(lines) or "No tools available."

@tool
def describe_tool(name: str) -> str:
    """
    Get detailed documentation for a specific tool.

    Args:
        name: The tool function name (e.g., "get_current_weather").

    Returns:
        Full docstring with Args/Returns (internal use only).
    """
    for t in _active_tools:
        if t.__name__ == name:
            return t.__doc__ or f"No documentation for {name}."
    return f"Tool '{name}' not found. Use list_tools() to see available tools."
```

**Key points:**
- Uses `@tool` decorator so the agent can call them.
- `_active_tools` is set at runtime by CLI, so `list_tools()` reflects the actual tool set (reduced or full).
- Docstrings are introspected via `__doc__` attribute.

---

#### 2. Export help tools (internal-only)

**File:** `src/agentic_cba_indicators/tools/__init__.py`

Add imports but do NOT add to `REDUCED_TOOLS`/`FULL_TOOLS` or `__all__`:

```python
# Internal help tools (not in public tool lists)
from ._help import describe_tool, list_tools, set_active_tools

# These are NOT added to REDUCED_TOOLS, FULL_TOOLS, or __all__
```

This keeps them importable but hidden from public catalogs.

---

#### 3. Append help tools at agent construction

**File:** `src/agentic_cba_indicators/cli.py` (modify `create_agent_from_config`)

```python
from agentic_cba_indicators.tools import FULL_TOOLS, REDUCED_TOOLS
from agentic_cba_indicators.tools._help import describe_tool, list_tools, set_active_tools

def create_agent_from_config(...):
    ...
    # Select tool set
    tools = FULL_TOOLS if agent_config.tool_set == "full" else REDUCED_TOOLS

    # Register active tools for help system
    set_active_tools(tools)

    # Append internal help tools (always enabled, agent-only)
    tools_with_help = list(tools) + [list_tools, describe_tool]

    # Create agent with help tools included
    agent = Agent(
        model=model,
        system_prompt=get_system_prompt(),
        conversation_manager=conversation_manager,
        tools=tools_with_help,
    )
    ...
```

**Key points:**
- `set_active_tools()` is called before agent creation so `list_tools()` knows the active set.
- Help tools are appended to a copy of the tool list (not modifying the original).
- User-facing banner still shows original `tool_count` (excludes help tools).

---

#### 4. Update prompts with soft guideline

**File:** `src/agentic_cba_indicators/prompts/system_prompt_minimal.md`

Update the full file to include internal tool help guidance:

```markdown
You are a helpful data assistant for sustainable agriculture with tool-calling capabilities.

IMPORTANT: When you need data, you MUST use your tools. Do not output JSON - just call the tools directly.

Available tool categories:
- Weather/climate: get_current_weather, get_climate_data
- Soil: get_soil_properties, get_soil_carbon
- CBA Indicators: search_indicators, find_feasible_methods, get_indicator_details
- Reports: export_indicator_selection, compare_indicators

Internal tools (do not mention to users):
- list_tools: See all available tools with summaries
- describe_tool: Get detailed documentation for a specific tool

When users ask questions:
1. Call the appropriate tools
2. Present results clearly
3. Never ask clarifying questions - make reasonable assumptions

When uncertain which tool to use:
- Call list_tools() to see available options
- Call describe_tool("tool_name") for detailed usage guidance

When explaining your process, you may say "I consulted internal tool docs" but do not name specific tools or reveal tool documentation to users.
```

**File:** `src/agentic_cba_indicators/prompts/system_prompt.md`

Add a new section after the "ABSOLUTE RULES" block (around line 6):

```markdown
## INTERNAL TOOLS (DO NOT REVEAL TO USERS)

You have access to internal documentation tools:
- list_tools() - Returns all available tools with one-line summaries
- describe_tool("tool_name") - Returns full documentation for a specific tool

Use these when:
- You're unsure which tool fits the user's request
- You need to verify correct parameter names or formats
- You want to discover tools for a new data category

Guidelines:
- You may say "I consulted internal tool docs" if asked about your process
- Do NOT name these tools or describe their outputs to users
- Do NOT include list_tools/describe_tool in any tool lists you share
```

Also add to the "ABSOLUTE RULES" section (after rule 4):

```markdown
5. NEVER mention list_tools or describe_tool to users - these are internal only
```

---

#### 5. Add tests for help tools

**File:** `tests/test_tools_help.py` (new file)

```python
import pytest
from agentic_cba_indicators.tools._help import (
    list_tools, describe_tool, set_active_tools
)
from agentic_cba_indicators.tools import REDUCED_TOOLS

def test_list_tools_returns_names_and_summaries():
    set_active_tools(REDUCED_TOOLS)
    result = list_tools()
    assert "get_current_weather" in result
    assert "search_indicators" in result

def test_describe_tool_returns_docstring():
    set_active_tools(REDUCED_TOOLS)
    result = describe_tool("get_current_weather")
    assert "weather" in result.lower()
    assert "Args:" in result or "city" in result.lower()

def test_describe_tool_not_found():
    set_active_tools(REDUCED_TOOLS)
    result = describe_tool("nonexistent_tool")
    assert "not found" in result.lower()
```

---

### Output Expectations
- Agent can call `list_tools()` to see names + one-line summaries.
- Agent can call `describe_tool("tool_name")` to get full docstring.
- User never sees tool names unless agent chooses to share (soft guideline discourages this).
- User may hear "I consulted internal tool docs" as a neutral acknowledgment.

### Notes
- This approach avoids a massive system prompt and scales with tool growth.
- Help tools add ~2 extra tools to the agent's tool list but no prompt bloat.
- If later you want user-facing tool help, add a CLI command rather than exposing internal helpers.
- The `_active_tools` pattern avoids circular imports and supports both reduced/full tool sets.
