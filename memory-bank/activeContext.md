# Active Context

## Current Focus
**GFW FORESTRY TOOLS COMPLETE** - Added 4 Global Forest Watch tools for forest state monitoring.

## Recent Changes
- Created `forestry.py` module with 4 GFW tools
- Added validation helpers for country codes, window years, radius, coordinates
- Implemented geostore creation for point-radius queries
- Integrated tools into exports (56 tools in FULL_TOOLS)
- Added 35 unit tests for forestry module (133 total tests)

## Key Deliverables
- `src/agentic_cba_indicators/tools/forestry.py` - 4 GFW tools
- `tests/test_tools_forestry.py` - 35 tests
- Updated `tools/__init__.py` - Exports for new tools
- `docs/dev/plan-gfw-forestry-tools.md` - Implementation plan

## Design Decisions
- Focus on state monitoring, not real-time alerts
- 5/10 year windows for trend analysis (M&E standards)
- 30% canopy threshold (GFW default)
- On-the-fly geostore creation (no caching)
- Uses require_api_key("gfw") for authentication

## Next Steps
- Consider additional data sources from External Data Source Integration Plan
- Monitor tool usage with real GFW API key
- Consider adding geostore caching if performance becomes issue
