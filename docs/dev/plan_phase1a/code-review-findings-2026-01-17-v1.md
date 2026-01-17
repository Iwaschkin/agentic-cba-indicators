# Code Review Findings

**Date:** 2026-01-17
**Version:** v1
**Reviewer:** Automated Review
**Standards Applied:** SEI CERT, OWASP, Google Engineering Practices, NASA Software Engineering, ISO 25010, STRIDE, LINDDUN, SonarQube/CodeQL patterns

---

## Executive Summary

This review covers the `agentic-cba-indicators` codebase—a CLI chatbot integrating weather, climate, socio-economic, and CBA indicator data using the Strands Agents SDK. The codebase demonstrates solid architectural patterns with centralized HTTP handling, proper configuration management, and a well-structured tool system. However, several issues across security, reliability, and maintainability require attention.

**Issue Counts by Severity:**
- **P0 (Critical):** 3
- **P1 (High):** 8
- **P2 (Medium):** 12
- **P3 (Low):** 7

---

## P0: Critical Issues

### P0-1: API Keys Logged/Exposed in Error Messages

**Problem:** Multiple tools pass raw exception messages to users that may contain API keys or authentication tokens embedded in request URLs or headers.

**Why it matters:** API keys leaked in error messages can be captured in logs, shared in bug reports, or displayed to users, leading to credential compromise and unauthorized API access.

**Affected files:**
- [src/agentic_cba_indicators/tools/commodities.py](../../../src/agentic_cba_indicators/tools/commodities.py#L123)
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L71)

**Fix:** Sanitize all error messages before returning to users. Create a centralized error sanitization function that strips sensitive patterns (URLs with tokens, headers, etc.):

```python
def sanitize_error(error: Exception) -> str:
    """Remove sensitive data from error messages."""
    msg = str(error)
    # Remove URLs with potential tokens
    msg = re.sub(r'https?://[^\s]+', '[URL REDACTED]', msg)
    # Remove Authorization headers
    msg = re.sub(r'Authorization:\s*\S+', 'Authorization: [REDACTED]', msg)
    return msg
```

---

### P0-2: Ollama API Key Passed in Bearer Header Without TLS Verification

**Problem:** In [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L36-L42) and [ingest_excel.py](../../../scripts/ingest_excel.py#L69-L74), the `OLLAMA_API_KEY` is sent as a Bearer token, but there's no enforcement of TLS for the `OLLAMA_HOST` endpoint. Users could configure an HTTP URL, leaking credentials in plaintext.

**Why it matters:** Credential exposure over unencrypted connections enables man-in-the-middle attacks, especially on shared networks.

**Affected files:**
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L36)
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py#L69)
- [scripts/ingest_usecases.py](../../../scripts/ingest_usecases.py#L65)

**Fix:** Validate that `OLLAMA_HOST` uses HTTPS when `OLLAMA_API_KEY` is set:

```python
def _get_ollama_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        if not OLLAMA_HOST.startswith("https://"):
            raise ValueError("OLLAMA_HOST must use HTTPS when API key is configured")
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    return headers
```

---

### P0-3: Unbounded Memory Growth in Geocode Cache

**Problem:** While the geocode cache in [_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L13-L17) has a `MAX_CACHE_SIZE`, the eviction logic only triggers *after* adding new entries. Under concurrent access or rapid requests, the cache can grow unbounded before eviction occurs.

**Why it matters:** Memory exhaustion can cause service denial and process crashes, especially in long-running CLI sessions or when integrated into servers.

**Affected files:**
- [src/agentic_cba_indicators/tools/_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L13)

**Fix:** Use a proper bounded cache with automatic eviction. Replace `OrderedDict` with `functools.lru_cache` or a thread-safe LRU implementation:

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def _cached_geocode(cache_key: str) -> GeoLocation | None:
    # Actual geocoding logic
    ...
```

---

## P1: High Priority Issues

### P1-1: No Input Validation on User-Provided Coordinates

**Problem:** In [_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L115-L124), coordinates from user input are parsed but only validated for basic range. Malformed inputs like `"51.5, , -0.1"` or `"NaN,NaN"` could cause downstream issues.

**Why it matters:** Invalid coordinates passed to external APIs may cause unexpected errors, rate limiting, or incorrect results that undermine data integrity.

**Affected files:**
- [src/agentic_cba_indicators/tools/_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L99)

**Fix:** Add comprehensive coordinate validation:

```python
def geocode_or_parse(location: str) -> tuple[float, float] | None:
    if "," in location:
        try:
            parts = [p.strip() for p in location.split(",")]
            if len(parts) != 2:
                return None
            lat, lon = float(parts[0]), float(parts[1])
            if not (math.isfinite(lat) and math.isfinite(lon)):
                return None
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return None
            return (lat, lon)
        except (ValueError, IndexError):
            pass
    ...
```

---

### P1-2: HTTP Client Not Closed on Exception Paths

**Problem:** In [_http.py](../../../src/agentic_cba_indicators/tools/_http.py#L139-L141), if an exception occurs before `client.close()` is called in the finally block, and `should_close` is True, resources may leak if the exception propagates incorrectly.

**Why it matters:** Connection leaks can exhaust system resources over time, leading to service degradation.

**Affected files:**
- [src/agentic_cba_indicators/tools/_http.py](../../../src/agentic_cba_indicators/tools/_http.py#L53)

**Fix:** Use context manager pattern consistently:

```python
def fetch_json(url: str, params: dict | None = None, ...) -> dict | list:
    with (client or create_client()) as http_client:
        # All logic inside context manager
        ...
```

---

### P1-3: YAML Config Allows Arbitrary Python Code via Environment Variable Expansion

**Problem:** The `_expand_env_vars` function in [provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py#L42-L55) recursively expands `${VAR}` patterns. While it only reads environment variables, a user with write access to the config file could inject patterns that reference unintended variables.

**Why it matters:** Configuration injection could allow extraction of sensitive environment variables not intended for the application.

**Affected files:**
- [src/agentic_cba_indicators/config/provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py#L42)

**Fix:** Whitelist allowed environment variables for expansion:

```python
ALLOWED_ENV_VARS = {'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY', 'OLLAMA_API_KEY', ...}

def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, str):
        matches = re.findall(r"\$\{([^}]+)\}", value)
        for var_name in matches:
            if var_name not in ALLOWED_ENV_VARS:
                raise ValueError(f"Environment variable '{var_name}' not allowed in config")
            ...
```

---

### P1-4: ChromaDB Path Traversal Vulnerability

**Problem:** The `get_kb_path()` function in [paths.py](../../../src/agentic_cba_indicators/paths.py#L81-L87) accepts `AGENTIC_CBA_DATA_DIR` from environment without validating for path traversal sequences like `../`.

**Why it matters:** A malicious environment variable could cause data to be written outside intended directories, potentially overwriting system files or accessing sensitive locations.

**Affected files:**
- [src/agentic_cba_indicators/paths.py](../../../src/agentic_cba_indicators/paths.py#L22)

**Fix:** Validate resolved paths are within expected boundaries:

```python
def get_data_dir() -> Path:
    env_dir = os.environ.get("AGENTIC_CBA_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir).expanduser().resolve()
        # Ensure resolved path doesn't escape expected locations
        if ".." in str(data_dir) or not data_dir.is_absolute():
            raise ValueError(f"Invalid data directory path: {env_dir}")
    ...
```

---

### P1-5: No Rate Limiting on Knowledge Base Queries

**Problem:** The knowledge base tools in [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py) allow unlimited queries to Ollama embedding endpoint without any rate limiting.

**Why it matters:** A malicious or buggy agent loop could flood the embedding service with requests, causing service denial or excessive API costs.

**Affected files:**
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L65)

**Fix:** Add simple rate limiting:

```python
from time import time
_last_embedding_call = 0.0
MIN_EMBEDDING_INTERVAL = 0.1  # 10 calls/second max

def _get_embedding(text: str) -> Sequence[float]:
    global _last_embedding_call
    now = time()
    if now - _last_embedding_call < MIN_EMBEDDING_INTERVAL:
        sleep(MIN_EMBEDDING_INTERVAL - (now - _last_embedding_call))
    _last_embedding_call = time()
    ...
```

---

### P1-6: Unhandled JSON Decode Errors in API Responses

**Problem:** Multiple tool modules call `response.json()` without handling `JSONDecodeError`, which can occur when APIs return non-JSON error pages.

**Why it matters:** Unhandled exceptions crash tool execution and provide poor user experience. The raw exception may leak information about internal API interactions.

**Affected files:**
- [src/agentic_cba_indicators/tools/commodities.py](../../../src/agentic_cba_indicators/tools/commodities.py#L137)
- [src/agentic_cba_indicators/tools/labor.py](../../../src/agentic_cba_indicators/tools/labor.py#L163)
- [src/agentic_cba_indicators/tools/gender.py](../../../src/agentic_cba_indicators/tools/gender.py#L155)

**Fix:** Wrap JSON parsing in try-except:

```python
try:
    return response.json()
except json.JSONDecodeError:
    raise APIError(f"Invalid JSON response from API (status {response.status_code})")
```

---

### P1-7: Duplicate Country Code Mappings Across Multiple Modules

**Problem:** Country code mappings are duplicated in [_mappings.py](../../../src/agentic_cba_indicators/tools/_mappings.py), [labor.py](../../../src/agentic_cba_indicators/tools/labor.py#L88), [gender.py](../../../src/agentic_cba_indicators/tools/gender.py#L123), and [commodities.py](../../../src/agentic_cba_indicators/tools/commodities.py#L59). These mappings are inconsistent and incomplete.

**Why it matters:** Inconsistent mappings lead to different behavior across tools for the same country input, confusing users and producing unreliable results.

**Affected files:**
- [src/agentic_cba_indicators/tools/_mappings.py](../../../src/agentic_cba_indicators/tools/_mappings.py)
- [src/agentic_cba_indicators/tools/labor.py](../../../src/agentic_cba_indicators/tools/labor.py#L88)
- [src/agentic_cba_indicators/tools/gender.py](../../../src/agentic_cba_indicators/tools/gender.py#L123)
- [src/agentic_cba_indicators/tools/commodities.py](../../../src/agentic_cba_indicators/tools/commodities.py#L59)

**Fix:** Centralize all country code mappings in `_mappings.py` with support for multiple code formats (ISO-2, ISO-3, UN, FAO) and have all tools use the centralized lookup.

---

### P1-8: Embedding Failures Silently Produce Partial Knowledge Base

**Problem:** In [ingest_excel.py](../../../scripts/ingest_excel.py#L588-L594), embedding failures cause individual documents to be skipped without failing the overall ingestion. This can result in a partially populated knowledge base without clear indication.

**Why it matters:** Users querying the knowledge base may get incomplete results, leading to incorrect conclusions. The silent failure makes debugging difficult.

**Affected files:**
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py#L588)

**Fix:** Add a strict mode that fails on any embedding error, and improve reporting:

```python
if failed_ids:
    if strict:
        raise RuntimeError(f"Embedding failed for {len(failed_ids)} indicators: {failed_ids[:5]}")
    print(f"  ⚠ WARNING: {len(failed_ids)} documents not indexed due to embedding failures")
    print(f"    Failed IDs: {failed_ids[:10]}{'...' if len(failed_ids) > 10 else ''}")
```

---

## P2: Medium Priority Issues

### P2-1: Missing Type Hints in Tool Return Types

**Problem:** Many tool functions lack explicit return type annotations, relying on `-> str` being inferred. This reduces IDE support and static analysis effectiveness.

**Affected files:**
- [src/agentic_cba_indicators/tools/agriculture.py](../../../src/agentic_cba_indicators/tools/agriculture.py)
- [src/agentic_cba_indicators/tools/biodiversity.py](../../../src/agentic_cba_indicators/tools/biodiversity.py)

**Fix:** Add explicit `-> str` return type annotations to all `@tool` decorated functions.

---

### P2-2: Weather Codes Dictionary Duplicated

**Problem:** The weather code-to-description mapping is duplicated in both `get_current_weather` and `get_weather_forecast` functions in [weather.py](../../../src/agentic_cba_indicators/tools/weather.py).

**Affected files:**
- [src/agentic_cba_indicators/tools/weather.py](../../../src/agentic_cba_indicators/tools/weather.py#L38)

**Fix:** Extract to module-level constant `WEATHER_CODES`.

---

### P2-3: Hardcoded Timeout Values

**Problem:** HTTP timeout values (30.0, 60.0, 120.0 seconds) are hardcoded across multiple modules without consistency or configurability.

**Affected files:**
- [src/agentic_cba_indicators/tools/_http.py](../../../src/agentic_cba_indicators/tools/_http.py#L12)
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L68)
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py#L539)

**Fix:** Centralize timeout configuration with environment variable override.

---

### P2-4: No Retry Logic for ChromaDB Operations

**Problem:** ChromaDB operations in [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py) have no retry logic. Transient SQLite locking errors or filesystem issues cause immediate failures.

**Affected files:**
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L78)

**Fix:** Add retry logic for collection operations with exponential backoff.

---

### P2-5: Unsafe Integer Conversion in Indicator ID Parsing

**Problem:** In [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L621), `int(indicator)` is attempted without bounds checking. Very large integers could cause issues.

**Affected files:**
- [src/agentic_cba_indicators/tools/knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L621)

**Fix:** Add bounds validation:

```python
indicator_id = int(indicator)
if not (1 <= indicator_id <= 999999):
    return None, f"Invalid indicator ID: {indicator_id}"
```

---

### P2-6: PDF Extraction Without Sanitization

**Problem:** In [ingest_usecases.py](../../../scripts/ingest_usecases.py#L197-L211), text extracted from PDFs is used directly without sanitization. Malicious PDFs could inject control characters or excessively long strings.

**Affected files:**
- [scripts/ingest_usecases.py](../../../scripts/ingest_usecases.py#L197)

**Fix:** Sanitize extracted text:

```python
def sanitize_text(text: str, max_len: int = 50000) -> str:
    text = text[:max_len]
    text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
    return text.strip()
```

---

### P2-7: Missing Docstrings on Helper Functions

**Problem:** Several internal helper functions lack docstrings, reducing code comprehension.

**Affected files:**
- [src/agentic_cba_indicators/tools/_http.py](../../../src/agentic_cba_indicators/tools/_http.py) - `create_client`
- [src/agentic_cba_indicators/config/provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py#L108) - `_validate_config`

**Fix:** Add docstrings explaining purpose, parameters, and return values.

---

### P2-8: Test Coverage Gaps for Error Paths

**Problem:** Tests primarily cover happy paths. Error conditions like network failures, invalid API responses, and configuration errors lack coverage.

**Affected files:**
- [tests/test_tools_weather.py](../../../tests/test_tools_weather.py)
- [tests/test_config.py](../../../tests/test_config.py)

**Fix:** Add tests for:
- API returning non-JSON response
- Network timeout scenarios
- Invalid coordinate inputs
- Missing/corrupted knowledge base

---

### P2-9: No Logging Framework Integration

**Problem:** The codebase uses `print()` for all output instead of a proper logging framework. This makes it impossible to filter, redirect, or structure logs appropriately.

**Affected files:**
- [src/agentic_cba_indicators/cli.py](../../../src/agentic_cba_indicators/cli.py)
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py)

**Fix:** Replace print statements with Python's `logging` module:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Processing %d indicators", len(indicators))
```

---

### P2-10: Magic Numbers in Data Processing

**Problem:** Various magic numbers appear without explanation: `6000` (max chars for embedding), `85` (fuzzy match threshold), `256` (cache size).

**Affected files:**
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py#L529)
- [scripts/ingest_usecases.py](../../../scripts/ingest_usecases.py#L62)

**Fix:** Extract to named constants with explanatory comments.

---

### P2-11: Inconsistent Error Message Formatting

**Problem:** Error messages use inconsistent formatting: some use `f"Error: {e}"`, others use `format_error()`, and some return raw exception strings.

**Affected files:** Multiple tool modules

**Fix:** Use `format_error()` consistently across all tools.

---

### P2-12: CLI Argument Parsing Uses Manual String Splitting

**Problem:** In [cli.py](../../../src/agentic_cba_indicators/cli.py#L190-L198), command-line arguments are parsed manually using string splitting instead of `argparse`.

**Affected files:**
- [src/agentic_cba_indicators/cli.py](../../../src/agentic_cba_indicators/cli.py#L190)

**Fix:** Use `argparse` for robust, documented argument handling:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CBA Indicators CLI Chatbot")
    parser.add_argument("--config", type=Path, help="Path to providers.yaml")
    parser.add_argument("--provider", choices=["ollama", "anthropic", "openai", "bedrock", "gemini"])
    return parser.parse_args()
```

---

## P3: Low Priority Issues

### P3-1: Unused Import Warnings

**Problem:** Some modules import `TYPE_CHECKING` but don't have any type-only imports, or import `Any` without using it.

**Affected files:**
- [src/agentic_cba_indicators/tools/climate.py](../../../src/agentic_cba_indicators/tools/climate.py)

**Fix:** Remove unused imports or add `# noqa: F401` if intentional.

---

### P3-2: Inconsistent Docstring Style

**Problem:** Docstrings mix Google style and NumPy style for parameter documentation.

**Fix:** Standardize on Google style docstrings as used in most of the codebase.

---

### P3-3: Missing `__all__` in Some Modules

**Problem:** Some modules like `_http.py` and `_geo.py` lack `__all__` declarations.

**Fix:** Add `__all__` to explicitly declare public API.

---

### P3-4: Typo in Column Name

**Problem:** In [ingest_excel.py](../../../scripts/ingest_excel.py#L466), the column name `"Social and partcipatory"` has a typo (missing 'i').

**Affected files:**
- [scripts/ingest_excel.py](../../../scripts/ingest_excel.py#L466)

**Fix:** Correct to `"Social and participatory"` (requires Excel file update) or add column name alias handling.

---

### P3-5: Version String Hardcoded

**Problem:** Version `"0.2.0"` is in `pyproject.toml` but may need to be accessible programmatically.

**Fix:** Use `importlib.metadata.version("agentic-cba-indicators")` where version is needed.

---

### P3-6: README URLs Contain Placeholder

**Problem:** In [pyproject.toml](../../../pyproject.toml#L59-L62), the repository URLs contain `yourusername` placeholder.

**Affected files:**
- [pyproject.toml](../../../pyproject.toml#L59)

**Fix:** Update with actual repository URL.

---

### P3-7: Commented-Out Code in Tests

**Problem:** Some test files contain commented sections that should either be enabled or removed.

**Fix:** Clean up test files.

---

## Architecture Notes

### Structural Strengths

1. **Clean separation of concerns**: Tools are isolated in their own modules with a clear HTTP abstraction layer.
2. **Centralized configuration**: The provider factory pattern allows easy switching between AI providers.
3. **XDG-compliant paths**: The `platformdirs` integration follows standard conventions.
4. **Deterministic ingestion**: The knowledge base ingestion uses stable IDs for idempotent updates.

### Areas for Improvement

1. **Dependency Injection**: The current design tightly couples tools to their HTTP client implementation. Consider injecting the HTTP client for better testability.

2. **Error Handling Strategy**: The codebase lacks a unified error handling strategy. Consider creating a hierarchy of domain-specific exceptions (`IndicatorNotFoundError`, `APIRateLimitError`, etc.) that provide structured information to the agent.

3. **Async Support**: All API calls are synchronous. For better performance when multiple data sources are queried, consider adding async variants of tools.

4. **Configuration Validation**: The config validation in `_validate_config` is thorough but could benefit from a schema validation library like Pydantic for better error messages and maintainability.

5. **Knowledge Base Versioning**: There's no versioning for the knowledge base schema. Adding schema version tracking would help manage migrations when the indicator structure changes.

6. **Tool Discovery**: The `REDUCED_TOOLS` and `FULL_TOOLS` lists are manually maintained. Consider using a decorator-based registration system.

### Security Model Assessment (STRIDE)

| Threat | Status | Notes |
|--------|--------|-------|
| **Spoofing** | Medium Risk | API keys validated but no mutual TLS |
| **Tampering** | Low Risk | Config files could be tampered if accessible |
| **Repudiation** | Medium Risk | No audit logging of tool invocations |
| **Information Disclosure** | High Risk | Error messages may leak sensitive data (P0-1, P0-2) |
| **Denial of Service** | Medium Risk | Unbounded cache (P0-3), no rate limiting (P1-5) |
| **Elevation of Privilege** | Low Risk | No privilege escalation paths identified |

### Privacy Assessment (LINDDUN)

- **Linkability**: User queries could be linked across sessions via ChromaDB persistence
- **Identifiability**: Location queries (geocoding) could identify users
- **Non-repudiation**: No logging, so no non-repudiation concerns
- **Detectability**: No sensitive detection patterns
- **Disclosure**: Error messages could disclose internal structure
- **Unawareness**: Users not informed of data processing
- **Non-compliance**: No GDPR/privacy compliance implementation

### Recommended Priority Order

1. Fix P0 issues immediately (security critical)
2. Address P1 issues in next sprint
3. Schedule P2 issues for technical debt cleanup
4. Include P3 issues in routine maintenance

---

*End of Review*
