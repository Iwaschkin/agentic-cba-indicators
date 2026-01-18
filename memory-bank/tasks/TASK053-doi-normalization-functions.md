# [TASK053] - DOI Normalization Functions

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Implement core DOI parsing and validation functions following DOI Handbook (ISO 26324) spec.

## Mapped Issues
- CN-05: Add `DOI_PATTERN` regex matching DOI Handbook spec
- CN-06: Implement `normalize_doi(raw)` function
- CN-07: Implement `extract_doi_from_text(text)` function
- CN-08: Implement `clean_citation_text(text)` function
- CN-09: Implement `doi_to_url(doi)` function

## Implementation Plan
1. Add `DOI_PATTERN` regex after imports in ingest_excel.py
2. Add `normalize_doi()` - strip prefixes, validate format, lowercase
3. Add `extract_doi_from_text()` - find DOI in citation text
4. Add `clean_citation_text()` - remove DOI patterns from text
5. Add `doi_to_url()` - generate https://doi.org/{doi}

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 53.1 | Add DOI_PATTERN regex | Complete | 2026-01-17 | Matches 10.XXXX+/suffix per DOI Handbook |
| 53.2 | Implement normalize_doi() | Complete | 2026-01-17 | Handles URL, prefix variants |
| 53.3 | Implement extract_doi_from_text() | Complete | 2026-01-17 | Finds embedded DOIs |
| 53.4 | Implement clean_citation_text() | Complete | 2026-01-17 | Removes DOI, cleans whitespace |
| 53.5 | Implement doi_to_url() | Complete | 2026-01-17 | Generates canonical HTTPS URLs |

## Progress Log
### 2026-01-17
- Task created from citation normalization strategy
- Part of Phase 1 implementation
- Implemented all 5 functions in scripts/ingest_excel.py
- All functions tested via test_citation_normalization.py

## Definition of Done
- [ ] DOI_PATTERN regex compiles and matches valid DOIs
- [ ] normalize_doi() handles all format variants
- [ ] extract_doi_from_text() finds embedded DOIs
- [ ] clean_citation_text() removes DOI patterns cleanly
- [ ] doi_to_url() returns canonical HTTPS URL
- [ ] All functions have docstrings
