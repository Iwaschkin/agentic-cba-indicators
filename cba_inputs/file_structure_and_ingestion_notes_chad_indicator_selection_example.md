# File structure and ingestion notes - Chad indicator selection example

## Purpose
This document describes **only** the structure and parsing rules for the example workbook:

- `Indicators for Use Case Regenerative Cotton in Chad.xlsx`
- Path: `/mnt/data/Indicators for Use Case Regenerative Cotton in Chad.xlsx`

This file is a **use-case selection list**. It does not contain full indicator definitions or measurement methods. It describes which indicators were selected for the Chad project, grouped by outcome.

Use this document as the ingestion contract for your IDE or pipeline.

---

## Workbook layout

### Sheets
- `Suggested indicators`

There is only one relevant sheet.

### Shape
- 13 rows (outcome rows)
- 4 columns

Each row represents one outcome and its associated indicators.

---

## Column schema and meaning

### 1) `Outcome id`
- Type: string
- Example values: `1.1`, `2.3`
- Role: unique outcome key within this file

Parsing rules:
- Treat as string, do not convert to float.
- Preserve formatting exactly.

### 2) `Outcome`
- Type: free text
- Role: the outcome statement

Parsing rules:
- Keep text as-is.
- Trim leading and trailing whitespace.

### 3) `Indicators (selected from CBA ME Indicators List)`
- Type: delimited list in a single cell
- Delimiter: semicolon `;`
- Role: indicator names that are intended to come from the master indicator library

Parsing rules:
- Split on `;`
- Trim whitespace on each item
- Drop empty items

Important:
- These values are **names**, not ids.
- They should be resolved to the master library (for example `CBA ME Indicators List.xlsx`) if you want canonical ids and full definitions.

### 4) `Extra indicators`
- Type: optional free text or delimited list
- Often semicolon-separated
- Role: indicators used in the project that are not present in the master library

Parsing rules:
- If semicolons are present, apply the same split/trim/drop logic.
- If not, treat the whole cell as a single entry.

---

## Normalisation rules
Apply these minimal normalisations to improve matching and consistency.

### Text normalisation
- Trim leading and trailing whitespace
- Collapse repeated internal spaces to a single space

Do not:
- Rewrite terms
- Translate
- Expand abbreviations

### Empty cells
- Treat empty/NaN as:
  - Empty list for list columns
  - Empty string for the outcome statement

---

## Canonical parsed record format
Your ingestion should convert each row into a normalised record like:

```json
{
  "use_case": "regen_cotton_chad",
  "country": "Chad",
  "outcome_id": "1.1",
  "outcome": "<free text>",
  "selected_indicator_names": ["<name>", "<name>"] ,
  "extra_indicator_names": ["<name>"]
}
```

Optionally, if you have already ingested the master library, enrich with:

```json
{
  "selected_indicator_ids": [123, 124],
  "unresolved_indicator_names": ["<name>"]
}
```

---

## Recommended RAG documents to create
Because this file is small and highly structured, the best approach is to create documents that match typical questions.

### Document A: one outcome document per row (recommended)
- Doc id: `usecase:regen_cotton_chad:outcome:{outcome_id}`
- Text: key-value block containing outcome statement plus the indicator lists
- Metadata:
  - `use_case`, `country`, `outcome_id`
  - `selected_indicator_names` (list)
  - `extra_indicator_names` (list)
  - Optional: `selected_indicator_ids` (list)

This supports:
- "What are the outcomes?"
- "Which indicators were selected for outcome 2.1?"

### Document B: indicator-to-outcome link docs (optional but useful)
Create one document per (outcome_id, indicator_name or indicator_id).
- Doc id: `usecase:regen_cotton_chad:link:{outcome_id}:{indicator_key}`
- Metadata:
  - `outcome_id`
  - `indicator_name`
  - Optional: `indicator_id`

This supports:
- "Which outcomes mention indicator X?"

### Document C: extra indicator docs (optional)
If extra indicators are important to search, store each as a small document.

---

## Linking to the master indicator library (optional enrichment)
This file references the master list by name. If the master workbook is available in your system:

1. Attempt exact match of `selected_indicator_names` to master `Indicators.Indicator`.
2. If exact match fails, attempt simple normalised match (trim + single spaces).
3. If still fails, optionally do fuzzy match and store a confidence score.

Keep unresolved names so the system can be honest and generate a review report.

---

## Quality checks (recommended)
1. Confirm `Suggested indicators` sheet exists.
2. Confirm required columns exist exactly:
   - `Outcome id`
   - `Outcome`
   - `Indicators (selected from CBA ME Indicators List)`
   - `Extra indicators`
3. Validate uniqueness of `Outcome id`.
4. Validate that each row has at least one selected indicator name.
5. If doing enrichment: report match coverage (resolved vs unresolved).

---

## Summary
This workbook is a **selection mapping**:
- Outcome id + outcome statement
- Names of selected indicators from the master library
- Optional extra indicators not present in the master library

Ingest by parsing semicolon-separated lists, preserving outcome ids as strings, and emitting one outcome document per row (plus optional link docs).
