# TASK125 - Audit Tool Context Discovery Logic

**Status:** Completed
**Priority:** P3
**Phase:** 5 - Help Tool Refinement
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue ATI-003: The `_get_tools_from_context()` function's runtime introspection is fragile and undocumented.

## Thought Process

Current implementation walks call stack and inspects locals to find tools:
```python
def _get_tools_from_context() -> list[Any] | None:
    for frame_info in inspect.stack():
        frame_locals = frame_info.frame.f_locals
        for var_name, var_value in frame_locals.items():
            if var_name == "tools" and isinstance(var_value, list):
                return var_value
    return None
```

Issues:
1. Relies on specific variable naming ("tools")
2. No documentation of expected call context
3. Silent failure makes debugging hard (addressed in TASK117)
4. Could break with strands-agents version updates

This task audits and documents the approach, potentially proposing alternatives.

## Implementation Plan

- [x] 5.1 Document current behavior in docstring
- [x] 5.2 Add unit tests for expected call contexts
- [x] 5.3 Research strands-agents API for official tool access
- [x] 5.4 If alternative exists: propose migration
- [x] 5.5 If not: document fragility in known-limitations

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 5.1 | Document in docstring | Complete | 2026-01-19 | Added notes in _help.py |
| 5.2 | Add unit tests | Complete | 2026-01-19 | Added tool_registry path test |
| 5.3 | Research strands API | Complete | 2026-01-19 | No public tool registry API found |
| 5.4 | Propose alternative | Not Applicable | 2026-01-19 | Continue with fallback registry |
| 5.5 | Document if no alternative | Complete | 2026-01-19 | Added to known-limitations (P3-024) |

## Acceptance Criteria

- [x] Function docstring explains mechanism
- [x] Tests verify expected behavior
- [x] Decision documented (migrate or accept)

## Definition of Done

- Documentation complete
- Tests added
- Decision recorded in code or known-limitations

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue ATI-003
- Depends on TASK117 for debug logging
### 2026-01-19
- Documented tool context introspection behavior in _help.py.
- Added tests covering tool_registry path.
- Added limitation entry in known-limitations.
