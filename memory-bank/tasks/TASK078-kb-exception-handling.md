# [TASK078] - Narrow Exception Handling in knowledge_base.py

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Replace broad `except Exception as e:` patterns with specific exception handling in knowledge_base.py to allow programming errors to propagate.

## Mapped Issue
- **Issue ID:** P1-1 (partial)
- **Priority:** P1 (High)
- **Phase:** 1

## Implementation Plan
1. Identify all `except Exception` blocks in knowledge_base.py (~15 occurrences)
2. Replace with `except (ChromaDBError,)` or appropriate specific exceptions
3. Add `logger.warning()` calls with `exc_info=True` for debugging
4. Verify tests still pass
5. Add test that confirms unexpected exceptions propagate

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Audit all except blocks | Not Started | | |
| 1.2 | Update search_indicators | Not Started | | |
| 1.3 | Update search_methods | Not Started | | |
| 1.4 | Update get_indicator_details | Not Started | | |
| 1.5 | Update remaining KB tools | Not Started | | |
| 1.6 | Add logging imports | Not Started | | |
| 1.7 | Run tests | Not Started | | |

## Progress Log

## Definition of Done
- All 15+ catch blocks use specific exceptions (ChromaDBError)
- logger.warning added with exc_info=True
- All 212+ tests pass
- Unexpected exceptions (AttributeError, TypeError) propagate
