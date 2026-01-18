# ADR-006: Deferred Features Summary

## Status
**Living Document** - Updated as features are deferred or implemented

## Context

During the Phase 1-6 remediation work following the code review (2026-01-18), several features were explicitly deferred. This ADR consolidates all deferred items for project planning and future reference.

## Deferred Features by Category

### Memory & State Management

| Feature | Priority | ADR | Review Trigger |
|---------|----------|-----|----------------|
| Long-term memory (cross-session) | P1-004 | ADR-003 | Production deployment, user retention goals |
| Conversation summarization | P2-012 | ADR-003 | Context overflow issues, long conversations |
| Selective context retrieval | P2-015 | ADR-003 | 64K+ token models, Strands support |
| Conversation-scoped tool caching | P2-024 | ADR-004 | Performance metrics show need |

### Observability & Monitoring

| Feature | Priority | ADR | Review Trigger |
|---------|----------|-----|----------------|
| Distributed tracing (spans) | P2-025 | ADR-002 | Production deployment, microservices |
| APM integration | P2-025 | ADR-002 | Enterprise requirements |
| Real-time alerting | P2-025 | ADR-002 | SLA requirements |

### Architecture & Reliability

| Feature | Priority | ADR | Review Trigger |
|---------|----------|-----|----------------|
| Self-correction mechanism | P1-006 | ADR-005 | Production use, autonomous workflows |
| Async embedding support | P1-007 | ADR-001 | High concurrency requirements |
| Embedding dimension negotiation | P2-009 | ADR-001 | Multi-model support needs |

### Performance & Scaling

| Feature | Priority | ADR | Review Trigger |
|---------|----------|-----|----------------|
| Async HTTP calls | P3-002 | N/A | Concurrency bottlenecks identified |
| Connection pooling for external APIs | P3-004 | N/A | High request volume |
| Batch API calls | P3-005 | N/A | Bulk data operations |

### Security & Compliance

| Feature | Priority | ADR | Review Trigger |
|---------|----------|-----|----------------|
| Rate limiting per user | P3-017 | N/A | Multi-user deployment |
| Audit log retention policy | P3-019 | N/A | Compliance requirements |
| PII detection in logs | P3-020 | N/A | GDPR/privacy requirements |

## Implementation Status

### Implemented in Phases 1-5

| Feature | Implementation | Tests |
|---------|---------------|-------|
| ChromaDB connection pooling | TASK101 | ✅ |
| Knowledge versioning metadata | TASK102 | ✅ |
| Basic metrics collection | TASK104 | ✅ |
| Audit logging module | TASK105 | ✅ |
| Structured JSON logging | TASK106 | ✅ |
| Token-budget conversation manager | TASK108 | ✅ |
| Input sanitization | TASK110 | ✅ |
| PDF context sanitization | TASK111 | ✅ |
| API response caching (TTL) | TASK112 | ✅ |
| Tool output truncation | TASK113 | ✅ |

### Documented in ADRs

| ADR | Title | Features Covered |
|-----|-------|------------------|
| ADR-001 | Synchronous Embedding Design | P1-007, P2-009 |
| ADR-002 | Observability Strategy | P2-025 (tracing) |
| ADR-003 | Memory Architecture | P1-004, P2-012, P2-015 |
| ADR-004 | Conversation Caching Deferral | P2-024 |
| ADR-005 | Self-Correction Deferral | P1-006 |
| ADR-006 | Deferred Features Summary | All |

## Prioritization Guidelines

### When to Implement Deferred Features

**High Priority Triggers:**
1. Production deployment planned
2. Enterprise customer requirements
3. Compliance/regulatory mandates
4. Security vulnerabilities identified

**Medium Priority Triggers:**
1. Performance metrics show bottlenecks
2. User feedback indicates need
3. Strands framework adds support
4. Community best practices emerge

**Low Priority / Future Consideration:**
1. Nice-to-have improvements
2. Optimization opportunities
3. Research/exploration items

## Review Schedule

- **Quarterly Review**: Assess deferred features against current needs
- **Release Planning**: Include deferred features in roadmap discussions
- **Incident Response**: Re-evaluate after any production issues
- **Framework Updates**: Check when Strands releases new features

## Consequences

### Positive
- Clear documentation of project scope boundaries
- Explicit rationale for deferrals
- Structured approach to future planning
- Avoids feature creep

### Negative
- Some advanced capabilities unavailable
- May need revisiting as requirements evolve
- Technical debt of documentation maintenance

## References

- Code Review: `docs/development/code-reviews/agentic_ai_code_review_report-2026-01-18-v1.md`
- Phase 1-6 Remediation: `memory-bank/tasks/_index.md`
- Individual ADRs: `docs/adr/`
