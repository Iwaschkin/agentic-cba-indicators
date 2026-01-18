# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant technical decisions made during the development of the Agentic CBA Indicators project.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-synchronous-embedding-design.md) | Synchronous Embedding Design | Accepted | 2026-01-18 |
| [ADR-002](ADR-002-observability-strategy.md) | Observability Strategy and Tracing Deferral | Accepted | 2026-01-18 |
| [ADR-003](ADR-003-memory-architecture.md) | Memory Architecture and Limitations | Accepted | 2026-01-18 |
| [ADR-004](ADR-004-conversation-caching-deferral.md) | Conversation-Scoped Tool Result Caching (Deferred) | Deferred | 2026-01-18 |
| [ADR-005](ADR-005-self-correction-deferral.md) | Self-Correction and Validation Mechanisms (Deferred) | Deferred | 2026-01-18 |
| [ADR-006](ADR-006-deferred-features-summary.md) | Deferred Features Summary | Living | 2026-01-18 |

## ADR Status Definitions

- **Proposed**: Decision under consideration
- **Accepted**: Decision approved and in effect
- **Deprecated**: Decision no longer applies
- **Superseded**: Replaced by a newer ADR

## Template

When creating a new ADR, use this template:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Date:** YYYY-MM-DD
**Context:** Brief context

## Context
What is the issue or decision that needs to be made?

## Decision
What is the decision that was made?

## Consequences
What are the positive and negative consequences?

## Alternatives Considered
What other options were evaluated?
```

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Michael Nygard's ADR Article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
