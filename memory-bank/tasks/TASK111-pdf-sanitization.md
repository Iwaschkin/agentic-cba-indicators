# [TASK111] - PDF Context Sanitization

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18
**Completed:** 2026-01-18
**Phase:** 4 - Security Hardening
**Priority:** P1
**Issue ID:** P2-029

## Original Request
Apply sanitization to PDF text extraction to prevent context injection attacks.

## Thought Process
PDF uploads could contain adversarial instructions that manipulate the agent. Need to:
- Apply same sanitization as user input
- Add specific length limit for PDF context
- Show warning if truncated

## Implementation Plan
1. Add MAX_PDF_CONTEXT_LENGTH = 50000 to security.py
2. Apply sanitize_user_input() to extracted PDF text in ui.py
3. Add truncation warning in UI
4. Add unit test

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 11.1 | Add MAX_PDF_CONTEXT_LENGTH constant | Complete | 2026-01-18 | 50000 characters |
| 11.2 | Apply sanitization in ui.py | Complete | 2026-01-18 | sanitize_pdf_context() |
| 11.3 | Add truncation warning | Complete | 2026-01-18 | st.sidebar.warning() |
| 11.4 | Add unit test | Complete | 2026-01-18 | 8 tests in test_security.py |

## Progress Log
### 2026-01-18
- Task created from code review finding P2-029

### 2026-01-18 (Implementation)
- Added `MAX_PDF_CONTEXT_LENGTH = 50000` to security.py
- Created `sanitize_pdf_context()` function:
  - Returns tuple (sanitized_text, was_truncated)
  - Applies same sanitization as user input
  - Larger default max_length for documents
  - Logs when truncation occurs
- Updated ui.py PDF upload handler:
  - Import sanitize_pdf_context
  - Sanitize PDF text after extraction
  - Show truncation warning if applicable
- Added 8 tests for PDF sanitization in TestSanitizePdfContext class
- All 408 tests pass (400 previous + 8 new)

## Files Changed
- `src/agentic_cba_indicators/security.py` (modified - new constant and function)
- `src/agentic_cba_indicators/ui.py` (modified - apply sanitization)
- `tests/test_security.py` (modified - 8 new PDF tests)

## Definition of Done
- [x] PDF text sanitized and truncated
- [x] Warning shown when truncated
- [x] Test verifies sanitization
