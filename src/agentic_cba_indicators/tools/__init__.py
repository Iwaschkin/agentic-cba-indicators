"""Custom tools for weather, climate, and socio-economic data."""

from __future__ import annotations

import functools
import inspect
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from agentic_cba_indicators.audit import log_tool_invocation
from agentic_cba_indicators.observability import instrument_tool

# Internal help tools (for agent self-discovery)
# These are included in tool sets for agent access but hidden from users
from ._help import describe_tool as describe_tool
from ._help import list_tools as list_tools
from ._help import list_tools_by_category as list_tools_by_category
from ._help import search_tools as search_tools
from ._help import set_active_tools as set_active_tools
from ._http import classify_error
from ._parallel import run_tools_parallel as run_tools_parallel
from ._timeout import timeout
from .agriculture import (
    get_crop_production,
    get_forest_statistics,
    get_land_use,
    search_fao_indicators,
)
from .biodiversity import (
    get_biodiversity_summary,
    get_species_occurrences,
    get_species_taxonomy,
    search_species,
)
from .climate import get_climate_data, get_historical_climate
from .commodities import (
    compare_commodity_producers,
    get_commodity_production,
    get_commodity_trade,
    list_fas_commodities,
    search_commodity_data,
)
from .forestry import (
    get_forest_carbon_stock,
    get_forest_extent,
    get_tree_cover_loss_by_driver,
    get_tree_cover_loss_trends,
)
from .gender import (
    compare_gender_gaps,
    get_gender_indicators,
    get_gender_time_series,
    search_gender_indicators,
)
from .knowledge_base import (
    compare_indicators,
    export_indicator_selection,
    find_feasible_methods,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_indicators_by_principle,
    get_indicator_details,
    get_knowledge_version,
    get_usecase_details,
    get_usecases_by_indicator,
    list_available_classes,
    list_indicators_by_component,
    list_knowledge_base_stats,
    search_indicators,
    search_methods,
    search_usecases,
)
from .labor import (
    get_employment_by_gender,
    get_labor_indicators,
    get_labor_time_series,
    search_labor_indicators,
)
from .nasa_power import (
    get_agricultural_climate,
    get_evapotranspiration,
    get_solar_radiation,
)
from .sdg import (
    get_sdg_for_cba_principle,
    get_sdg_progress,
    get_sdg_series_data,
    search_sdg_indicators,
)
from .socioeconomic import get_country_indicators, get_world_bank_data
from .soilgrids import get_soil_carbon, get_soil_properties, get_soil_texture
from .weather import get_current_weather, get_weather_forecast

_DEFAULT_TOOL_TIMEOUT_SECONDS = float(os.environ.get("TOOL_DEFAULT_TIMEOUT", "30"))


def _extract_params(
    func: Callable[..., str], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Extract parameters for audit logging, excluding ToolContext."""
    try:
        signature = inspect.signature(func)
        bound = signature.bind_partial(*args, **kwargs)
        params = dict(bound.arguments)
    except (TypeError, ValueError):
        params = {"args": args, "kwargs": kwargs}

    params.pop("tool_context", None)
    return params


def _wrap_with_audit(func: Callable[..., str]) -> Callable[..., str]:
    """Wrap a tool with audit logging."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        start_time = time.perf_counter()
        success = True
        error_message: str | None = None
        result_text: str | None = None

        try:
            result = func(*args, **kwargs)
            result_text = result if isinstance(result, str) else str(result)
            return result
        except Exception as exc:
            success = False
            category = classify_error(exc).value
            error_message = f"[category: {category}] {exc!s}"
            raise
        finally:
            latency = time.perf_counter() - start_time
            params = _extract_params(func, args, kwargs)
            log_tool_invocation(
                tool_name=getattr(func, "__name__", str(func)),
                params=params,
                result=result_text,
                success=success,
                latency=latency,
                error=error_message,
            )

    return wrapper


def _wrap_tool(tool_func: Callable[..., str]) -> Callable[..., str]:
    """Apply timeout, audit logging, and metrics to a tool function."""
    if getattr(tool_func, "__agentic_tool_wrapped__", False):
        return tool_func

    wrapped = tool_func

    if not getattr(wrapped, "__tool_timeout_wrapped__", False):
        wrapped = timeout(_DEFAULT_TOOL_TIMEOUT_SECONDS)(wrapped)

    wrapped = _wrap_with_audit(wrapped)
    wrapped = instrument_tool(wrapped)

    wrapped.__agentic_tool_wrapped__ = True  # type: ignore[attr-defined]
    return wrapped


def _prepare_toolset(
    tools: tuple[Callable[..., str], ...],
) -> tuple[Callable[..., str], ...]:
    return tuple(_wrap_tool(tool) for tool in tools)


__all__ = [
    "FULL_TOOLS",
    "REDUCED_TOOLS",
    "compare_commodity_producers",
    "compare_gender_gaps",
    "compare_indicators",
    "describe_tool",
    "export_indicator_selection",
    "find_feasible_methods",
    "find_indicators_by_class",
    "find_indicators_by_measurement_approach",
    "find_indicators_by_principle",
    "get_agricultural_climate",
    "get_biodiversity_summary",
    "get_climate_data",
    "get_commodity_production",
    "get_commodity_trade",
    "get_country_indicators",
    "get_crop_production",
    "get_current_weather",
    "get_employment_by_gender",
    "get_evapotranspiration",
    "get_forest_carbon_stock",
    "get_forest_extent",
    "get_forest_statistics",
    "get_gender_indicators",
    "get_gender_time_series",
    "get_historical_climate",
    "get_indicator_details",
    "get_knowledge_version",
    "get_labor_indicators",
    "get_labor_time_series",
    "get_land_use",
    "get_sdg_for_cba_principle",
    "get_sdg_progress",
    "get_sdg_series_data",
    "get_soil_carbon",
    "get_soil_properties",
    "get_soil_texture",
    "get_solar_radiation",
    "get_species_occurrences",
    "get_species_taxonomy",
    "get_tree_cover_loss_by_driver",
    "get_tree_cover_loss_trends",
    "get_usecase_details",
    "get_usecases_by_indicator",
    "get_weather_forecast",
    "get_world_bank_data",
    "list_available_classes",
    "list_fas_commodities",
    "list_indicators_by_component",
    "list_knowledge_base_stats",
    "list_tools",
    "list_tools_by_category",
    "run_tools_parallel",
    "search_commodity_data",
    "search_fao_indicators",
    "search_gender_indicators",
    "search_indicators",
    "search_labor_indicators",
    "search_methods",
    "search_sdg_indicators",
    "search_species",
    "search_tools",
    "search_usecases",
    "set_active_tools",
]


# Reduced tool set (23 tools) - good for most models
_REDUCED_TOOLS_RAW = (
    # Internal Help (agent self-discovery)
    list_tools,
    list_tools_by_category,
    search_tools,
    describe_tool,
    run_tools_parallel,
    # Weather
    get_current_weather,
    get_weather_forecast,
    get_climate_data,
    # Soil
    get_soil_properties,
    get_soil_carbon,
    # Socio-economic
    get_country_indicators,
    get_world_bank_data,
    # Knowledge Base - Core
    search_indicators,
    search_methods,
    get_indicator_details,
    list_knowledge_base_stats,
    get_knowledge_version,
    # Indicator Selection
    find_indicators_by_principle,
    find_indicators_by_class,
    find_feasible_methods,
    list_available_classes,
    compare_indicators,
    export_indicator_selection,
    # Use Cases
    search_usecases,
)


# Full tool set (61 tools) - for models with large context
_FULL_TOOLS_RAW = (
    # Internal Help (agent self-discovery)
    list_tools,
    list_tools_by_category,
    search_tools,
    describe_tool,
    run_tools_parallel,
    # Weather & Climate
    get_current_weather,
    get_weather_forecast,
    get_climate_data,
    get_historical_climate,
    # Agricultural Climate (NASA POWER)
    get_agricultural_climate,
    get_solar_radiation,
    get_evapotranspiration,
    # Soil Properties (ISRIC SoilGrids)
    get_soil_properties,
    get_soil_carbon,
    get_soil_texture,
    search_species,  # GBIF
    get_species_occurrences,
    get_biodiversity_summary,
    get_species_taxonomy,
    # Labor Statistics (ILO)
    get_labor_indicators,
    get_employment_by_gender,
    get_labor_time_series,
    search_labor_indicators,
    # Gender Statistics (World Bank)
    get_gender_indicators,
    compare_gender_gaps,
    get_gender_time_series,
    search_gender_indicators,
    get_forest_statistics,  # FAO Agriculture & Forestry
    get_crop_production,
    get_land_use,
    search_fao_indicators,
    # Commodity Markets (USDA FAS)
    get_commodity_production,
    get_commodity_trade,
    compare_commodity_producers,
    list_fas_commodities,
    search_commodity_data,
    # SDG Indicators (UN SDG API)
    get_sdg_progress,
    search_sdg_indicators,
    get_sdg_series_data,
    get_sdg_for_cba_principle,
    # Forestry / Global Forest Watch
    get_tree_cover_loss_trends,
    get_tree_cover_loss_by_driver,
    get_forest_carbon_stock,
    get_forest_extent,
    # Socio-economic
    get_country_indicators,
    get_world_bank_data,
    # Knowledge Base (CBA ME Indicators)
    search_indicators,
    search_methods,
    get_indicator_details,
    list_knowledge_base_stats,
    get_knowledge_version,
    # Indicator Selection Tools
    find_indicators_by_principle,
    find_indicators_by_class,
    find_indicators_by_measurement_approach,
    find_feasible_methods,
    list_indicators_by_component,
    list_available_classes,
    compare_indicators,
    export_indicator_selection,
    # Use Cases
    search_usecases,
    get_usecase_details,
    get_usecases_by_indicator,
)


REDUCED_TOOLS = _prepare_toolset(_REDUCED_TOOLS_RAW)
FULL_TOOLS = _prepare_toolset(_FULL_TOOLS_RAW)
