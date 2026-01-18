# ADR-002: Observability Strategy and Tracing Deferral

**Status:** Accepted
**Date:** 2026-01-18
**Deciders:** Development team
**Category:** Observability

## Context

The code review identified that the application lacks distributed tracing integration (Issue P2-025). Distributed tracing with OpenTelemetry would provide:
- Request correlation across tool calls
- Timing breakdown for each processing step
- Integration with observability platforms (Jaeger, Zipkin, Datadog)
- Standardized span/trace context propagation

However, implementing full OpenTelemetry/OTLP integration adds complexity:
- New dependency (`opentelemetry-sdk`, `opentelemetry-instrumentation`)
- Infrastructure requirements (collector, storage backend)
- Configuration complexity for exporters
- Potential performance overhead from instrumentation

## Decision

**Defer distributed tracing implementation.** Instead, implement a lightweight observability layer using standard Python logging and custom metrics:

1. **Structured JSON Logging** (`logging_config.py`)
   - Optional JSON Lines output format via `AGENTIC_CBA_LOG_FORMAT=json`
   - Standard fields: timestamp, level, logger, message
   - Extra fields for structured context
   - Compatible with log aggregation systems (ELK, CloudWatch)

2. **Metrics Collection** (`observability.py`)
   - Tool call counters (success/failure by tool name)
   - Latency histograms with percentiles (p50, p95, p99)
   - Thread-safe implementation
   - Bounded memory usage (10,000 samples max)

3. **Audit Logging** (`audit.py`)
   - JSON Lines file-based audit trail
   - Parameter sanitization (redacts API keys, passwords, tokens)
   - Result truncation to prevent log bloat
   - Configurable via `AGENTIC_CBA_AUDIT_LOG` environment variable

## Rationale

### Single-Service Architecture
The application is a CLI chatbot with a single process. There are no distributed service calls to trace across network boundaries. The value proposition of distributed tracing is significantly reduced in this context.

### Sufficient Observability for Current Scale
The combination of JSON logging, metrics, and audit logging provides adequate observability:
- **Debugging**: Structured logs with context enable root cause analysis
- **Performance**: Latency histograms identify slow tools
- **Security**: Audit logs track all tool invocations
- **Monitoring**: Metrics can be exposed for Prometheus scraping

### Dependency Philosophy
The project prioritizes minimal dependencies. OpenTelemetry would add:
- `opentelemetry-api` (~500KB)
- `opentelemetry-sdk` (~1MB)
- `opentelemetry-instrumentation-*` (per-library)
- Optional exporters

### Infrastructure Requirements
Full tracing requires:
- Collector deployment (or direct exporter configuration)
- Backend storage (Jaeger, Tempo, commercial APM)
- Configuration management for endpoints and sampling

## Consequences

### Positive
- Simpler architecture with fewer dependencies
- No infrastructure requirements for basic observability
- Faster startup and lower memory footprint
- Clear migration path when tracing becomes necessary

### Negative
- No automatic correlation across async operations
- No waterfall visualization of request timing
- Manual effort required to correlate log entries
- Not compatible with existing APM dashboards

### Neutral
- Log-based debugging is familiar to most developers
- JSON logs can be processed by observability platforms

## Future Migration Path

When distributed tracing becomes necessary (see review triggers below), the migration path is:

1. **Add OpenTelemetry dependency:**
   ```bash
   uv add 'opentelemetry-api' 'opentelemetry-sdk'
   uv add 'opentelemetry-exporter-otlp'  # or jaeger, zipkin, etc.
   ```

2. **Initialize tracer in CLI:**
   ```python
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

   trace.set_tracer_provider(TracerProvider())
   tracer = trace.get_tracer(__name__)

   processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
   trace.get_tracer_provider().add_span_processor(processor)
   ```

3. **Instrument tools with spans:**
   ```python
   @tool
   def my_tool(query: str) -> str:
       with tracer.start_as_current_span("my_tool") as span:
           span.set_attribute("query", query)
           # ... tool logic ...
           span.set_attribute("result_count", len(results))
           return results
   ```

4. **Integrate with @instrument_tool decorator:**
   Enhance `observability.py` to optionally create spans when a tracer is configured.

## Review Triggers

Reconsider this decision when ANY of the following occur:

1. **Multi-service deployment**: Application is split into separate services
2. **Async processing**: Background jobs or message queue integration added
3. **Production incidents**: Debugging requires better request correlation
4. **APM mandate**: Organization requires standardized observability
5. **Strands SDK support**: Strands adds native OpenTelemetry instrumentation

## Related Decisions

- [ADR-001: Synchronous Embedding Design](ADR-001-synchronous-embedding-design.md) - Also defers async for simplicity
- TASK104: Metrics collection implementation
- TASK105: Audit logging implementation
- TASK106: JSON logging implementation

## References

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Strands Agents SDK](https://strandsagents.com/) - Check for native instrumentation support
