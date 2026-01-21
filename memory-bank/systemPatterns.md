# System Patterns

## Architecture
- CLI entry point constructs agent from configuration
- Tool modules implement external data access
- Shared utilities for HTTP and geocoding
- Knowledge base ingestion scripts populate ChromaDB
- **MCP Server** (`mcp_server.py`) exposes all tools via FastMCP stdio transport

## Key Patterns
- Configuration resolution order: explicit path -> user config -> bundled default
- Tools exposed via Strands `@tool` decorator
- Paths resolved via platformdirs with environment overrides
- **Tool Sets**: FULL_TOOLS (58 tools) vs REDUCED_TOOLS (20 tools)
- **Tool Name Constants**: FULL_TOOL_NAMES, REDUCED_TOOL_NAMES for filtering
- **MCP Native Discovery**: Help tools removed - MCP provides list_tools capability
