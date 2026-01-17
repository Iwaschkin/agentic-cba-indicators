# System Patterns

## Architecture
- CLI entry point constructs agent from configuration
- Tool modules implement external data access
- Shared utilities for HTTP and geocoding
- Knowledge base ingestion scripts populate ChromaDB

## Key Patterns
- Configuration resolution order: explicit path -> user config -> bundled default
- Tools exposed via Strands `@tool` decorator
- Paths resolved via platformdirs with environment overrides
