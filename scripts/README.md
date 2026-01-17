# Data Ingestion Scripts

This directory contains scripts for building and maintaining the CBA ME Indicators knowledge base. The knowledge base powers semantic search capabilities in the Agentic CBA Indicators chatbot.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Scripts Overview](#scripts-overview)
- [Detailed Documentation](#detailed-documentation)
  - [ingest_excel.py](#ingest_excelpy---master-indicators-ingestion)
  - [ingest_usecases.py](#ingest_usecasespy---use-case-projects-ingestion)
- [Data Model](#data-model)
- [Troubleshooting](#troubleshooting)
- [Adding New Data](#adding-new-data)

---

## Quick Start

### First-Time Setup

```bash
# 1. Ensure Ollama is running with the embedding model
ollama serve
ollama pull nomic-embed-text

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
- **Ollama** running locally with the `nomic-embed-text` model
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

# Pull the embedding model (768-dimension embeddings)
ollama pull nomic-embed-text

# Verify it's working
curl http://localhost:11434/api/embed -d '{"model": "nomic-embed-text", "input": "test"}'
```

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
│  4. Generate embeddings via Ollama (nomic-embed-text)           │
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
  ✓ Ollama ready (embedding dim: 768)

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
│   ├── Embedding: 768-dim (nomic-embed-text)
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
│   ├── Embedding: 768-dim
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
ollama pull nomic-embed-text
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
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `nomic-embed-text` |

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
