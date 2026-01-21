"""
MCP Server for Agentic CBA Indicators.

Exposes all tools via Model Context Protocol (MCP) using stdio transport.
Tools are wrapped with timeout, audit logging, and metrics before registration.

Entry point: agentic-cba-mcp (defined in pyproject.toml)

Usage:
    The CLI and UI connect to this server as an MCPClient subprocess.
    The server is stateless - all configuration is handled client-side.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from agentic_cba_indicators.logging_config import setup_logging

# Import raw tools (before wrapping) and wrapping function
from agentic_cba_indicators.tools import (
    compare_commodity_producers,
    compare_gender_gaps,
    compare_indicators,
    export_indicator_selection,
    find_feasible_methods,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_indicators_by_principle,
    get_agricultural_climate,
    get_biodiversity_summary,
    get_climate_data,
    get_commodity_production,
    get_commodity_trade,
    get_country_indicators,
    get_crop_production,
    get_current_weather,
    get_employment_by_gender,
    get_evapotranspiration,
    get_forest_carbon_stock,
    get_forest_extent,
    get_forest_statistics,
    get_gender_indicators,
    get_gender_time_series,
    get_historical_climate,
    get_indicator_details,
    get_knowledge_version,
    get_labor_indicators,
    get_labor_time_series,
    get_land_use,
    get_sdg_for_cba_principle,
    get_sdg_progress,
    get_sdg_series_data,
    get_soil_carbon,
    get_soil_properties,
    get_soil_texture,
    get_solar_radiation,
    get_species_occurrences,
    get_species_taxonomy,
    get_tree_cover_loss_by_driver,
    get_tree_cover_loss_trends,
    get_usecase_details,
    get_usecases_by_indicator,
    get_weather_forecast,
    get_world_bank_data,
    list_available_classes,
    list_fas_commodities,
    list_indicators_by_component,
    list_knowledge_base_stats,
    run_tools_parallel,
    search_commodity_data,
    search_fao_indicators,
    search_gender_indicators,
    search_indicators,
    search_labor_indicators,
    search_methods,
    search_sdg_indicators,
    search_species,
    search_usecases,
)

# Server instructions for MCP clients
_SERVER_INSTRUCTIONS = """
Agentic CBA Indicators MCP Server

This server provides tools for sustainable agriculture data access and CBA indicator exploration.

Tool Categories:
- Weather & Climate: get_current_weather, get_weather_forecast, get_climate_data, get_historical_climate
- Agricultural Climate (NASA POWER): get_agricultural_climate, get_solar_radiation, get_evapotranspiration
- Soil Properties (ISRIC SoilGrids): get_soil_properties, get_soil_carbon, get_soil_texture
- Biodiversity (GBIF): search_species, get_species_occurrences, get_biodiversity_summary, get_species_taxonomy
- Forestry (Global Forest Watch): get_tree_cover_loss_trends, get_tree_cover_loss_by_driver, get_forest_carbon_stock, get_forest_extent
- Agriculture (FAO): get_forest_statistics, get_crop_production, get_land_use, search_fao_indicators
- Commodity Markets (USDA FAS): get_commodity_production, get_commodity_trade, compare_commodity_producers, list_fas_commodities
- Labor Statistics (ILO): get_labor_indicators, get_employment_by_gender, get_labor_time_series, search_labor_indicators
- Gender Statistics (World Bank): get_gender_indicators, compare_gender_gaps, get_gender_time_series, search_gender_indicators
- SDG Indicators (UN): get_sdg_progress, search_sdg_indicators, get_sdg_series_data, get_sdg_for_cba_principle
- Socio-Economic: get_country_indicators, get_world_bank_data
- CBA Knowledge Base: search_indicators, search_methods, get_indicator_details, find_indicators_by_principle,
  find_indicators_by_class, find_feasible_methods, list_indicators_by_component, list_available_classes,
  compare_indicators, export_indicator_selection, list_knowledge_base_stats, get_knowledge_version
- Use Cases: search_usecases, get_usecase_details, get_usecases_by_indicator
- Utility: run_tools_parallel

Indicator Selection Workflow:
1. Start with search_usecases() for project context
2. Extract indicator IDs from matched use cases
3. Expand with search_indicators() for additional candidates
4. Evaluate with get_indicator_details() for each
5. Find methods with search_methods() and find_feasible_methods()
6. Generate report with export_indicator_selection()
"""

# All tools to register (excluding help tools - MCP provides native discovery)
_ALL_TOOLS = [
    # --- Weather & Climate ---
    get_current_weather,
    get_weather_forecast,
    get_climate_data,
    get_historical_climate,
    # --- Agricultural Climate (NASA POWER) ---
    get_agricultural_climate,
    get_solar_radiation,
    get_evapotranspiration,
    # --- Soil Properties (ISRIC SoilGrids) ---
    get_soil_properties,
    get_soil_carbon,
    get_soil_texture,
    # --- Biodiversity (GBIF) ---
    search_species,
    get_species_occurrences,
    get_biodiversity_summary,
    get_species_taxonomy,
    # --- Forestry (Global Forest Watch) ---
    get_tree_cover_loss_trends,
    get_tree_cover_loss_by_driver,
    get_forest_carbon_stock,
    get_forest_extent,
    # --- Agriculture (FAO) ---
    get_forest_statistics,
    get_crop_production,
    get_land_use,
    search_fao_indicators,
    # --- Commodity Markets (USDA FAS) ---
    get_commodity_production,
    get_commodity_trade,
    compare_commodity_producers,
    list_fas_commodities,
    search_commodity_data,
    # --- Labor Statistics (ILO) ---
    get_labor_indicators,
    get_employment_by_gender,
    get_labor_time_series,
    search_labor_indicators,
    # --- Gender Statistics (World Bank) ---
    get_gender_indicators,
    compare_gender_gaps,
    get_gender_time_series,
    search_gender_indicators,
    # --- SDG Indicators (UN) ---
    get_sdg_progress,
    search_sdg_indicators,
    get_sdg_series_data,
    get_sdg_for_cba_principle,
    # --- Socio-Economic ---
    get_country_indicators,
    get_world_bank_data,
    # --- CBA Knowledge Base ---
    search_indicators,
    search_methods,
    get_indicator_details,
    list_knowledge_base_stats,
    get_knowledge_version,
    find_indicators_by_principle,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_feasible_methods,
    list_indicators_by_component,
    list_available_classes,
    compare_indicators,
    export_indicator_selection,
    # --- Use Cases ---
    search_usecases,
    get_usecase_details,
    get_usecases_by_indicator,
    # --- Utility ---
    run_tools_parallel,
]

# Create MCP server instance
mcp = FastMCP(
    "Agentic CBA Indicators",
    instructions=_SERVER_INSTRUCTIONS,
)


def _register_tools() -> None:
    """Register all tools with the MCP server.

    Tools are already wrapped with timeout/audit/metrics from the tools module.
    This function converts them to MCP tool format.
    """
    for tool_func in _ALL_TOOLS:
        # FastMCP's @mcp.tool() decorator extracts function signature and docstring
        # We use the function directly since tools are already @tool decorated
        mcp.tool()(tool_func)


def run_server() -> None:
    """Entry point for the MCP server.

    Starts the server with stdio transport for subprocess communication.
    """
    setup_logging()
    _register_tools()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
