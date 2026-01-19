# Agentic CBA Indicators

A CLI chatbot for sustainable agriculture that queries weather, climate, socio-economic data, and **CBA ME Indicators** using the **Strands Agents SDK**.

## Features

- 🌤️ Weather and climate data (Open-Meteo, NASA POWER)
- 🪨 Soil properties and carbon content (ISRIC SoilGrids)
- 🌱 Biodiversity data (GBIF)
- 📊 Labor and gender statistics (ILO, World Bank)
- 🌾 Agriculture data (FAO, USDA FAS)
- 🎯 UN SDG indicators
- 📋 CBA ME Indicators and measurement methods
- 📁 Real project use cases
- 🖥️ Streamlit web UI with PDF context and report export

## Supported AI Providers

| Provider | Model Examples | Installation |
|----------|---------------|--------------|
| **Ollama** (default) | llama3.1, qwen2.5 | Local install |
| **Anthropic** | Claude Sonnet 4 | `uv add 'strands-agents[anthropic]'` |
| **OpenAI** | GPT-4o | `uv add 'strands-agents[openai]'` |
| **AWS Bedrock** | Claude, Nova | `uv add 'strands-agents[bedrock]'` |
| **Google Gemini** | Gemini 2.5 | `uv add 'strands-agents[gemini]'` |

## Quick Start

```bash
# Setup
uv sync
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run with Ollama (default)
ollama serve
agentic-cba

# Run with cloud providers
agentic-cba --provider=anthropic   # Requires ANTHROPIC_API_KEY
agentic-cba --provider=openai      # Requires OPENAI_API_KEY
agentic-cba --provider=gemini      # Requires GOOGLE_API_KEY
agentic-cba --provider=bedrock     # Requires AWS credentials
```

## Streamlit Web UI

Launch the web UI (chat, provider selection, PDF context, report export):

```bash
agentic-cba-ui

# Or run directly with streamlit
streamlit run src/agentic_cba_indicators/ui.py
```

## Configuration

The CLI looks for configuration in this order:
1. Explicit `--config=path/to/file.yaml`
2. User config: `~/.config/agentic-cba-indicators/providers.yaml` (Linux) or `%APPDATA%\agentic-cba-indicators\providers.yaml` (Windows)
3. Bundled default config

Example `providers.yaml`:

```yaml
active_provider: ollama  # or anthropic, openai, bedrock, gemini

providers:
  ollama:
    host: "http://localhost:11434"
    model_id: "llama3.1:latest"

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model_id: "claude-sonnet-4-20250514"

  openai:
    api_key: ${OPENAI_API_KEY}
    model_id: "gpt-4o"

agent:
  tool_set: reduced  # or "full" for cloud models
  conversation_window: 5
```

Environment variables are supported using `${VAR_NAME}` syntax.

## Data Storage

Data is stored in platform-appropriate locations:
- **Linux**: `~/.local/share/agentic-cba-indicators/`
- **macOS**: `~/Library/Application Support/agentic-cba-indicators/`
- **Windows**: `%LOCALAPPDATA%\agentic-cba\agentic-cba-indicators\`

Override with environment variables:
- `AGENTIC_CBA_DATA_DIR` - Knowledge base and data storage
- `AGENTIC_CBA_CONFIG_DIR` - Configuration files

## Embedding Configuration

The knowledge base uses **Ollama for embeddings** (semantic search), which is separate from the LLM provider used for chat. This means you can use Claude/GPT for conversations while using Ollama (local or cloud) for embeddings.

### Local Ollama (Default)

```bash
# Start Ollama locally
ollama serve
ollama pull bge-m3

# Run with any LLM provider - embeddings use local Ollama
agentic-cba --provider=anthropic
```

### Ollama Cloud

Use [Ollama Cloud](https://ollama.com) for embeddings without running Ollama locally:

```bash
# Set Ollama Cloud credentials
export OLLAMA_HOST=https://ollama.com
export OLLAMA_API_KEY=your_api_key_here

# Now you can run fully cloud-based
agentic-cba --provider=anthropic
```

### Embedding Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_API_KEY` | Bearer token (for Ollama Cloud) | *(none)* |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `bge-m3` |

> ⚠️ **Note**: If you change the embedding model or switch between local/cloud Ollama, rebuild the knowledge base:
> ```bash
> python scripts/ingest_excel.py --clear
> ```

## Example Queries

```
You: What's the weather in Tokyo?
You: Find indicators for soil health measurement
You: Show indicators for a cotton farm in Chad
You: Compare soil carbon indicators
```

## Project Structure

```
agentic-cba-indicators/
├── src/agentic_cba_indicators/  # Main package
│   ├── cli.py                   # CLI entry point (agentic-cba command)
│   ├── ui.py                    # Streamlit UI entry point (agentic-cba-ui command)
│   ├── paths.py                 # XDG-style path resolution
│   ├── config/                  # Provider configuration
│   ├── prompts/                 # System prompts
│   └── tools/                   # Custom Strands tools (52 total)
├── scripts/                     # Data ingestion scripts
├── tests/                       # pytest test suite
└── pyproject.toml               # Package configuration
```

## Knowledge Base

Ingest CBA indicators before first use:

```bash
python scripts/ingest_excel.py
```

## Documentation

- [Tools Reference](docs/tools-reference.md) - Complete list of available tools
- [Known Limitations](docs/known-limitations.md) - Documented constraints and limitations
- [Architecture Decision Records](docs/adr/README.md) - Key design decisions

## Contributing

See CONTRIBUTING.md for tool authoring guidelines and testing expectations.

## License

MIT
