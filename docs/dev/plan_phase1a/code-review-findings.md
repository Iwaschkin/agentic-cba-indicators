# Code Review Findings (Phase 1a)

Scope: Full repository review for architecture, security, reliability, robustness, maintainability, data integrity, and operational safety using SEI CERT, OWASP, Google Eng Practices, NASA SWE, ISO 25010, STRIDE, and LINDDUN guidance.

## P0: Critical issues

No P0 issues identified in the current codebase.

## P1: High priority issues

### Bundled config loader references a non-existent package
- **Problem**: `load_config()` attempts to read bundled providers config via `importlib.resources.files("strands_cli.config")`, which does not match the actual package name (`agentic_cba_indicators`). This causes the CLI to fail when no user config is present.
- **Why it matters**: Default configuration fails in the common “first run” path, preventing the CLI from starting without a user-supplied config file.
- **Fix / Recommendation**: Update the resource lookup to `importlib.resources.files("agentic_cba_indicators.config")` (or `agentic_cba_indicators/config/providers.yaml`) and add a test that exercises the bundled fallback path.
- **Affected**: src/agentic_cba_indicators/config/provider_factory.py

### Network calls without timeouts or retry/format handling in multiple tools
- **Problem**: Several tools (e.g., weather, climate, socioeconomic) call `httpx.Client()` without explicit timeouts or standardized retry/format handling. This diverges from the shared `_http.py` utilities and can hang indefinitely or crash on malformed responses.
- **Why it matters**: External APIs are unreliable. A single blocked call can freeze the CLI or cause inconsistent failures. This is a reliability and availability risk (STRIDE: DoS).
- **Fix / Recommendation**: Standardize on `_http.fetch_json()` for all external API calls, or enforce explicit timeouts + error handling + retries; add response validation before use.
- **Affected**: src/agentic_cba_indicators/tools/weather.py, src/agentic_cba_indicators/tools/climate.py, src/agentic_cba_indicators/tools/socioeconomic.py, src/agentic_cba_indicators/tools/_geo.py

## P2: Medium priority issues

### Silent embedding failures can corrupt knowledge base quality
- **Problem**: In ingestion scripts, embedding failures are handled by inserting zero-vectors without failing or marking documents as invalid. This silently degrades search quality and can poison relevance results.
- **Why it matters**: Data integrity and retrieval quality are core to the RAG workflow. Silent failures make it difficult to detect corrupted embeddings and can produce misleading outputs.
- **Fix / Recommendation**: Fail-fast or mark failed embeddings with metadata and skip upsert; emit explicit warnings and a summary of failures; optionally allow `--strict` mode to abort on any embedding failure.
- **Affected**: scripts/ingest_excel.py, scripts/ingest_usecases.py

### Unbounded in-memory geocode cache
- **Problem**: `_geo.py` caches geocoding results in a global dict without a size limit or TTL. Long CLI sessions or scripted usage can grow memory without bound.
- **Why it matters**: Memory growth affects reliability and can cause CLI instability on long-running sessions or when used as a tool backend.
- **Fix / Recommendation**: Add a bounded cache (e.g., `functools.lru_cache` or a size-limited dict) with a TTL policy; provide a configurable max size.
- **Affected**: src/agentic_cba_indicators/tools/_geo.py

### Lack of schema validation for config files
- **Problem**: YAML config is parsed and expanded, but there is no schema validation or explicit checks for required fields. Missing or malformed fields can lead to runtime errors later during model construction.
- **Why it matters**: Error feedback is delayed and unclear, reducing robustness and increasing support burden.
- **Fix / Recommendation**: Add explicit validation with clear error messages (e.g., `pydantic` or a lightweight manual schema check) and tests for malformed config structures.
- **Affected**: src/agentic_cba_indicators/config/provider_factory.py

### Incomplete resilience for external API rate limits
- **Problem**: `_http.fetch_json()` implements basic retry logic, but some tools bypass it; additionally, retries are unconditional and do not account for per-service quotas or jitter.
- **Why it matters**: In high-frequency usage (e.g., agent tool chains), this can amplify rate limiting and degrade overall experience.
- **Fix / Recommendation**: Apply `_http.fetch_json()` consistently and add jittered backoff with an upper bound; consider a simple per-service rate limiter to prevent tool storms.
- **Affected**: src/agentic_cba_indicators/tools/_http.py and tool modules that bypass it

### Minimal test coverage for tools and ingestion workflows
- **Problem**: Tests focus on config and paths; the core tool modules and ingestion scripts have no automated coverage.
- **Why it matters**: Changes to APIs or logic can break functionality without detection, harming reliability and maintainability.
- **Fix / Recommendation**: Add tests for representative tool calls (with mocked HTTP), ingestion parsing, and embedding error handling; include regression tests for known edge cases.
- **Affected**: tests/ (coverage gaps across tools and scripts)

## P3: Low priority issues

### Duplicate geocoding logic across modules
- **Problem**: Weather and climate tools implement their own geocoding instead of reusing `_geo.geocode_city()`.
- **Why it matters**: Duplicated logic increases maintenance cost and inconsistent behavior.
- **Fix / Recommendation**: Centralize geocoding through `_geo.py` and remove duplicate implementations.
- **Affected**: src/agentic_cba_indicators/tools/weather.py, src/agentic_cba_indicators/tools/climate.py

### Country/indicator code maps duplicated in multiple modules
- **Problem**: Country code mappings appear in multiple tools with partial overlaps and different normalization behaviors.
- **Why it matters**: Inconsistent mappings lead to confusing behavior and harder maintenance.
- **Fix / Recommendation**: Centralize common lookup tables and normalization functions in a shared module.
- **Affected**: src/agentic_cba_indicators/tools/socioeconomic.py, src/agentic_cba_indicators/tools/sdg.py, src/agentic_cba_indicators/tools/agriculture.py

### Runtime dependencies include tooling packages
- **Problem**: `pyright` is listed under runtime dependencies rather than dev/test dependencies.
- **Why it matters**: Increases install size and supply-chain exposure for end users.
- **Fix / Recommendation**: Move type-checking tooling to `dev` extras only.
- **Affected**: pyproject.toml

## Architecture Notes

- **Tooling integration consistency**: The codebase has a shared `_http` layer but does not consistently use it. This creates uneven reliability and error handling across tools, complicating operational stability. Consolidation would reduce risk and improve maintainability.
- **Config fallback path**: The packaged default config path is critical for first-run UX; its current mismatch signals a fragile configuration boundary. This should be corrected and covered by tests.
- **Data pipeline integrity**: Ingestion scripts should make integrity guarantees explicit (e.g., strict vs. best-effort embedding). A clear policy is needed to avoid silent quality degradation in the knowledge base.
