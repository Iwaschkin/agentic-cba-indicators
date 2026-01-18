# [TASK071] - Add PDF links to export_indicator_selection()

**Status:** Not Started
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

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 71.1 | Locate citation display in export | Not Started | - | Find where citations are formatted |
| 71.2 | Add OA badge logic | Not Started | - | 🔓 for is_oa=True |
| 71.3 | Add PDF link logic | Not Started | - | [PDF](url) if pdf_url present |
| 71.4 | Test export with OA citations | Not Started | - | Validate markdown rendering |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
