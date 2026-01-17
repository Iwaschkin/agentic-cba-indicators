# [TASK034] - Organize Imports

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-18
**Priority:** P3 - Low
**Phase:** 9

## Original Request
Address P3-06: Import ordering not consistent with PEP 8 (stdlib, third-party, local).

## Thought Process
Imports should follow PEP 8 ordering:
1. Standard library imports
2. Third-party imports
3. Local application imports

With blank lines between each group. Some files don't follow this consistently.

Solution: Use ruff or isort to automatically organize imports.

## Implementation Plan
- [x] Configure isort/ruff for import sorting
- [x] Run import sorting on all files
- [x] Verify no broken imports
- [x] Add to CI/pre-commit hooks

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 34.1 | Configure import sorting | Complete | 2025-01-18 | Already configured in pyproject.toml |
| 34.2 | Sort all imports | Complete | 2025-01-18 | Fixed 2 files |
| 34.3 | Verify no breakage | Complete | 2025-01-18 | Tests pass: 35/35 |
| 34.4 | Add to pre-commit | Complete | 2025-01-18 | ruff "I" rules already enabled |

## Progress Log
### 2025-01-17
- Task created from code review finding P3-06
- Assigned to Phase 9 (Code Cleanup)

### 2025-01-18
- Checked pyproject.toml - ruff already has isort configured:
  - `select = ["I"]` enables isort rules
  - `known-first-party = ["agentic_cba_indicators"]` for proper grouping
- Ran `ruff check --select I` - found 2 files with issues:
  - scripts/ingest_excel.py: Import block un-sorted
  - src/agentic_cba_indicators/tools/knowledge_base.py: Import block un-sorted
- Ran `ruff check --select I --fix` - auto-fixed both files
- Verified: `ruff check --select I` - All checks passed
- Tests pass: 35/35

## Acceptance Criteria
- [x] All imports follow PEP 8 ordering
- [x] ruff/isort configured
- [x] Tests pass

## Implementation Notes
- ruff isort was already configured in pyproject.toml with:
  - `select = ["I"]` in `[tool.ruff.lint]`
  - `known-first-party = ["agentic_cba_indicators"]` in `[tool.ruff.lint.isort]`
- Only 2 files needed fixing out of all source files
- Auto-fix maintained by running `ruff check --fix` or including in CI
