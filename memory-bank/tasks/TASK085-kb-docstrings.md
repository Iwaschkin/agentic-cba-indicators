# [TASK085] - Add Docstrings to KB Internal Helpers

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Add complete docstrings to _get_chroma_client() and _resolve_indicator_id() internal functions.

## Mapped Issue
- **Issue ID:** P3-2
- **Priority:** P3 (Low)
- **Phase:** 3

## Resolution
1. `_get_chroma_client()` - Already had complete Google-style docstring with Returns and Raises ✅
2. `_resolve_indicator_id()` - Enhanced docstring with:
   - Full description of behavior
   - Args section for the indicator parameter
   - Detailed Returns section explaining tuple format
   - Note about similarity threshold constant
