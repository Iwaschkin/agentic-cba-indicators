# [TASK023] - Extract Magic Numbers to Named Constants

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P2 - Medium
**Phase:** 6

## Original Request
Address P2-05: Magic numbers (retry counts, chunk sizes, sleep durations) scattered throughout code.

## Thought Process
Magic numbers reduce code readability and make tuning difficult. Found in:
- `knowledge_base.py`: Result limits (20, 50, 100), similarity threshold (0.7)
- `biodiversity.py`: Species/occurrence limits (50, 100), radius (200)

Note: Many magic numbers were already addressed:
- Retry counts already configurable via environment variables
- MAX_EMBEDDING_CHARS already extracted in _embedding.py
- MAX_CACHE_SIZE already extracted in _geo.py

Solution: Extract remaining magic numbers to named constants with clear documentation.

## Implementation Plan
- [x] Audit magic numbers in codebase
- [x] Add constants to knowledge_base.py
- [x] Add constants to biodiversity.py
- [x] Update code to use constants
- [x] Verify tests pass

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 23.1 | Audit magic numbers | Complete | 2025-01-17 | Found in knowledge_base.py, biodiversity.py |
| 23.2 | Add constants to knowledge_base.py | Complete | 2025-01-17 | 4 constants added |
| 23.3 | Add constants to biodiversity.py | Complete | 2025-01-17 | 3 constants added |
| 23.4 | Update code to use constants | Complete | 2025-01-17 | All 10 usages updated |
| 23.5 | Verify tests pass | Complete | 2025-01-17 | All 35 tests pass |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-05
- Added to `knowledge_base.py`:
  - `_MAX_SEARCH_RESULTS_DEFAULT = 20` - Standard search functions
  - `_MAX_SEARCH_RESULTS_MEDIUM = 50` - Principle/class browsing
  - `_MAX_SEARCH_RESULTS_LARGE = 100` - Component listing, comparison
  - `_INDICATOR_MATCH_THRESHOLD = 0.7` - Similarity threshold for name matching
- Updated 7 functions to use these constants
- Added to `biodiversity.py`:
  - `_MAX_SPECIES_RESULTS = 50` - Species search limit
  - `_MAX_OCCURRENCE_RESULTS = 100` - Occurrence query limit
  - `_MAX_RADIUS_KM = 200` - Maximum spatial search radius
- Updated 3 functions to use these constants
- All 35 tests passing
- Task complete

## Constants Added

### knowledge_base.py
| Constant | Value | Purpose |
|----------|-------|---------|
| _MAX_SEARCH_RESULTS_DEFAULT | 20 | Standard semantic search functions |
| _MAX_SEARCH_RESULTS_MEDIUM | 50 | Principle/class browsing functions |
| _MAX_SEARCH_RESULTS_LARGE | 100 | Component listing, comparison functions |
| _INDICATOR_MATCH_THRESHOLD | 0.7 | Cosine distance threshold (~65% similarity) |

### biodiversity.py
| Constant | Value | Purpose |
|----------|-------|---------|
| _MAX_SPECIES_RESULTS | 50 | Maximum results for species search |
| _MAX_OCCURRENCE_RESULTS | 100 | Maximum results for occurrence queries |
| _MAX_RADIUS_KM | 200 | Maximum search radius for spatial queries |

## Acceptance Criteria
- [x] No unexplained magic numbers in code
- [x] Constants named meaningfully
- [x] Easy to tune parameters
- [x] Tests pass
