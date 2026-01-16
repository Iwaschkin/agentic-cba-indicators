# Strands CLI Chatbot - AI Coding Instructions

## Project Overview

A CLI chatbot that queries weather, climate, socio-economic data, and **CBA ME Indicators** using the **Strands Agents SDK** with **Ollama** as the local AI provider. Includes a local RAG knowledge base using ChromaDB for semantic search over indicator and measurement method data.

## Technology Stack

- **Language:** Python 3.11+
- **Package Manager:** uv
- **AI Framework:** [strands-agents](https://strandsagents.com/) with Ollama model provider
- **Vector Store:** ChromaDB (local persistence in `kb_data/`)
- **Embeddings:** Ollama `nomic-embed-text` model
- **APIs:** Open-Meteo (weather/climate), World Bank API, REST Countries API

## Quick Start

```bash
# Setup
uv sync
.venv\Scripts\activate  # Windows

# Ensure Ollama is running with required models
ollama pull llama3.1        # Chat model
ollama pull nomic-embed-text # Embedding model
ollama serve

# Ingest knowledge base (first time or after Excel updates)
python scripts/ingest_excel.py

# Run the chatbot
python main.py
python main.py --model=mistral --host=http://localhost:11434
```

## Project Structure

```
strands/
├── main.py              # CLI entry point, agent configuration
├── tools/               # Custom Strands tools
│   ├── __init__.py      # Exports all tools
│   ├── weather.py       # Open-Meteo current weather & forecast
│   ├── climate.py       # Climate normals & historical data
│   ├── socioeconomic.py # World Bank & REST Countries APIs
│   └── knowledge_base.py# ChromaDB RAG for CBA indicators
├── scripts/
│   └── ingest_excel.py  # Excel → ChromaDB ingestion
├── cba_inputs/          # Source data files
│   └── CBA ME Indicators List.xlsx
├── kb_data/             # ChromaDB vector store (gitignored)
├── pyproject.toml       # Dependencies managed by uv
└── .python-version      # Python 3.11
```

## Key Patterns

### Creating Strands Tools

Tools use the `@tool` decorator from strands. See [tools/weather.py](../tools/weather.py):

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

### Agent Configuration

The agent is configured in `main.py` with Ollama and custom tools:

```python
from strands import Agent
from strands.models.ollama import OllamaModel

agent = Agent(
    model=OllamaModel(host="http://localhost:11434", model_id="llama3.1"),
    system_prompt=SYSTEM_PROMPT,
    tools=[get_current_weather, get_weather_forecast, ...],
)
```

### Adding New Tools

1. Create tool in `tools/` with `@tool` decorator
2. Include clear docstring with Args/Returns (used by LLM)
3. Export in `tools/__init__.py`
4. Add to agent's tools list in `main.py`

### Knowledge Base (RAG) Pattern

The knowledge base uses ChromaDB with Ollama embeddings. See [tools/knowledge_base.py](../tools/knowledge_base.py):

```python
from strands import tool
import chromadb

@tool
def search_indicators(query: str, n_results: int = 5) -> str:
    """Search CBA indicators by semantic similarity."""
    collection = _get_collection("indicators")
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
6. **Persist** - ChromaDB PersistentClient at `kb_data/`

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
