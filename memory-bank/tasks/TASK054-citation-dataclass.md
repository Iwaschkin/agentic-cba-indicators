# [TASK054] - Citation Dataclass

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Create structured Citation dataclass with factory method and formatting methods.

## Mapped Issues
- CN-01: Create `Citation` dataclass with `raw_text`, `text`, `doi`, `url` fields
- CN-02: Implement `Citation.from_raw()` classmethod
- CN-03: Implement `Citation.to_embed_string()` for embeddings
- CN-04: Implement `Citation.to_display_string()` for user output

## Implementation Plan
1. Add Citation dataclass after CRITERIA_COLUMNS
2. Implement from_raw() using normalize_doi(), extract_doi_from_text()
3. Implement to_embed_string() returning text only
4. Implement to_display_string() including URL when available

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 54.1 | Create Citation dataclass | Complete | 2026-01-17 | Fields: raw_text, text, doi, url |
| 54.2 | Implement from_raw() | Complete | 2026-01-17 | Parses and normalizes DOI |
| 54.3 | Implement to_embed_string() | Complete | 2026-01-17 | Returns text only |
| 54.4 | Implement to_display_string() | Complete | 2026-01-17 | Includes URL when available |

## Progress Log
### 2026-01-17
- Task created from citation normalization strategy
- Depends on TASK053 (DOI functions)
- Implemented Citation dataclass with all methods
- Tested via test_citation_normalization.py (13 tests)

## Definition of Done
- [ ] Citation dataclass with all fields
- [ ] from_raw() normalizes DOI and generates URL
- [ ] to_embed_string() returns text without DOI/URL
- [ ] to_display_string() includes clickable URL
