# Agentic CBA Indicators - AI Coding Instructions

## Project Overview

A CLI chatbot that queries weather, climate, socio-economic data, and **CBA ME Indicators** using the **Strands Agents SDK**. Supports multiple AI providers: **Ollama** (local), **Anthropic**, **OpenAI**, **AWS Bedrock**, and **Google Gemini**. Includes a local RAG knowledge base using ChromaDB for semantic search over indicator and measurement method data.

## Technology Stack

- **Language:** Python 3.11+
- **Package Manager:** uv
- **Package Name:** agentic-cba-indicators (src layout)
- **AI Framework:** [strands-agents](https://strandsagents.com/) with multi-provider support
- **AI Providers:** Ollama (default), Anthropic, OpenAI, AWS Bedrock, Google Gemini
- **Vector Store:** ChromaDB (XDG-style data directory)
- **Embeddings:** Ollama `bge-m3` model (8K context, 1024 dimensions)
- **APIs:** Open-Meteo (weather/climate), World Bank API, REST Countries API

## Quick Start

```bash
# Setup
uv sync
.venv\Scripts\activate  # Windows

# For cloud providers, install extras:
uv add 'strands-agents[anthropic]'  # Anthropic
uv add 'strands-agents[openai]'     # OpenAI
uv add 'strands-agents[bedrock]'    # AWS Bedrock
uv add 'strands-agents[gemini]'     # Google Gemini

# Ingest knowledge base (first time or after Excel updates)
python scripts/ingest_excel.py

# Run the chatbot
agentic-cba                        # Uses bundled config (Ollama default)
agentic-cba --provider=anthropic   # Use Anthropic (needs ANTHROPIC_API_KEY)
agentic-cba --provider=openai      # Use OpenAI (needs OPENAI_API_KEY)
agentic-cba --provider=bedrock     # Use AWS Bedrock (needs AWS credentials)
agentic-cba --provider=gemini      # Use Google Gemini (needs GOOGLE_API_KEY)
```

## Project Structure

```
agentic-cba-indicators/
├── src/agentic_cba_indicators/  # Main package (src layout)
│   ├── __init__.py              # Version, exports
│   ├── py.typed                 # PEP 561 typing marker
│   ├── cli.py                   # CLI entry point (agentic-cba command)
│   ├── paths.py                 # XDG-style path resolution
│   ├── config/
│   │   ├── __init__.py          # Config exports
│   │   ├── provider_factory.py  # Model creation factory
│   │   ├── providers.yaml       # Bundled default config
│   │   └── examples/            # Example configs per provider
│   ├── prompts/
│   │   ├── __init__.py          # Prompt loader (importlib.resources)
│   │   └── *.md                 # System prompts
│   └── tools/
│       ├── __init__.py          # Tool exports, REDUCED_TOOLS, FULL_TOOLS
│       ├── weather.py           # Open-Meteo current weather & forecast
│       ├── climate.py           # Climate normals & historical data
│       ├── socioeconomic.py     # World Bank & REST Countries APIs
│       └── knowledge_base.py    # ChromaDB RAG for CBA indicators
├── scripts/
│   └── ingest_excel.py          # Excel → ChromaDB ingestion
├── tests/                       # pytest test suite
├── cba_inputs/                  # Source data files
├── pyproject.toml               # Package configuration (hatchling build)
└── .python-version              # Python 3.11
```

## Key Patterns

### Path Resolution

Uses `platformdirs` for XDG-style paths with environment variable overrides:

```python
from agentic_cba_indicators.paths import get_kb_path, get_data_dir, get_config_dir

# Data: ~/.local/share/agentic-cba-indicators/ (Linux) or %LOCALAPPDATA%\agentic-cba\agentic-cba-indicators\ (Windows)
# Config: ~/.config/agentic-cba-indicators/ (Linux) or %APPDATA%\agentic-cba-indicators\ (Windows)

# Override with:
# AGENTIC_CBA_DATA_DIR, AGENTIC_CBA_CONFIG_DIR
```

### Creating Strands Tools

Tools use the `@tool` decorator from strands. See [src/agentic_cba_indicators/tools/weather.py](../src/agentic_cba_indicators/tools/weather.py):

```python
from strands import tool

@tool
def get_current_weather(city: str) -> str:
    """
    Get current weather conditions for a city.

    Args:
        city: Name of the city (e.g., "London", "New York")

    Returns:
        Current weather information
    """
    # Tool implementation...
```

### Multi-Provider Configuration

Configuration resolution order:
1. Explicit `--config=path/to/file.yaml`
2. User config: `~/.config/agentic-cba-indicators/providers.yaml`
3. Bundled default: `agentic_cba_indicators/config/providers.yaml`

```yaml
active_provider: ollama  # or anthropic, openai, bedrock, gemini

providers:
  ollama:
    host: "http://localhost:11434"
    model_id: "llama3.1:latest"
    temperature: 0.1

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}  # Environment variable
    model_id: "claude-sonnet-4-20250514"
    max_tokens: 8192

agent:
  tool_set: reduced  # "reduced" (19 tools) or "full" (52 tools)
  conversation_window: 5
```

### Agent Creation

The agent is created from config via the CLI module:

```python
from agentic_cba_indicators.cli import create_agent_from_config

agent, provider_config, agent_config = create_agent_from_config()
# Or with override:
agent, _, _ = create_agent_from_config(provider_override="anthropic")
```

### Adding New Tools

1. Create tool in `src/agentic_cba_indicators/tools/` with `@tool` decorator
2. Include clear docstring with Args/Returns (used by LLM)
3. Export in `src/agentic_cba_indicators/tools/__init__.py`
4. Add to `REDUCED_TOOLS` or `FULL_TOOLS` in `tools/__init__.py`

### Knowledge Base (RAG) Pattern

The knowledge base uses ChromaDB with Ollama embeddings. See [src/agentic_cba_indicators/tools/knowledge_base.py](../src/agentic_cba_indicators/tools/knowledge_base.py):

```python
from strands import tool
import chromadb
from agentic_cba_indicators.paths import get_kb_path

@tool
def search_indicators(query: str, n_results: int = 5) -> str:
    """Search CBA indicators by semantic similarity."""
    client = chromadb.PersistentClient(path=str(get_kb_path()))
    collection = client.get_collection("indicators")
    query_embedding = _get_embedding(query)  # via Ollama
    results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    # Format and return results...
```

**Ingestion Script (`scripts/ingest_excel.py`):**

Deterministic, repeatable ingestion following this workflow:
1. **Load workbook** - Read Indicators and Methods sheets from Excel
2. **Normalise** - Convert `x`/`(x)` flags to booleans, clean citations
3. **Build RAG documents** - Create stable document IDs (`indicator:{id}`, `methods_for_indicator:{id}`)
4. **Embed** - Generate embeddings via Ollama (with truncation for large docs)
5. **Upsert** - Safe incremental updates using stable IDs
6. **Persist** - ChromaDB PersistentClient at XDG data directory

```bash
# Standard ingestion (upsert)
python scripts/ingest_excel.py

# Clear and rebuild
python scripts/ingest_excel.py --clear

# Preview without changes
python scripts/ingest_excel.py --dry-run

# Verbose output
python scripts/ingest_excel.py --verbose
```

**Data model:**
- `indicators` collection: 224 documents, one per indicator (ID format: `indicator:{id}`)
- `methods` collection: 223 documents, one per indicator with ALL methods grouped (ID format: `methods_for_indicator:{id}`)
- Note: Indicator id=105 has no associated methods

## Dependencies

Use `uv add <package>` to add dependencies:
```bash
uv add requests           # Runtime dependency
uv add --dev pytest       # Development dependency
```

## External APIs (No Keys Required)

- **Open-Meteo:** Weather forecasts, historical data, climate normals
- **World Bank:** GDP, population, inflation, life expectancy, etc.
- **REST Countries:** Country profiles, demographics, currencies

---

*Update this file as the project evolves with new patterns and conventions.*
