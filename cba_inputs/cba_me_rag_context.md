# CBA ME Indicators List - RAG Context Reference

## 1. Overview

This document describes the structure, relationships, and recommended retrieval strategy for the Excel workbook:

- **File:** `CBA ME Indicators List.xlsx`
- **Purpose:** Serve as authoritative context for a local RAG system using ChromaDB and Ollama embeddings

The workbook contains **two sheets**:
1. `Indicators` - master list of indicators
2. `Methods` - measurement methods linked to indicators

---

## 2. Sheet: Indicators

### 2.1 Dimensions
- Rows: 224
- Columns: 39
- One row per indicator

### 2.2 Primary Key
- `id` - integer, unique (1 to 224)

### 2.3 Core Descriptor Columns
- `Component`
- `Class`
- `Indicator` - free-text description
- `Unit`

These fields define *what* the indicator is.

### 2.4 Measurement Category Flags
Each column contains `x`, `(x)`, or blank.

- `Field methods`
- `Lab methods`
- `Remote sensing & modelling`
- `Social and partcipatory`
- `Production assessments and audits`

Interpretation:
- `x` or `(x)` = applicable
- blank = not applicable

These should be treated as categorical metadata, not free text.

### 2.5 Principles and Criteria Coverage

Indicators are mapped against Principles 1-7 and their criteria.

Examples:
- `Principle: 1. Natural Environment`
  - `1.1 Avoid ecosystem degradation`
  - `1.2 Minimize GHG emissions and enhance sinks`
- `Principle: 6. Adaptive Capacity`
  - `6.1 Reduce socioecological risks`
  - `6.2 Enhance innovation capacity`

Values are `x` or blank.

### 2.6 Coverage Totals
- `Total principles covered`
- `Total criteria covered`

Numeric summaries derived from the coverage flags.

---

## 3. Sheet: Methods

### 3.1 Dimensions
- Rows: 801
- Columns: 34
- Multiple rows per indicator

### 3.2 Foreign Key Relationship
- `id` - foreign key referencing `Indicators.id`

Notes:
- One-to-many relationship
- Indicator `id = 105` has **no** corresponding method rows

### 3.3 Duplicated Context Fields
- `Indicator`
- `Unit`

These repeat data from the Indicators sheet and can be treated as denormalised convenience fields.

### 3.4 Method Description Fields
- `Method  (General)`
- `Method  (Specific)`
- `Notes`

`Notes` is the most semantically rich free-text field.

### 3.5 Method Evaluation Fields
Each category includes three columns.

**Accuracy**
- `Accuracy (High/Medium/Low)`
- `Accuracy (Data)`
- `Accuracy (Inidicator Range)`

**Ease of Use**
- `Ease of Use (High/Medium/Low)`
- `Ease of Use (Data)`
- `Ease of Use (Inidcator Range)`

**Financial Cost**
- `Financial Cost (High/Medium/Low)`
- `Financial Cost  (Data)`
- `Financial Cost (Indicator Range)`

### 3.6 Citations
- `DOI`, `Citation`
- Repeated pairs up to `DOI.5`, `Citation.5`
- `Unnamed: 32`, `Unnamed: 33` may contain additional citation data

---

## 4. Sheet Mapping and Data Model

### 4.1 Relationship Model

- `Indicators.id` (primary key)
- `Methods.id` (foreign key)

Relationship type:
- One indicator → zero or many methods

### 4.2 Authoritative Sources

- Indicator definition, classification, principles, and category flags: **Indicators sheet**
- Measurement procedures, cost/accuracy/ease trade-offs, citations: **Methods sheet**

---

## 5. RAG Chunking and Document Strategy

### 5.1 Indicator Documents (Required)

Create **one document per indicator**.

- **Document ID:** `indicator:{id}`
- **Text content:**
  - Component
  - Class
  - Indicator description
  - Unit
  - Applicable measurement categories
  - Principles and criteria coverage
  - Totals
- **Metadata:**
  - `id`
  - `component`
  - `class`
  - `unit`
  - boolean or list flags for categories and principles

Purpose:
- Queries about *what* an indicator represents
- Filtering by principle, category, or component

### 5.2 Methods Documents (Two Valid Approaches)

#### Option A - Grouped by Indicator (Recommended Default)

- **Document ID:** `methods_for_indicator:{id}`
- **Text content:** all methods for the indicator, structured as a list
- **Metadata:** `id`

Best for:
- "How can indicator X be measured?"
- Full method comparison in one retrieval

#### Option B - One Document per Method Row

- **Document ID:** `method:{id}:{row_index}`
- **Text content:** single method entry
- **Metadata:**
  - `id`
  - `method_general`
  - `accuracy_level`
  - `ease_level`
  - `cost_level`

Best for:
- Constraint-based queries (low cost, high accuracy, easy to use)

#### Recommended Practice

If storage permits, **store both** grouped and per-method documents.

---

## 6. Normalisation and Edge Cases

- Treat `x` and `(x)` as equivalent boolean true
- Preserve raw value if distinction is later needed
- Handle `Unnamed: 32` and `Unnamed: 33` as optional citation spillover
- Expect missing methods for `id = 105`

---

## 7. Minimal Join Contract for Retrieval

Every document derived from either sheet should include:

- `id`
- `indicator` (text)
- `unit`

This guarantees deterministic cross-sheet retrieval and synthesis during answer generation.

---

## 8. Intended Usage

This document is intended to be:
- Embedded directly into an IDE or project docs
- Used as grounding context for an AI agent
- Treated as the authoritative schema and ingestion reference

No business logic, scoring rules, or interpretations beyond the source data are implied.
