# [TASK071] - Add PDF links to export_indicator_selection()

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Include Open Access PDF links and badges in markdown export output.

## Thought Process
- export_indicator_selection() generates markdown reports
- Users want to access OA PDFs directly from exports
- Show 🔓 badge for OA citations
- Include clickable [PDF](url) links
- Enhance value of exported reports

## Implementation Plan
1. Check citation.is_oa when displaying citations
2. Add 🔓 badge for OA citations
3. Add [PDF](citation.pdf_url) link if pdf_url present
4. Test markdown rendering

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 71.1 | Locate citation display in export | Complete | 2026-01-18 | Found References section in export |
| 71.2 | Add OA badge logic | Complete | 2026-01-18 | 🔓 badge added for OA citations |
| 71.3 | Add PDF link logic | Complete | 2026-01-18 | PDF links included when available |
| 71.4 | Test export with OA citations | Complete | 2026-01-18 | Markdown rendering verified |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
- Added OA badges and PDF links to exports
