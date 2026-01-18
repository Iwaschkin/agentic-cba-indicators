# Data Ingestion Scripts

This directory contains scripts for building and maintaining the CBA ME Indicators knowledge base. The knowledge base powers semantic search capabilities in the Agentic CBA Indicators chatbot.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Embedding Model](#embedding-model)
- [Citation Management](#citation-management)
- [Scripts Overview](#scripts-overview)
- [Detailed Documentation](#detailed-documentation)
  - [ingest_excel.py](#ingest_excelpy---master-indicators-ingestion)
  - [ingest_usecases.py](#ingest_usecasespy---use-case-projects-ingestion)
- [Data Model](#data-model)
- [Troubleshooting](#troubleshooting)
- [Adding New Data](#adding-new-data)
- [Environment Variables](#environment-variables)
  - [Path Configuration](#path-configuration)
  - [Ollama Configuration](#ollama-configuration)
  - [Citation Enrichment APIs](#citation-enrichment-apis)

---

## Quick Start

### First-Time Setup

```bash
# 1. Ensure Ollama is running with the embedding model
ollama serve
ollama pull bge-m3

# 2. Ingest the master indicator library (required)
python scripts/ingest_excel.py

# 3. Ingest example use case projects (optional)
uv add pymupdf  # Required for PDF extraction
python scripts/ingest_usecases.py
```

### Common Commands

| Command | Description |
|---------|-------------|
| `python scripts/ingest_excel.py` | Standard ingestion (upsert mode) |
| `python scripts/ingest_excel.py --clear` | Clear collections and rebuild from scratch |
| `python scripts/ingest_excel.py --dry-run` | Preview what would be indexed |
| `python scripts/ingest_excel.py --verbose` | Show detailed progress |
| `python scripts/ingest_excel.py --enrich` | Ingestion with CrossRef/Unpaywall enrichment |
| `python scripts/ingest_excel.py --preview-citations` | Preview DOI extraction stats |
| `python scripts/ingest_excel.py --preview-oa` | Preview Open Access coverage |
| `python scripts/ingest_usecases.py` | Ingest use case projects |
| `python scripts/ingest_usecases.py --clear` | Clear usecases collection first |

### Verify Installation

```bash
# Check knowledge base stats via the CLI
agentic-cba
> list knowledge base stats
```

---

## Prerequisites

### Required

- **Python 3.11+** with the agentic-cba-indicators package installed
- **Ollama** running locally with the `bge-m3` model (8K context, 1024 dimensions)
- **Source data**: `cba_inputs/CBA ME Indicators List.xlsx`

### Optional

- **PyMuPDF** (`pymupdf`) for PDF text extraction in use case ingestion:
  ```bash
  uv add pymupdf
  ```

### Ollama Setup

```bash
# Start Ollama server
ollama serve

# Pull the embedding model (1024-dimension embeddings, 8K context)
ollama pull bge-m3

# Verify it's working
curl http://localhost:11434/api/embed -d '{"model": "bge-m3", "input": "test"}'
```

---

## Embedding Model

The knowledge base uses **bge-m3** from BAAI (Beijing Academy of Artificial Intelligence) for semantic embeddings. This model was selected for its superior context length and multilingual capabilities.

### Model Specifications

| Property | Value |
|----------|-------|
| **Model** | `bge-m3` (BGE-M3-Embedding) |
| **Provider** | BAAI via Ollama |
| **Context Length** | **8,192 tokens** (~32,000 characters) |
| **Embedding Dimensions** | **1,024** |
| **Model Size** | 1.2 GB |
| **Multilingual** | 100+ languages |

### Why bge-m3?

BGE-M3 is distinguished for its **M3** capabilities:

1. **Multi-Functionality**: Supports dense retrieval, multi-vector retrieval, and sparse retrieval simultaneously
2. **Multi-Linguality**: Works across 100+ languages without translation
3. **Multi-Granularity**: Handles inputs from short sentences to long documents (up to 8K tokens)

### Context Length Comparison

| Model | Context | Dimensions | Size | Notes |
|-------|---------|------------|------|-------|
| **bge-m3** (current) | **8K tokens** | 1024 | 1.2GB | Best for long documents |
| nomic-embed-text (previous) | 2K tokens | 768 | 274MB | Good general-purpose |
| snowflake-arctic-embed | 512 tokens | 1024 | 669MB | Short text only |
| mxbai-embed-large | 512 tokens | 1024 | 670MB | Short text only |
| all-minilm | 256 tokens | 384 | 46MB | Lightweight, limited |

### Character Limits

The ingestion scripts enforce these limits to ensure reliable embedding:

| Limit | Value | Usage |
|-------|-------|-------|
| `MAX_EMBEDDING_CHARS` | 24,000 | Default max per document |
| PDF summary extraction | 4,000 | Use case project summaries |

The 24,000 character limit is ~75% of the theoretical 8K token capacity, providing a safety margin for tokenization variance.

### Switching Embedding Models

> ⚠️ **Warning**: Changing the embedding model requires a **full knowledge base rebuild** because embeddings from different models are incompatible.

To switch models:

```bash
# 1. Set the new model
export OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# 2. Pull the model
ollama pull nomic-embed-text

# 3. Rebuild the knowledge base (required!)
python scripts/ingest_excel.py --clear
python scripts/ingest_usecases.py --clear
```

### Supported Models

The following models are pre-configured with correct dimensions:

```python
EMBEDDING_DIMENSIONS = {
    "bge-m3": 1024,           # Default: 8K context, multilingual
    "nomic-embed-text": 768,  # 2K context, proven stable
    "mxbai-embed-large": 1024,
    "snowflake-arctic-embed:335m": 1024,
    "qwen3-embedding:0.6b": 1024,
    "embeddinggemma": 768,
    "all-minilm:33m": 384,
}
```

To use an unlisted model, add it to `EMBEDDING_DIMENSIONS` in `src/agentic_cba_indicators/tools/_embedding.py`.

---

## Citation Management

The ingestion scripts include comprehensive citation handling with DOI normalization, metadata enrichment from CrossRef, and Open Access status from Unpaywall.

### Citation Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXCEL SOURCE                                  │
├─────────────────────────────────────────────────────────────────┤
│  Methods Sheet columns:                                          │
│  ├── DOI, DOI.2, DOI.3, DOI.4, DOI.5                            │
│  ├── Citation, Citation.2, Citation.3, Citation.4, Citation.5   │
│  └── Unnamed: 32, 33 (spillover columns)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOI NORMALIZATION                             │
├─────────────────────────────────────────────────────────────────┤
│  1. Extract DOI from explicit DOI columns                        │
│  2. Extract embedded DOIs from citation text                     │
│  3. Normalize to canonical form: 10.xxxx/yyyy (lowercase)       │
│  4. Generate canonical URL: https://doi.org/10.xxxx/yyyy        │
│                                                                  │
│  Supported input formats:                                        │
│  ├── 10.1234/abc                                                │
│  ├── doi: 10.1234/abc                                           │
│  ├── DOI:10.1234/abc (no space)                                 │
│  ├── https://doi.org/10.1234/ABC                                │
│  └── http://dx.doi.org/10.1234/abc                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (optional --enrich flag)
┌─────────────────────────────────────────────────────────────────┐
│                    METADATA ENRICHMENT                           │
├─────────────────────────────────────────────────────────────────┤
│  CrossRef API:                                                   │
│  ├── Title (full article title)                                 │
│  ├── Authors (list of names)                                    │
│  ├── Journal name                                               │
│  ├── Publication year                                           │
│  ├── Abstract (when available)                                  │
│  └── License URL                                                │
│                                                                  │
│  Unpaywall API:                                                  │
│  ├── is_oa (boolean)                                            │
│  ├── oa_status (gold, green, hybrid, bronze, closed)            │
│  ├── pdf_url (best OA PDF location)                             │
│  ├── license (CC-BY, CC-BY-NC, etc.)                            │
│  └── version (publishedVersion, acceptedVersion)                │
└─────────────────────────────────────────────────────────────────┘
```

### Citation Commands

| Command | Description |
|---------|-------------|
| `--preview-citations` | Preview DOI extraction stats (no KB changes) |
| `--enrich-citations` | Fetch CrossRef metadata (preview only) |
| `--enrich-citations --limit 10` | Test enrichment with 10 DOIs |
| `--preview-oa` | Preview Open Access coverage via Unpaywall |
| `--enrich` | Full ingestion with CrossRef+Unpaywall enrichment |

### Preview Citations

Validate DOI extraction before running full ingestion:

```bash
python scripts/ingest_excel.py --preview-citations
```

Example output:

```
============================================================
Citation Normalization Preview
============================================================
Source: cba_inputs/CBA ME Indicators List.xlsx

=== Summary ===
Total citations: 1024
With DOI: 880 (85.9%)
Without DOI: 144 (14.1%)
DOI extracted from text: 42 (4.1%)

OK: Preview complete (no changes made to KB)
```

### Preview Open Access Coverage

Check OA availability before enrichment:

```bash
python scripts/ingest_excel.py --preview-oa
```

Example output:

```
============================================================
Open Access Coverage via Unpaywall API
============================================================
Source: cba_inputs/CBA ME Indicators List.xlsx

Fetching metadata for 880 DOIs...
  CrossRef: 736 found (83.6%)
  Unpaywall: 524 found (59.5%)
  Total enriched: 736/880 (83.6%)

Open Access Statistics:
  Total citations: 880
  OA citations: 312 (35.5%)

OA Status Breakdown:
    gold: 156
    green: 98
    hybrid: 42
    bronze: 16
```

### Citation Enrichment

Fetch metadata from CrossRef API (preview mode):

```bash
python scripts/ingest_excel.py --enrich-citations --verbose
```

For production ingestion with enrichment:

```bash
python scripts/ingest_excel.py --enrich
```

### DOI Normalization Details

The script normalizes DOIs per ISO 26324 (DOI Handbook):

**Input variants handled:**
- `10.1016/j.agee.2020.106989` - Plain DOI
- `DOI: 10.1016/j.agee.2020.106989` - With prefix
- `https://doi.org/10.1016/J.AGEE.2020.106989` - URL with uppercase
- `http://dx.doi.org/10.1016/j.agee.2020.106989` - Legacy dx.doi.org
- `(10.1016/j.agee.2020.106989)` - In parentheses

**Normalized output:**
- DOI: `10.1016/j.agee.2020.106989` (lowercase)
- URL: `https://doi.org/10.1016/j.agee.2020.106989`

### API Requirements

#### CrossRef API

CrossRef provides citation metadata. Uses the "polite pool" (faster rate limits) when email is configured:

```bash
export CROSSREF_EMAIL=your.email@example.com
```

| Variable | Description | Default |
|----------|-------------|---------|
| `CROSSREF_EMAIL` | Email for polite pool access | *(none)* |
| `CROSSREF_TIMEOUT` | Request timeout (seconds) | `15.0` |
| `CROSSREF_BATCH_DELAY` | Delay between requests | `0.1` |

**Rate limits:**
- Without email: ~1 request/second (public pool)
- With email: ~50 requests/second (polite pool)

#### Unpaywall API

Unpaywall provides Open Access metadata. **Email is required** for API access:

```bash
export UNPAYWALL_EMAIL=your.email@example.com
```

| Variable | Description | Default |
|----------|-------------|---------|
| `UNPAYWALL_EMAIL` | **Required** - Email for API access | *(none)* |
| `UNPAYWALL_TIMEOUT` | Request timeout (seconds) | `10.0` |

### Citation Data Structure

Each citation in the knowledge base includes:

```python
@dataclass
class Citation:
    # Core fields (always present)
    raw_text: str      # Original text from Excel
    text: str          # Cleaned citation text
    doi: str | None    # Normalized DOI
    url: str | None    # Canonical https://doi.org URL

    # Enrichment fields (from CrossRef)
    enriched_title: str | None
    enriched_authors: list[str]
    enriched_journal: str | None
    enriched_year: int | None
    enriched_abstract: str | None
    enrichment_source: str | None  # "crossref"

    # Open Access fields (from Unpaywall)
    is_oa: bool
    oa_status: str | None   # gold, green, hybrid, bronze, closed
    pdf_url: str | None     # Best OA PDF location
    license: str | None     # CC-BY, CC-BY-NC, etc.
    version: str | None     # publishedVersion, acceptedVersion
    host_type: str | None   # publisher, repository
```

### OA Status Types

| Status | Description |
|--------|-------------|
| `gold` | Published in an open-access journal |
| `green` | Self-archived in repository (preprint/postprint) |
| `hybrid` | Open access in a subscription journal |
| `bronze` | Free to read but no open license |
| `closed` | Not openly accessible |

---

## Scripts Overview

| Script | Purpose | Collections | Documents |
|--------|---------|-------------|-----------|
| `ingest_excel.py` | Master indicator library | `indicators`, `methods` | 224 + 223 |
| `ingest_usecases.py` | Example project data | `usecases` | Variable |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCE DATA                                  │
├─────────────────────────────────────────────────────────────────┤
│  cba_inputs/                                                     │
│  ├── CBA ME Indicators List.xlsx    ──────► ingest_excel.py     │
│  └── example/                                                    │
│      ├── *.xlsx (outcome mappings)  ──────► ingest_usecases.py  │
│      └── *.pdf  (project summaries) ──────► ingest_usecases.py  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Load & parse Excel/PDF files                                 │
│  2. Normalize data (flags → booleans, clean text)               │
│  3. Build RAG documents with stable IDs                         │
│  4. Generate embeddings via Ollama (bge-m3, 1024-dim)           │
│  5. Upsert to ChromaDB collections                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHROMADB                                      │
├─────────────────────────────────────────────────────────────────┤
│  Location: ~/.local/share/agentic-cba-indicators/kb_data/       │
│  (Windows: %LOCALAPPDATA%\agentic-cba\agentic-cba-indicators\)  │
│                                                                  │
│  Collections:                                                    │
│  ├── indicators  (224 docs) - One per indicator                 │
│  ├── methods     (223 docs) - Grouped methods per indicator     │
│  └── usecases    (variable) - Project outcomes + overviews      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Documentation

### ingest_excel.py - Master Indicators Ingestion

This script ingests the CBA ME Indicators master library from Excel into ChromaDB for semantic search.

#### Usage

```bash
python scripts/ingest_excel.py [OPTIONS]

Options:
  --file, -f PATH    Path to Excel file (default: cba_inputs/CBA ME Indicators List.xlsx)
  --clear, -c        Clear existing collections before ingesting
  --dry-run, -n      Show what would be done without making changes
  --verbose, -v      Enable detailed output
```

#### Workflow

The script follows a deterministic, repeatable 6-step workflow:

```
Step 1: Test Ollama Connection
    └── Verify embedding model is available

Step 2: Initialize ChromaDB
    └── Create/connect to persistent storage
    └── Optionally clear existing collections (--clear)

Step 3: Load Workbook
    └── Read "Indicators" sheet (224 rows)
    └── Read "Methods" sheet (~1000+ rows)

Step 4: Normalize Data
    └── Convert x/(x) flags to booleans
    └── Extract principles & criteria coverage
    └── Clean citations and text fields

Step 5: Build RAG Documents
    └── Create IndicatorDoc for each indicator
    └── Group methods by indicator → MethodsGroupDoc

Step 6: Embed & Upsert
    └── Generate embeddings in batches (size=5)
    └── Upsert to 'indicators' collection
    └── Upsert to 'methods' collection
```

#### Data Extracted

**From Indicators Sheet:**

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Unique indicator ID | `107` |
| `Component` | Category: Biotic, Abiotic, Socio-economic | `Abiotic` |
| `Class` | Sub-category | `Soil carbon` |
| `Indicator` | Full indicator name | `Soil organic carbon (SOC)` |
| `Unit` | Measurement unit | `% or g/kg` |
| `Field methods` | Supports field measurement | `true` |
| `Lab methods` | Supports lab analysis | `true` |
| `Remote sensing & modelling` | Supports remote sensing | `true` |
| `Social and participatory` | Supports social methods | `false` |
| `Production assessments` | Supports production audits | `false` |
| `Principle 1-7` | Coverage flags | `x`, `S`, or blank |
| `Criteria 1.1-7.4` | Coverage with priority marking | `x`, `P`, or blank |

**From Methods Sheet:**

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Links to indicator ID | `107` |
| `Method (General)` | General method category | `Dry combustion` |
| `Method (Specific)` | Specific technique | `LECO CN analyzer` |
| `Notes` | Additional details | `Requires sample preparation` |
| `Accuracy` | High/Medium/Low | `High` |
| `Ease of Use` | High/Medium/Low | `Low` |
| `Financial Cost` | High/Medium/Low | `High` |
| `Citation/DOI` | Reference information | DOI links |

#### CBA Principles & Criteria

The script maps indicators to the 7 CBA Principles and their 20 Criteria:

| # | Principle | Criteria Count |
|---|-----------|----------------|
| 1 | Natural Environment | 4 (1.1-1.4) |
| 2 | Social Well-being | 3 (2.1-2.3) |
| 3 | Economic Prosperity | 2 (3.1-3.2) |
| 4 | Diversity | 3 (4.1-4.3) |
| 5 | Connectivity | 2 (5.1-5.2) |
| 6 | Adaptive Capacity | 2 (6.1-6.2) |
| 7 | Harmony | 4 (7.1-7.4) |

#### Output Collections

**`indicators` Collection (224 documents)**

- **Document ID format**: `indicator:{id}` (e.g., `indicator:107`)
- **Document text**: Searchable description including indicator name, component, class, measurement approaches, and principle/criteria coverage
- **Metadata**: Structured fields for filtering (component, class, measurement flags, principle flags)

**`methods` Collection (223 documents)**

- **Document ID format**: `methods_for_indicator:{id}` (e.g., `methods_for_indicator:107`)
- **Document text**: All methods for an indicator grouped together with evaluation criteria
- **Metadata**: Indicator info + quality flags (has_high_accuracy, has_low_cost, has_high_ease)
- **Note**: Indicator ID 105 has no associated methods

#### Example Output

```
============================================================
CBA ME Indicators - Deterministic Ingestion
============================================================
Source: E:\DEV\GIT\strands\cba_inputs\CBA ME Indicators List.xlsx
Target: C:\Users\david\AppData\Local\agentic-cba\agentic-cba-indicators\kb_data

Testing Ollama connection...
  ✓ Ollama ready (embedding dim: 768)

Initializing ChromaDB at C:\...\kb_data...

Loading workbook: CBA ME Indicators List.xlsx
  Sheets found: ['Indicators', 'Methods']
  Indicators: 224 rows
  Methods: 1047 rows

Normalising data...
  Loaded 224 indicators
  Loaded methods for 223 indicators

Building RAG documents...
  ⚠ Indicators with no methods: [105]
  Built 224 indicator documents
  Built 223 method group documents (1047 total methods)

[1/2] Processing indicators...
  Embedding 224 indicator documents...
  Upserting to 'indicators' collection...

[2/2] Processing methods...
  Embedding 223 method group documents...
  Upserting to 'methods' collection...

============================================================
SUMMARY
============================================================
Indicators indexed: 224
Method groups indexed: 223
Total individual methods: 1047
Indicators without methods: [105]

✓ Knowledge base ready at: C:\...\kb_data
```

---

### ingest_usecases.py - Use Case Projects Ingestion

This script ingests example project data showing real-world indicator selections for specific agricultural contexts.

#### Usage

```bash
python scripts/ingest_usecases.py [OPTIONS]

Options:
  --clear, -c        Clear usecases collection before ingesting
  --dry-run, -n      Show what would be done without making changes
  --verbose, -v      Enable detailed output with name resolution details
```

#### Workflow

```
Step 1: Test Ollama Connection
    └── Verify embedding model is available

Step 2: Initialize ChromaDB
    └── Connect to existing knowledge base
    └── Optionally clear usecases collection (--clear)

Step 3: Load Master Indicator Library
    └── Build name-to-ID lookup table
    └── Store both original and normalized names

Step 4: For Each Use Case Project:
    ├── Load Excel (outcome-indicator mappings)
    ├── Extract PDF summary (project overview)
    ├── Resolve indicator names to IDs
    │   ├── Exact match
    │   ├── Normalized match (lowercase, collapsed spaces)
    │   └── Fuzzy match (≥85% similarity)
    └── Build RAG documents

Step 5: Embed & Upsert
    └── Generate embeddings
    └── Upsert to 'usecases' collection
```

#### Use Case Configuration

New projects are added by editing the `USE_CASES` list in the script:

```python
USE_CASES = [
    {
        "slug": "regen_cotton_chad",           # Unique identifier
        "name": "Regenerative Cotton in Chad", # Display name
        "country": "Chad",                     # Country
        "region": "Africa",                    # Region
        "commodity": "Cotton",                 # Commodity type
        "excel_file": "Indicators_for_Use_Case_Regenerative_Cotton_in_Chad.xlsx",
        "pdf_file": "Use Case Regenerative Cotton in Chad.pdf",
        "excel_sheet": "Suggested indicators", # Sheet name in Excel
    },
    # Add more projects here...
]
```

#### Name Resolution

The script resolves indicator names from use case files to IDs in the master library using a 3-tier matching strategy:

1. **Exact Match**: Direct string comparison
2. **Normalized Match**: Lowercase + collapsed whitespace
3. **Fuzzy Match**: SequenceMatcher with 85% threshold

```
Example:
  ✓ Exact: 'Soil organic carbon (SOC)' → 107
  ✓ Normalized: 'soil organic carbon (soc)' → 107
  ✓ Fuzzy (92%): 'Soil organic Carbon' → 107
  ✗ Unresolved (45%): 'Custom farm indicator'
```

#### Output Collection

**`usecases` Collection (Variable document count)**

Two document types:

**1. Overview Documents**
- **ID format**: `usecase:{slug}:overview`
- **Content**: Project summary extracted from PDF (up to 4000 chars)
- **Metadata**: Project info (name, country, region, commodity, outcome count)

**2. Outcome Documents**
- **ID format**: `usecase:{slug}:outcome:{id}`
- **Content**: Outcome description + selected indicators list
- **Metadata**: Outcome info + resolved indicator IDs (as JSON)

#### Example Output

```
============================================================
Use Case Projects - Ingestion
============================================================
Source: E:\DEV\GIT\strands\cba_inputs\example
Target: C:\Users\david\AppData\Local\agentic-cba\agentic-cba-indicators\kb_data

Testing Ollama connection...
  ✓ Ollama ready (embedding dim: 1024)

Initializing ChromaDB at C:\...\kb_data...

Loading master indicator library...
  Loaded 224 indicators for name resolution

==================================================
Processing: Regenerative Cotton in Chad
==================================================
  Loading outcomes from Excel...
    Found 12 outcomes
  Extracting PDF summary...
    Extracted 3847 chars
  Embedding 13 documents...
  Upserting to 'usecases' collection...

  Summary for regen_cotton_chad:
    Overview doc: Yes
    Outcome docs: 12
    Resolved indicators: 47
    Unresolved indicators: 3

============================================================
SUMMARY
============================================================
Use cases processed: 1
Total documents indexed: 13

✓ Use cases ready in 'usecases' collection at: C:\...\kb_data
```

---

## Data Model

### ChromaDB Collections Summary

```
Knowledge Base
├── indicators (224 docs)
│   ├── Document ID: indicator:{id}
│   ├── Embedding: 1024-dim (bge-m3)
│   ├── Text: Indicator description + coverage info
│   └── Metadata:
│       ├── id, component, class, unit
│       ├── field_methods, lab_methods, remote_sensing, ...
│       ├── principle_1..7 (boolean flags)
│       ├── total_principles, total_criteria
│       └── principles_json, criteria_json
│
├── methods (223 docs)
│   ├── Document ID: methods_for_indicator:{id}
│   ├── Embedding: 1024-dim (bge-m3)
│   ├── Text: All methods grouped with evaluations
│   └── Metadata:
│       ├── indicator_id, indicator, unit
│       ├── method_count
│       └── has_high_accuracy, has_low_cost, has_high_ease
│
└── usecases (variable)
    ├── Overview docs: usecase:{slug}:overview
    │   └── Metadata: use_case_name, country, region, commodity
    └── Outcome docs: usecase:{slug}:outcome:{id}
        └── Metadata: outcome_id, indicator_ids_json
```

### Document ID Stability

All document IDs are deterministic and stable across runs:

| Collection | ID Format | Example |
|------------|-----------|---------|
| indicators | `indicator:{id}` | `indicator:107` |
| methods | `methods_for_indicator:{id}` | `methods_for_indicator:107` |
| usecases | `usecase:{slug}:overview` | `usecase:regen_cotton_chad:overview` |
| usecases | `usecase:{slug}:outcome:{id}` | `usecase:regen_cotton_chad:outcome:1` |

This enables safe **upsert** operations - running ingestion multiple times updates existing documents rather than creating duplicates.

---

## Troubleshooting

### Common Issues

#### Ollama Connection Failed

```
Error: Ollama connection failed: Connection refused
```

**Solution**: Start Ollama and pull the embedding model:
```bash
ollama serve
ollama pull bge-m3
```

#### Excel File Not Found

```
Error: File not found: cba_inputs/CBA ME Indicators List.xlsx
```

**Solution**: Ensure the source Excel file is in the correct location.

#### PyMuPDF Not Installed

```
⚠ pymupdf not installed. Run: uv add pymupdf
```

**Solution**: Install PyMuPDF for PDF extraction:
```bash
uv add pymupdf
```

#### Unresolved Indicator Names

```
⚠ Total unresolved indicator names: 3
```

**Cause**: Some indicator names in use case files don't match the master library.

**Solutions**:
1. Run with `--verbose` to see which names failed
2. Adjust the `FUZZY_MATCH_THRESHOLD` (default 0.85)
3. Manually update indicator names in source Excel files

### Reset Knowledge Base

To completely rebuild the knowledge base:

```bash
# Clear and rebuild everything
python scripts/ingest_excel.py --clear
python scripts/ingest_usecases.py --clear
```

Or delete the data directory:
```bash
# Linux/macOS
rm -rf ~/.local/share/agentic-cba-indicators/kb_data

# Windows
rmdir /s %LOCALAPPDATA%\agentic-cba\agentic-cba-indicators\kb_data
```

---

## Adding New Data

### Adding a New Use Case Project

1. **Prepare files** in `cba_inputs/example/`:
   - Excel file with outcome-indicator mappings
   - PDF file with project overview (optional)

2. **Add configuration** to `USE_CASES` in `ingest_usecases.py`:
   ```python
   {
       "slug": "my_new_project",
       "name": "My New Project",
       "country": "Country Name",
       "region": "Region",
       "commodity": "Commodity",
       "excel_file": "my_project_indicators.xlsx",
       "pdf_file": "my_project_overview.pdf",
       "excel_sheet": "Sheet Name",
   }
   ```

3. **Run ingestion**:
   ```bash
   python scripts/ingest_usecases.py --verbose
   ```

### Excel File Format for Use Cases

The use case Excel file should have these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `Outcome id` | Yes | Unique outcome identifier (e.g., "1", "2a") |
| `Outcome` | Yes | Outcome description text |
| `Indicators (selected from CBA ME Indicators List)` | Yes | Semicolon-separated indicator names |
| `Extra indicators` | No | Additional indicators not in master list |

### Updating the Master Library

When the master Excel file is updated:

```bash
# Incremental update (recommended)
python scripts/ingest_excel.py

# Or full rebuild
python scripts/ingest_excel.py --clear
```

---

## Environment Variables

### Path Configuration

Override default paths with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTIC_CBA_DATA_DIR` | Data directory (knowledge base) | Platform-specific |
| `AGENTIC_CBA_CONFIG_DIR` | Config directory | Platform-specific |

### Ollama Configuration

Configure Ollama embeddings for local or cloud usage:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_API_KEY` | Bearer token for Ollama Cloud | *(none)* |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `bge-m3` |
| `OLLAMA_MAX_EMBEDDING_CHARS` | Max characters per embedding | `24000` |

### Citation Enrichment APIs

Configure metadata enrichment from CrossRef and Unpaywall:

| Variable | Description | Default |
|----------|-------------|---------|
| `CROSSREF_EMAIL` | Email for CrossRef polite pool | *(none)* |
| `CROSSREF_TIMEOUT` | CrossRef request timeout (seconds) | `15.0` |
| `CROSSREF_BATCH_DELAY` | Delay between CrossRef requests | `0.1` |
| `UNPAYWALL_EMAIL` | **Required** for Unpaywall API access | *(none)* |
| `UNPAYWALL_TIMEOUT` | Unpaywall request timeout (seconds) | `10.0` |

### Examples

**Local Ollama (default):**
```bash
# No configuration needed, uses localhost
python scripts/ingest_excel.py
```

**Ollama Cloud:**
```bash
# Set credentials for ollama.com cloud API
export OLLAMA_HOST=https://ollama.com
export OLLAMA_API_KEY=your_api_key_here
python scripts/ingest_excel.py
```

**Self-hosted remote Ollama:**
```bash
# Point to your own Ollama server
export OLLAMA_HOST=https://ollama.mycompany.com
python scripts/ingest_excel.py
```

**Custom embedding model:**
```bash
export OLLAMA_EMBEDDING_MODEL=all-minilm
python scripts/ingest_excel.py --clear  # Rebuild with new embeddings
```

> ⚠️ **Important**: If you change the embedding model, you must rebuild the knowledge base with `--clear` since embeddings from different models are not compatible.
