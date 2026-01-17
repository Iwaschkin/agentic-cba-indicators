# Active Context

## Current Focus
**INTERNAL TOOL HELP SYSTEM COMPLETE** - Added agent self-discovery capability via internal help tools.

## Recent Changes
- Created `_help.py` module with `list_tools()` and `describe_tool()` tools
- Integrated help tools into CLI agent creation (appended to tool list)
- Updated system prompts with internal-only guidance
- Added 8 unit tests for help tools (83 total tests now)

## Key Deliverables
- `src/agentic_cba_indicators/tools/_help.py` - Internal help tools module
- Updated `cli.py` - Registers and appends help tools to agent
- Updated `system_prompt.md` and `system_prompt_minimal.md` - Internal tool guidance
- `tests/test_tools_help.py` - Unit tests for help tools

## Design Decisions
- Help tools use `_active_tools` registry pattern (set at CLI startup)
- Help tools NOT in `REDUCED_TOOLS`/`FULL_TOOLS` or `__all__` (internal-only)
- Agent tool list includes help tools; user-facing banner shows original count
- Soft acknowledgment allowed: "I consulted internal tool docs"

## Next Steps
- Monitor agent usage of help tools in production
- Consider additional internal tools if needed
- Plan for documentation updates
