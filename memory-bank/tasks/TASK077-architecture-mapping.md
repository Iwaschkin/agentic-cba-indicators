# [TASK077] - Architecture & Module Discovery

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Systematic code review Phase 1: Map system architecture, component boundaries, data flows, and integration points.

## Architecture Overview

### System Structure
```
agentic-cba-indicators/
├── CLI Layer (cli.py)
│   ├── Entry point: main()
│   ├── Agent creation: create_agent_from_config()
│   └── Conversation loop with streaming
│
├── Configuration Layer (config/)
│   ├── provider_factory.py - Multi-provider model creation
│   ├── _secrets.py - API key management
│   └── providers.yaml - Default configuration
│
├── Tool Layer (tools/)
│   ├── External APIs (weather, climate, socioeconomic, etc.)
│   ├── Knowledge Base (knowledge_base.py)
│   └── Internal Utilities (_http, _geo, _embedding, _help)
│
├── Prompts Layer (prompts/)
│   └── System prompts for agent behavior
│
└── Ingestion Scripts (scripts/)
    ├── ingest_excel.py - CBA indicators ingestion
    └── ingest_usecases.py - Use case ingestion
```

### Component Responsibilities

#### 1. CLI (cli.py)
- **Entry Point**: `main()` function with argparse
- **Agent Factory**: `create_agent_from_config()` creates Strands Agent
- **Providers**: Ollama (default), Anthropic, OpenAI, Bedrock, Gemini
- **Tool Sets**: REDUCED_TOOLS (~19) or FULL_TOOLS (~52)

#### 2. Configuration (config/)
- **provider_factory.py**:
  - Config resolution: explicit → user config → bundled default
  - Environment variable expansion with whitelist (ALLOWED_ENV_VARS)
  - Schema validation for providers.yaml
  - Model instantiation for each provider type
- **_secrets.py**:
  - Lazy API key loading from environment
  - Optional .env support via python-dotenv
  - Supported keys: GFW, USDA_FAS, Anthropic, OpenAI, Google, CrossRef, Unpaywall

#### 3. Tools (tools/)

**External Data APIs** (No API key required):
- weather.py - Open-Meteo current/forecast
- climate.py - Open-Meteo climate normals
- nasa_power.py - NASA POWER agricultural climate
- soilgrids.py - ISRIC SoilGrids soil data
- socioeconomic.py - World Bank & REST Countries
- biodiversity.py - GBIF species data
- labor.py - ILO STAT labor data
- gender.py - World Bank gender data
- sdg.py - UN SDG indicators
- agriculture.py - FAO agriculture data

**External Data APIs** (API key required):
- forestry.py - Global Forest Watch (GFW_API_KEY)
- commodities.py - USDA FAS (USDA_FAS_API_KEY)

**Knowledge Base**:
- knowledge_base.py - 17 tools for CBA indicator search/comparison

**Internal Utilities** (underscore-prefixed):
- _http.py - Shared HTTP client with retry logic
- _geo.py - Geocoding and coordinate validation
- _embedding.py - Ollama embedding generation
- _crossref.py - CrossRef DOI metadata
- _unpaywall.py - Unpaywall OA metadata
- _mappings.py - Country code mappings
- _help.py - Internal agent help tools

#### 4. Paths (paths.py)
- XDG-style path resolution via platformdirs
- Environment overrides: AGENTIC_CBA_DATA_DIR, AGENTIC_CBA_CONFIG_DIR
- Path traversal prevention with validation

#### 5. Ingestion Scripts (scripts/)
- **ingest_excel.py**:
  - 1687 lines, complex Excel → ChromaDB pipeline
  - DOI normalization, CrossRef/Unpaywall enrichment
  - Citation dataclass with display/embed separation
  - Batch embedding with rate limiting
- **ingest_usecases.py**:
  - PDF extraction via PyMuPDF
  - Use case project ingestion

### Data Flow

```
User Input → CLI → Agent → Tool Invocation
                      ↓
              ┌───────────────────┐
              │ Tool Execution    │
              │                   │
              │ External API Call │
              │     or            │
              │ ChromaDB Query    │
              └───────────────────┘
                      ↓
              Response Formatting
                      ↓
              Streamed to User
```

### External Dependencies

| Dependency | Purpose | Min Version |
|------------|---------|-------------|
| strands-agents | AI agent framework | 1.22.0 |
| chromadb | Vector store | 1.4.1 |
| httpx | HTTP client | 0.28.1 |
| pandas | Data manipulation | 2.3.3 |
| openpyxl | Excel reading | 3.1.5 |
| platformdirs | XDG paths | 4.0.0 |
| pyyaml | Config parsing | 6.0.3 |
| pymupdf | PDF extraction | 1.26.7 |

### Security Boundaries

1. **Config Trust Boundary**: YAML files can contain env var references
2. **API Trust Boundary**: External APIs (Open-Meteo, World Bank, etc.)
3. **Embedding Trust Boundary**: Ollama (local or cloud)
4. **Vector Store Trust Boundary**: ChromaDB local storage

### Concurrency Model
- Synchronous, single-threaded execution
- Rate limiting via time.sleep() for Ollama embeddings
- No async/await patterns in core code

## Key Patterns Identified

1. **Tool Decorator Pattern**: All tools use `@tool` from strands
2. **Retry with Backoff**: HTTP and embedding operations
3. **Error Sanitization**: Credentials removed from error messages
4. **Bounded Caching**: Geocode cache with LRU eviction
5. **Lazy Loading**: API keys loaded on first access
6. **Config Validation**: Schema checks on YAML load

## Implementation Plan
- [x] Map module structure
- [x] Document component responsibilities
- [x] Identify data flows
- [x] Document security boundaries
- [x] Identify key patterns

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Read memory bank | Complete | 2026-01-18 | Reviewed all 6 core files |
| 1.2 | Map CLI and config | Complete | 2026-01-18 | cli.py, provider_factory.py, _secrets.py |
| 1.3 | Map tool modules | Complete | 2026-01-18 | 22 modules identified |
| 1.4 | Map ingestion scripts | Complete | 2026-01-18 | 2 scripts, ~2000 lines |
| 1.5 | Document architecture | Complete | 2026-01-18 | This document |

## Progress Log
### 2026-01-18
- Completed full architecture mapping
- Identified 22 tool modules (12 external APIs, 10 internal utilities)
- Documented security boundaries and data flows
- Phase 2 Security Analysis: Verified all P0/P1 issues from v1 resolved
- Phase 3 Integration Review: Cross-module patterns analyzed
- Phase 4 Operational Review: All 212 tests passing
- Phase 5 Findings Synthesis: Created final report
- Created `code-review-findings-2026-01-18-v2.md`

## Final Deliverable
[code-review-findings-2026-01-18-v2.md](../../docs/dev/plan_phase1a/code-review-findings-2026-01-18-v2.md)
