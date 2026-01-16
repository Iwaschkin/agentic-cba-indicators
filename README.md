# CBA Data Assistant

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
python main.py

# Run with cloud providers
python main.py --provider=anthropic   # Requires ANTHROPIC_API_KEY
python main.py --provider=openai      # Requires OPENAI_API_KEY
python main.py --provider=gemini      # Requires GOOGLE_API_KEY
python main.py --provider=bedrock     # Requires AWS credentials
```

## Configuration

Edit `config/providers.yaml` to set your preferences:

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

## Example Queries

```
You: What's the weather in Tokyo?
You: Find indicators for soil health measurement
You: Show indicators for a cotton farm in Chad
You: Compare soil carbon indicators
```

## Project Structure

```
strands/
├── main.py              # CLI entry point
├── config/
│   ├── providers.yaml   # Provider configuration
│   ├── provider_factory.py  # Model creation factory
│   └── examples/        # Example configs per provider
├── tools/               # Custom Strands tools
├── prompts/             # System prompts
└── kb_data/             # ChromaDB vector store
```

## Knowledge Base

Ingest CBA indicators before first use:

```bash
python scripts/ingest_excel.py
```

## License

MIT
