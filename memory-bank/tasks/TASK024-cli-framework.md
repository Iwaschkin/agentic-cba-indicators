# [TASK024] - Use CLI Framework for Argument Parsing

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P2 - Medium
**Phase:** 6

## Original Request
Address P2-08: Manual argument parsing in `cli.py` instead of using argparse or click.

## Thought Process
The `cli.py` previously used manual `sys.argv` parsing which:
1. Required manual help text implementation
2. Had no validation of arguments
3. No consistent error handling for bad arguments
4. Was harder to extend with new options

Solution: Use `argparse` (stdlib) for proper CLI handling since it's already available in the standard library.

## Implementation Plan
- [x] Add argparse to cli.py
- [x] Define arguments: --provider, --config
- [x] Add help text and descriptions
- [x] Add choices validation for --provider
- [x] Verify CLI works correctly

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 24.1 | Set up argparse | Complete | 2025-01-17 | With RawDescriptionHelpFormatter |
| 24.2 | Define --provider argument | Complete | 2025-01-17 | With choices validation |
| 24.3 | Define --config argument | Complete | 2025-01-17 | With metavar PATH |
| 24.4 | Add help text | Complete | 2025-01-17 | Includes examples in epilog |
| 24.5 | Test CLI | Complete | 2025-01-17 | Help and validation working |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-08
- Replaced manual argument parsing (25+ lines) with argparse:
  - Added `argparse.ArgumentParser` with description and epilog
  - Defined `--config` with PATH metavar
  - Defined `--provider` with choices=['ollama', 'anthropic', 'openai', 'bedrock', 'gemini']
  - Used RawDescriptionHelpFormatter for examples
- Benefits gained:
  - Automatic `-h` / `--help` generation
  - Automatic validation of provider choices
  - Consistent error messages for invalid arguments
  - Easier to extend with new options
- Verified with `agentic-cba --help` and invalid provider test
- All 35 tests passing
- Task complete

## Before/After

### Before (manual parsing)
```python
for arg in sys.argv[1:]:
    if arg.startswith("--config="):
        config_path = arg.split("=")[1]
    elif arg.startswith("--provider="):
        provider_override = arg.split("=")[1]
    elif arg in ["-h", "--help"]:
        print("Usage: agentic-cba [OPTIONS]")
        # ... 15 more lines of manual help text
```

### After (argparse)
```python
parser = argparse.ArgumentParser(
    prog="agentic-cba",
    description="CBA Indicators & Sustainable Agriculture Data Assistant",
    epilog="Examples:\n  ...",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--config", metavar="PATH", help="...")
parser.add_argument("--provider", metavar="NAME", choices=[...], help="...")
args = parser.parse_args()
```

## Acceptance Criteria
- [x] CLI uses argparse for argument parsing
- [x] Help text available via --help
- [x] Invalid provider choices rejected with helpful error
- [x] Tests pass
### 2025-01-17
- Task created from code review finding P2-08
- Assigned to Phase 6 (Configuration)

## Acceptance Criteria
- [ ] --help shows usage information
- [ ] Arguments properly validated
- [ ] Error messages helpful
- [ ] Documentation updated
- [ ] CLI tests pass
