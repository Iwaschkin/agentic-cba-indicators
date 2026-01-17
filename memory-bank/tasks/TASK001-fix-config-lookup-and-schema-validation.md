# TASK001 - Fix bundled config lookup + schema validation

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Fix bundled config lookup mismatch and add schema validation for configuration files.

## Thought Process
Bundled config lookup must succeed for first-run UX. Schema validation ensures early, clear failures and prevents runtime errors in model creation.

## Implementation Plan
- Correct importlib.resources lookup to agentic_cba_indicators.config
- Add schema validation with explicit error messages
- Add tests for bundled fallback and malformed configs

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Fix bundled config lookup path | Complete | 2026-01-17 | Updated importlib.resources path |
| 1.2 | Add config schema validation | Complete | 2026-01-17 | Added validation for required fields |
| 1.3 | Add tests for fallback and invalid configs | Complete | 2026-01-17 | Added tests in test_config.py |

## Progress Log
### 2026-01-17
- Task created
- Fixed bundled config lookup to agentic_cba_indicators.config
- Added config schema validation and clearer error handling
- Added tests for bundled fallback and invalid config structure
