# [TASK087] - Document Thread-Safety Constraint

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Document that the geocode cache is not thread-safe and the module assumes single-threaded operation.

## Mapped Issue
- **Issue ID:** P2-1
- **Priority:** P2 (Medium)
- **Phase:** 4

## Resolution
Added "Thread Safety" section to _geo.py module docstring that:
1. Notes the cache is NOT thread-safe
2. States the module assumes single-threaded operation (default for Strands)
3. Provides guidance for future async/concurrent usage:
   - threading.Lock option
   - cachetools.LRUCache + lock option
   - functools.lru_cache option
