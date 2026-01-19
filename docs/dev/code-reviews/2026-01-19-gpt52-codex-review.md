# Repository Code Review (GPT-5.2-Codex)

## Executive summary
- CR-0001 exposes a real USDA FAS API key and personal emails in `.env`, creating immediate credential leakage risk.
- CR-0002 runs the CLI twice because `__main__` is duplicated, causing a second session after exit.
- CR-0003 makes Streamlit UI token budgeting inconsistent with CLI, increasing context overflow risk.
- CR-0004 corrupts geocoding cache misses into a fake (0,0) location after the first miss.
- CR-0006 timeouts do not cancel work, so timed-out tools keep running in background threads.
- CR-0008 uses a longitude-range formula that explodes near the equator, yielding invalid queries.
- CR-0010 references a missing LICENSE in build config, likely breaking sdist or omitting license files.
- CR-0012/CR-0013 show pervasive mojibake/control characters that degrade user-visible units and output.

Risk posture: Medium-high. There is a confirmed secret exposure plus multiple correctness and reliability defects in user-facing tools. Most issues are localized and fixable, but current output quality and edge-case handling can erode trust in results if left unaddressed.

## Review methodology
- Scanned `src/agentic_cba_indicators`, `tests`, `scripts`, `docs`, `.github`, `pyproject.toml`, `.env`, `Makefile`, and `uv.lock`.
- Reviewed tool modules, config, ingestion scripts, and tests for correctness, security, and reliability issues.
- No issues found in ADR content (`docs/adr`) and memory-bank planning docs beyond documentation-only content.
- Assumptions/limitations: No network calls executed; no runtime execution of ingestion or APIs; PDF/Excel content not validated for data quality.

## Issue index (tracking system)
| ID | Severity | Category | Component | File:Line | Title | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| CR-0001 | High | Security | Env/Secrets | `.env:11` | Real API key and emails stored in repo `.env` | High |
| CR-0002 | Medium | Broken behaviour | CLI | `src/agentic_cba_indicators/cli.py:357` | CLI runs twice due to duplicate `__main__` guard | High |
| CR-0003 | Medium | Reliability | UI/Memory | `src/agentic_cba_indicators/ui.py:107` | UI token budget ignores system prompt/tool overhead | Medium |
| CR-0004 | Medium | Bug | Geo utils | `src/agentic_cba_indicators/tools/_geo.py:113` | Cached “not found” returns fake 0,0 location | High |
| CR-0005 | Low | Bug | Geo utils | `src/agentic_cba_indicators/tools/_geo.py:216` | `clear_cache()` uses undefined `OrderedDict` | High |
| CR-0006 | Medium | Reliability | Tool timeout | `src/agentic_cba_indicators/tools/_timeout.py:36` | Timed-out tools continue running in background | High |
| CR-0007 | Medium | Bug | Weather tool | `src/agentic_cba_indicators/tools/weather.py:154` | Forecast indexing can throw on mismatched arrays (Hypothesis) | Medium |
| CR-0008 | Medium | Bug | Biodiversity tool | `src/agentic_cba_indicators/tools/biodiversity.py:393` | Longitude range formula explodes near equator | High |
| CR-0009 | Medium | Reliability | GFW tools | `src/agentic_cba_indicators/tools/forestry.py:37` | Retry settings unused; transient API failures not retried | Medium |
| CR-0010 | Medium | Config/Build | Packaging | `pyproject.toml:77` | sdist includes `/LICENSE` but file is missing | High |
| CR-0011 | Medium | Bug | Multiple tools | `src/agentic_cba_indicators/tools/labor.py:225` | Valid zero values treated as missing across tools | Medium |
| CR-0012 | Medium | Bug | Multiple tools | `src/agentic_cba_indicators/tools/weather.py:104` | Unit symbols corrupted (°C, m², CO2e, etc.) | High |
| CR-0013 | Low | Broken behaviour | Output text | `src/agentic_cba_indicators/cli.py:201` | Control characters/mojibake in user-visible output | High |
| CR-0014 | Low | Dead code | Commodities tool | `src/agentic_cba_indicators/tools/commodities.py:626` | Duplicate returns in `search_commodity_data()` | High |
| CR-0015 | Low | Docs mismatch | Tooling docs | `src/agentic_cba_indicators/tools/__init__.py:149` | Tool count claims inconsistent across docs/config | High |
| CR-0016 | Low | Test gap | CI | `.github/copilot-instructions.md:1` | No CI workflows found for tests/linting | Medium |

## Findings (detailed)

### CR-0001: Real API key and emails stored in repo `.env`
- Severity: High
- Category: Security
- Component: Env/Secrets
- Location: `.env:11`
- Evidence:
  - `.env` includes real values (redacted here):
    ```
    USDA_FAS_API_KEY=<REDACTED>
    CROSSREF_EMAIL=<REDACTED>
    UNPAYWALL_EMAIL=<REDACTED>
    ```
- Impact:
  - API key exposure enables unauthorized usage or quota exhaustion.
  - Personal emails can be harvested and abused.
- Reproduction/Trigger:
  - Open `.env` in repo root.
- Recommended fix (no code):
  - Remove secrets from the repo, rotate the USDA FAS key, and move real values to local `.env` or a secret manager.
  - Ensure `.env` stays untracked; keep `.env.example` for placeholders only.
  - Add pre-commit/CI secret scanning.
- Tests/Verification:
  - Verify git status does not include `.env`.
  - Confirm rotated keys work and old key is invalid.
- Notes:
  - Related: CR-0016 (lack of CI could allow secret regressions).
  - This file is ignored by `.gitignore`, and is not published. Confirm that no prior commits exposed these secrets. It exists for local development only.

### CR-0002: CLI runs twice due to duplicate `__main__` guard
- Severity: Medium
- Category: Broken behaviour
- Component: CLI
- Location: `src/agentic_cba_indicators/cli.py:357`
- Evidence:
  ```py
  if __name__ == "__main__":
      main()
  if __name__ == "__main__":
      main()
  ```
- Impact:
  - The CLI starts a second session after the first exits; users must quit twice.
- Reproduction/Trigger:
  - Run `python -m agentic_cba_indicators.cli` and exit; a second prompt appears.
- Recommended fix (no code):
  - Remove the duplicate guard.
- Tests/Verification:
  - Run the CLI and confirm it exits after a single quit.
- Notes:
  - None.

### CR-0003: UI token budget ignores system prompt/tool overhead
- Severity: Medium
- Category: Reliability
- Component: UI/Memory
- Location: `src/agentic_cba_indicators/ui.py:107`
- Evidence:
  ```py
  if agent_config.context_budget is not None:
      conversation_manager = TokenBudgetConversationManager(
          max_tokens=agent_config.context_budget,
      )
  ```
  - CLI accounts for system prompt/tool definitions:
    ```py
    system_prompt_budget = _estimate_system_prompt_budget(system_prompt, tools)
    TokenBudgetConversationManager(..., system_prompt_budget=system_prompt_budget)
    ```
- Impact:
  - UI may exceed model context when `context_budget` is set, causing overflow errors or truncation inconsistencies compared to CLI.
- Reproduction/Trigger:
  - Use UI with `context_budget` configured and a large tool set/system prompt.
- Recommended fix (no code):
  - Compute and pass `system_prompt_budget` in the UI, matching CLI behavior.
- Tests/Verification:
  - Add a UI test that verifies budget reservation and that prompts do not exceed model limits.
- Notes:
  - Related: CR-0011 (large outputs can also pressure context limits).

### CR-0004: Cached “not found” returns fake 0,0 location
- Severity: Medium
- Category: Bug
- Component: Geo utils
- Location: `src/agentic_cba_indicators/tools/_geo.py:113`
- Evidence:
  ```py
  cached = _geocode_cache.get(cache_key)
  if cached is not None:
      return GeoLocation(... latitude=cached.get("latitude", 0.0), ...)
  ...
  _geocode_cache[cache_key] = {}  # Empty dict marks "not found"
  ```
- Impact:
  - After a miss, subsequent calls return `(0.0, 0.0)` as a valid location, producing incorrect tool results.
- Reproduction/Trigger:
  - Call `geocode_city("NonexistentCity")` twice; the second call returns a non-None location.
- Recommended fix (no code):
  - Store `None` as the miss marker or check for empty dict before returning cached results.
- Tests/Verification:
  - Add a test asserting that cached misses return `None` rather than a default location.
- Notes:
  - Related: CR-0005 for cache clearing.

### CR-0005: `clear_cache()` uses undefined `OrderedDict`
- Severity: Low
- Category: Bug
- Component: Geo utils
- Location: `src/agentic_cba_indicators/tools/_geo.py:216`
- Evidence:
  ```py
  def clear_cache() -> None:
      global _geocode_cache
      _geocode_cache = OrderedDict()
  ```
- Impact:
  - Calling `clear_cache()` raises `NameError` and replaces the TTL cache with a different type.
- Reproduction/Trigger:
  - Call `agentic_cba_indicators.tools._geo.clear_cache()`.
- Recommended fix (no code):
  - Remove this function or use the existing TTL cache’s `.clear()` (as in `clear_geocode_cache`).
- Tests/Verification:
  - Add a test that calls `clear_cache()` and asserts cache is emptied without exceptions.
- Notes:
  - Related: CR-0004.

### CR-0006: Timed-out tools continue running in background
- Severity: Medium
- Category: Reliability
- Component: Tool timeout
- Location: `src/agentic_cba_indicators/tools/_timeout.py:36`
- Evidence:
  ```py
  future = executor.submit(func, *args, **kwargs)
  return future.result(timeout=seconds)
  ```
- Impact:
  - The timed-out function keeps running after a timeout, potentially causing duplicate API calls, side effects, or resource leaks.
- Reproduction/Trigger:
  - Call a long-running tool with a short timeout; observe background work continuing.
- Recommended fix (no code):
  - Cancel futures on timeout, or use process-based timeouts for safe termination, or redesign to use per-request timeouts instead of wall-clock thread timeouts.
- Tests/Verification:
  - Add a test that asserts timed-out functions do not continue mutating state.
- Notes:
  - None.

### CR-0007: Forecast indexing can throw on mismatched arrays (Hypothesis)
- Severity: Medium
- Category: Bug
- Component: Weather tool
- Location: `src/agentic_cba_indicators/tools/weather.py:154`
- Evidence:
  ```py
  for i in range(len(dates)):
      weather_desc = WEATHER_CODE_EMOJI.get(weather[i], "Unknown")
      ... temps_max[i] ... temps_min[i] ... precip[i] ... wind[i]
  ```
- Impact:
  - If the API returns arrays of different lengths or missing fields, this loop raises `IndexError` and the tool fails.
- Reproduction/Trigger:
  - Hypothesis: an Open-Meteo response with a missing `weather_code` or shorter array.
- Recommended fix (no code):
  - Iterate using `zip()` with a safe fill policy or validate array lengths before indexing.
- Tests/Verification:
  - Add a test with mismatched arrays and assert a graceful response.
- Notes:
  - Hypothesis: confirm by inspecting actual Open-Meteo responses for edge cases.

### CR-0008: Longitude range formula explodes near equator
- Severity: Medium
- Category: Bug
- Component: Biodiversity tool
- Location: `src/agentic_cba_indicators/tools/biodiversity.py:393`
- Evidence:
  ```py
  lon_range = radius_km / (111 * abs(lat) / 90 + 0.001) if abs(lat) < 89 else ...
  ```
- Impact:
  - At or near the equator, `abs(lat)` is ~0, making `lon_range` huge and yielding invalid bounding boxes or overly broad queries.
- Reproduction/Trigger:
  - Call `get_biodiversity_summary("0,0", radius_km=50)` and inspect the request bounds.
- Recommended fix (no code):
  - Use a cosine-based formula for longitude scaling and clamp to valid bounds.
- Tests/Verification:
  - Add tests for lat=0 and lat=80 that validate reasonable `lon_range`.
- Notes:
  - None.

### CR-0009: Retry settings unused; transient API failures not retried
- Severity: Medium
- Category: Reliability
- Component: GFW tools
- Location: `src/agentic_cba_indicators/tools/forestry.py:37`
- Evidence:
  ```py
  GFW_RETRIES: Final[int] = 3
  ...
  response = client.get(url, params=params)
  ... raise APIError on 429/5xx without retry
  ```
- Impact:
  - Rate limits or transient server errors immediately fail without backoff, reducing tool reliability.
- Reproduction/Trigger:
  - Simulate 429/500 responses from GFW endpoints.
- Recommended fix (no code):
  - Implement retry/backoff in `_gfw_get()` and `_gfw_post()` or reuse shared retry helpers.
- Tests/Verification:
  - Add tests with mocked 429/500 responses to verify retry behavior.
- Notes:
  - None.

### CR-0010: sdist includes `/LICENSE` but file is missing
- Severity: Medium
- Category: Config/Build
- Component: Packaging
- Location: `pyproject.toml:77`
- Evidence:
  ```toml
  [tool.hatch.build.targets.sdist]
  include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
  ]
  ```
- Impact:
  - `hatchling` may fail the build or produce a distribution missing the license despite declaring MIT in metadata.
- Reproduction/Trigger:
  - Build sdist; observe missing LICENSE file.
- Recommended fix (no code):
  - Add a LICENSE file or remove it from the sdist include list and update project metadata accordingly.
- Tests/Verification:
  - Build sdist/wheel and confirm LICENSE is included.
- Notes:
  - None.

### CR-0011: Valid zero values treated as missing across tools
- Severity: Medium
- Category: Bug
- Component: Multiple tools
- Location: `src/agentic_cba_indicators/tools/labor.py:225`
- Evidence:
  - Labor trend skips zero values:
    ```py
    if prev_value and value:
        change = float(value) - float(prev_value)
    ```
  - Similar truthiness checks suppress zeros:
    - `src/agentic_cba_indicators/tools/nasa_power.py:387`
    - `src/agentic_cba_indicators/tools/soilgrids.py:286`
    - `src/agentic_cba_indicators/tools/sdg.py:373`
    - `src/agentic_cba_indicators/tools/biodiversity.py:309`
- Impact:
  - Legitimate zero values (e.g., 0 precipitation, 0 coordinates) are omitted or shown as “N/A,” skewing summaries and trends.
- Reproduction/Trigger:
  - Provide data with 0.0 values; observe missing output/trend.
- Recommended fix (no code):
  - Use explicit `is not None` checks and sentinel comparisons instead of truthiness.
- Tests/Verification:
  - Add unit tests for zero values in each affected tool.
- Notes:
  - Related: CR-0003 (context budgeting), CR-0012 (unit correctness).

### CR-0012: Unit symbols corrupted (°C, m², CO2e, etc.)
- Severity: Medium
- Category: Bug
- Component: Multiple tools
- Location: `src/agentic_cba_indicators/tools/weather.py:104`
- Evidence:
  - Examples of corrupted units:
    ```py
    "øC"  # weather.py
    "MJ/mı/day"  # nasa_power.py
    "kg/dmü"  # soilgrids.py
    "COż" / "COże"  # forestry.py
    "kmı"  # socioeconomic.py
    ```
- Impact:
  - Outputs show incorrect units, which can mislead users interpreting measurements.
- Reproduction/Trigger:
  - Call affected tools and observe displayed units.
- Recommended fix (no code):
  - Normalize unit strings to correct symbols (e.g., "°C", "m^2", "CO2e") and ensure files are UTF-8.
- Tests/Verification:
  - Add snapshot tests for tool outputs to validate unit formatting.
- Notes:
  - Related: CR-0013 (general output mojibake).

### CR-0013: Control characters/mojibake in user-visible output
- Severity: Low
- Category: Broken behaviour
- Component: Output text
- Location: `src/agentic_cba_indicators/cli.py:201`
- Evidence:
  - CLI help includes bell character (rendered here as `\x07`):
    ```py
    print("  \x07 What's the weather in Tokyo?")
    ```
  - Similar control/mojibake in other outputs (e.g., `labor.py:228`, `agriculture.py:157`, `sdg.py:185`) and README structure symbols (`README.md:154`).
- Impact:
  - Terminal beeps/garbled text; reduced readability of output and docs.
- Reproduction/Trigger:
  - Run CLI or tools and view output in a standard terminal.
- Recommended fix (no code):
  - Replace control characters with ASCII bullets or standard Unicode symbols; normalize file encoding.
- Tests/Verification:
  - Add tests that assert no control characters in output strings.
- Notes:
  - Related: CR-0012.

### CR-0014: Duplicate returns in `search_commodity_data()`
- Severity: Low
- Category: Dead code
- Component: Commodities tool
- Location: `src/agentic_cba_indicators/tools/commodities.py:626`
- Evidence:
  ```py
  return "\n".join(output)
  return "\n".join(output)
  return "\n".join(output)
  ```
- Impact:
  - Unreachable code; indicates editing mistakes and increases maintenance risk.
- Reproduction/Trigger:
  - Static inspection.
- Recommended fix (no code):
  - Remove redundant returns and keep a single exit point.
- Tests/Verification:
  - None needed beyond linting.
- Notes:
  - None.

### CR-0015: Tool count claims inconsistent across docs/config
- Severity: Low
- Category: Docs mismatch
- Component: Tooling docs
- Location: `src/agentic_cba_indicators/tools/__init__.py:149`
- Evidence:
  - Code comments claim 24/62 tools, but actual counts are 23/61:
    ```py
    # Reduced tool set (24 tools)
    # Full tool set (62 tools)
    ```
  - Config and README claim different counts:
    - `src/agentic_cba_indicators/config/providers.yaml:74` (19/52)
    - `README.md:160` (52 total)
- Impact:
  - Users and maintainers are misled about available tool capacity and sizing guidance.
- Reproduction/Trigger:
  - Compare counts in docs vs list sizes in `tools/__init__.py`.
- Recommended fix (no code):
  - Update comments/docs to reflect actual counts or adjust lists to match published counts.
- Tests/Verification:
  - Add a test asserting the documented counts match the list lengths.
- Notes:
  - None.

### CR-0016: No CI workflows found for tests/linting
- Severity: Low
- Category: Test gap
- Component: CI
- Location: `.github/copilot-instructions.md:1`
- Evidence:
  - `.github/` contains only `copilot-instructions.md`; no `.github/workflows/` directory exists.
- Impact:
  - Test and lint regressions can ship unnoticed; secret leaks and output regressions are easier to miss.
- Reproduction/Trigger:
  - Inspect `.github` directory structure.
- Recommended fix (no code):
  - Add CI workflows for tests, linting, and secret scanning.
- Tests/Verification:
  - Ensure CI runs on PRs and main branch.
- Notes:
  - Related: CR-0001 and CR-0013.

## Cross-cutting concerns
- **Observability:** `setup_logging()` is documented but not called by CLI/UI entry points, so structured logging and correlation IDs may not be active by default.
- **API consistency:** Several tools return user-facing summaries but differ in error handling and formatting conventions; consider a shared response/format contract.
- **Config/deployment posture:** Env var whitelist is good, but storing secrets in `.env` weakens posture; add secret scanning and stronger environment hygiene.
- **Testing strategy gaps:** No CI workflows; limited coverage for external API edge cases and output formatting. Add contract tests for API payload shapes and output snapshots.
- **No issues found:** ADRs and memory-bank planning docs are informational only and do not appear to introduce runtime risks.

## Appendix
- **Questionable areas needing human confirmation:**
  - Whether Open-Meteo can return mismatched array lengths for daily fields (CR-0007).
  - Whether output encoding issues stem from source file encoding or rendering environment (CR-0012/CR-0013).
- **Hypotheses and evidence to confirm:**
  - CR-0007 is a hypothesis; confirm by sampling Open-Meteo responses with missing fields or partial daily arrays.
