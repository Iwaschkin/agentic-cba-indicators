# Repository Code Review (GPT-5.2-Codex)

## Executive summary
- **UI prompt configuration is ignored**: the Streamlit UI always uses the default system prompt, even when `prompt_name` is configured.
- **Gemini `top_p` config is unused**: the config value exists but is never passed to the model constructor.
- **Batch embeddings can crash on malformed JSON**: `get_embeddings_batch()` does not guard `response.json()` failures, so ingestion can fail without fallback.
- **Timeout metadata never set**: the timeout decorator assigns metadata after a `return`, so those flags are unreachable.
- **Timeouts don’t stop underlying work**: timed-out tool calls continue executing in background threads, risking thread exhaustion.
- **Logging configuration never applied at entry points**: `setup_logging()` is not called in CLI/UI, so JSON formatting and correlation IDs don’t activate.
- **Documentation mismatch**: `setup_logging()` docs reference `force=True` which does not exist.

Risk posture: **Moderate**. The core functionality appears stable, but there are several correctness and reliability gaps around configuration fidelity, ingestion resilience, and operational observability that can surface as confusing behavior or production brittleness.

## Review methodology
- **Scanned**: `src/agentic_cba_indicators/` (CLI, UI, config, tools, security, logging), `scripts/`, `pyproject.toml`, `README.md`, `CODE_QUALITY.md`, `CONTRIBUTING.md`, and docs under `docs/`.
- **Focused checks**: tool execution and timeout behavior, configuration ingestion, prompt selection, embedding pipeline robustness, and logging/observability wiring.
- **Limitations**: No runtime execution, network calls, or external service validation. Findings are based solely on static evidence in the repository.
- **No issues found**: docs/adr (architecture decisions), security.py (input/PDF sanitization), paths.py (path safety), tools/_help.py (internal help tooling), audit/observability modules (design and tests).

## Issue index (tracking system)
| ID | Severity | Category | Component | File:Line | Title | Confidence |
|---|---|---|---|---|---|---|
| CR-0001 | Medium | Broken behaviour | UI agent factory | src/agentic_cba_indicators/ui.py:117-131 | UI ignores `prompt_name` config | High |
| CR-0002 | Low | Config/Build | Provider config | src/agentic_cba_indicators/config/providers.yaml:63-68; src/agentic_cba_indicators/config/provider_factory.py:418-426 | Gemini `top_p` is never applied | High |
| CR-0003 | Medium | Reliability | Embeddings | src/agentic_cba_indicators/tools/_embedding.py:257-296 | Batch embeddings crash on malformed JSON | Medium |
| CR-0004 | Low | Bug | Timeout utilities | src/agentic_cba_indicators/tools/_timeout.py:62-82 | Timeout metadata flags never set | High |
| CR-0005 | Medium | Reliability | Timeout utilities | src/agentic_cba_indicators/tools/_timeout.py:65-78 | Timed-out tools keep running in background threads | Medium |
| CR-0006 | Medium | Config/Build | CLI/UI logging | src/agentic_cba_indicators/cli.py:248-322; src/agentic_cba_indicators/ui.py:400-520; src/agentic_cba_indicators/logging_config.py:1-29 | Logging setup not invoked at entry points | Medium |
| CR-0007 | Low | Docs mismatch | Logging config | src/agentic_cba_indicators/logging_config.py:224-229 | `setup_logging()` docs mention non-existent `force` | High |

## Findings (detailed)

### CR-0001: UI ignores `prompt_name` config
- **Severity:** Medium
- **Category:** Broken behaviour
- **Component:** UI agent factory
- **Location:** src/agentic_cba_indicators/ui.py:117-131
- **Evidence:**
  - The UI loads config and agent config, but calls `get_system_prompt()` with no `prompt_name` argument:
    - `agent_config = get_agent_config(config)`
    - `system_prompt = get_system_prompt()`
- **Impact:**
  - UI sessions always use the default prompt (`system_prompt_minimal`), ignoring user configuration. This creates behavior divergence between CLI and UI and can break intended prompt constraints.
- **Reproduction/Trigger:**
  - Set `agent.prompt_name: system_prompt` in providers.yaml and launch the Streamlit UI; it still loads the default prompt.
- **Recommended fix (no code):**
  - Pass `agent_config.prompt_name` into `get_system_prompt()` for UI agent creation. Consider adding a UI selector or surfacing the active prompt in the sidebar.
- **Tests/Verification:**
  - Add a unit test for `create_agent_for_ui()` verifying the prompt name passed matches config. Add a UI integration test (or snapshot) if available.
- **Notes:**
  - Related to CLI behavior which already respects `prompt_name`.

### CR-0002: Gemini `top_p` is never applied
- **Severity:** Low
- **Category:** Config/Build
- **Component:** Provider config
- **Location:** src/agentic_cba_indicators/config/providers.yaml:63-68; src/agentic_cba_indicators/config/provider_factory.py:418-426
- **Evidence:**
  - `providers.yaml` includes `top_p: 0.9` for Gemini, but `create_model()` only passes `temperature` and `max_output_tokens`.
- **Impact:**
  - The configured `top_p` has no effect, leading to inconsistent model behavior and confusion for users who expect their config to be honored.
- **Reproduction/Trigger:**
  - Set `top_p` in `providers.yaml` and run with Gemini; behavior remains unaffected because the parameter is ignored.
- **Recommended fix (no code):**
  - Include `top_p` (and other supported provider params) in `params` when constructing `GeminiModel`, or document that `top_p` must be nested under `options` and passed through consistently.
- **Tests/Verification:**
  - Unit test for `get_provider_config` + `create_model` ensuring provider-specific params are included.

### CR-0003: Batch embeddings crash on malformed JSON
- **Severity:** Medium
- **Category:** Reliability
- **Component:** Embeddings
- **Location:** src/agentic_cba_indicators/tools/_embedding.py:257-296
- **Evidence:**
  - `response.json()` is called without try/except. If JSON parsing fails, the function raises and no fallback occurs.
- **Impact:**
  - Ingestion can fail hard on transient API issues (HTML error pages, truncated JSON), and the batch fallback path is skipped.
- **Reproduction/Trigger:**
  - Ollama returns a 200 response with invalid JSON (proxy error page, partial response, or corrupted payload).
- **Recommended fix (no code):**
  - Wrap `response.json()` in a try/except for `json.JSONDecodeError` and either fall back to individual embeddings or return `None` entries when `strict=False`.
- **Tests/Verification:**
  - Add a test that mocks a 200 response with invalid JSON and asserts fallback behavior in non-strict mode.

### CR-0004: Timeout metadata flags never set
- **Severity:** Low
- **Category:** Bug
- **Component:** Timeout utilities
- **Location:** src/agentic_cba_indicators/tools/_timeout.py:62-82
- **Evidence:**
  - `wrapper.__tool_timeout_seconds__` and `wrapper.__tool_timeout_wrapped__` are assigned *after* `return future.result(...)`, which exits the function before the assignments execute.
- **Impact:**
  - Any introspection relying on these metadata flags will incorrectly conclude the function is not wrapped or has no timeout.
- **Reproduction/Trigger:**
  - Decorate a tool with `@timeout(30)` and inspect `__tool_timeout_seconds__` after a successful call; it will be missing.
- **Recommended fix (no code):**
  - Set metadata on the wrapper at decoration time (inside `decorator()` but outside `wrapper()`), or set before calling `future.result()`.
- **Tests/Verification:**
  - Add a unit test that checks metadata presence immediately after decoration and after a call.

### CR-0005: Timed-out tools keep running in background threads
- **Severity:** Medium
- **Category:** Reliability
- **Component:** Timeout utilities
- **Location:** src/agentic_cba_indicators/tools/_timeout.py:65-78
- **Evidence:**
  - On timeout, the code calls `future.cancel()` but cannot terminate the underlying thread running the tool.
- **Impact:**
  - Timed-out tool calls can continue executing (potentially with side effects). Over time, hung calls can saturate the executor (max 4 workers), blocking subsequent tool calls and causing perceived outages.
- **Reproduction/Trigger:**
  - Use a tool that blocks indefinitely; repeated calls will exhaust the executor despite timeouts being raised.
- **Recommended fix (no code):**
  - Consider process-based timeouts for truly cancellable execution, or redesign tools to be cooperatively cancellable. At minimum, add monitoring/metrics and a fallback to a fresh executor after repeated timeouts.
- **Tests/Verification:**
  - Stress test with a tool that sleeps longer than timeout and validate executor capacity doesn’t degrade permanently.

### CR-0006: Logging setup not invoked at entry points
- **Severity:** Medium
- **Category:** Config/Build
- **Component:** CLI/UI logging
- **Location:** src/agentic_cba_indicators/cli.py:248-322; src/agentic_cba_indicators/ui.py:400-520; src/agentic_cba_indicators/logging_config.py:1-29
- **Evidence:**
  - `logging_config` explicitly instructs calling `setup_logging()` at entry points, but CLI/UI never invoke it.
- **Impact:**
  - Logging stays at default root configuration; JSON logging, correlation ID injection, and structured logging configuration are effectively inactive in normal runs. This undermines observability and audit correlation.
- **Reproduction/Trigger:**
  - Run `agentic-cba` or `agentic-cba-ui` with `AGENTIC_CBA_LOG_FORMAT=json` and observe no JSON output or correlation ID fields.
- **Recommended fix (no code):**
  - Call `setup_logging()` early in CLI `main()` and UI `main()` before agent creation. Consider adding a CLI flag for log level/format overrides.
- **Tests/Verification:**
  - Add an integration test that runs the CLI/UI entry points with env vars set and validates log format and correlation IDs.

### CR-0007: `setup_logging()` docs mention non-existent `force`
- **Severity:** Low
- **Category:** Docs mismatch
- **Component:** Logging config
- **Location:** src/agentic_cba_indicators/logging_config.py:224-229
- **Evidence:**
  - Docstring states “Subsequent calls are no-ops unless force=True,” but the function signature has no `force` parameter.
- **Impact:**
  - Contributors may assume a `force` argument exists and attempt to use it, causing confusion or silent misconfiguration.
- **Reproduction/Trigger:**
  - Read docstring or attempt to call `setup_logging(force=True)`.
- **Recommended fix (no code):**
  - Either implement a `force` parameter or remove the docstring reference.
- **Tests/Verification:**
  - Update docstring tests (if any) or add a simple unit test asserting the function signature.

## Cross-cutting concerns
- **Observability:** Logging is well designed, but not wired into runtime entry points (CR-0006). Correlation IDs exist but are not emitted without setup.
- **API consistency:** Provider configuration is not consistently applied (CR-0001, CR-0002). Documented options must match runtime behavior.
- **Reliability:** Timeout behavior prevents blocking responses but does not stop execution (CR-0005). Batch embedding path lacks defensive JSON handling (CR-0003).
- **Config and deployment posture:** No issues found beyond logging setup and parameter propagation.
- **Testing strategy gaps:** No tests currently enforce prompt selection parity between CLI and UI, or JSON decode handling for batch embeddings.

## Appendix
### Questionable areas needing human confirmation
- **Timeout cancellation side effects:** Confirm whether tool functions have side effects that must be prevented when timeouts occur. Evidence would be tool-specific mutation paths or external requests that should be cancelled.
- **Embedding API stability:** If Ollama is known to return non-JSON responses under specific conditions, confirm with logs; otherwise treat CR-0003 as a defensive hardening item.

### Hypotheses
- **Hypothesis:** The UI is intended to mirror CLI prompt selection but was left default. Evidence: product requirements or UX docs indicating prompt selection should be configurable in UI.
- **Hypothesis:** Gemini `top_p` was intended to be supported. Evidence: product requirements or prior commits showing `top_p` propagation.

## Severity rubric (apply consistently)
- **Blocker:** prevents build/deploy/run; data loss; critical security issue; core feature unusable
- **High:** frequent runtime errors; serious correctness bugs; authz/authn weakness; major reliability risk
- **Medium:** partial feature breakage; edge-case correctness issues; performance pitfalls
- **Low:** minor defects; confusing API; maintainability issues that could become bugs
