# Custom tools for weather, climate, and socio-economic data
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

__all__ = [
    # Weather & Climate
    "get_current_weather",
    "get_weather_forecast",
    "get_climate_data",
    "get_historical_climate",
    # Agricultural Climate (NASA POWER)
    "get_agricultural_climate",
    "get_solar_radiation",
    "get_evapotranspiration",
    # Soil Properties (ISRIC SoilGrids)
    "get_soil_properties",
    "get_soil_carbon",
    "get_soil_texture",
    # Biodiversity (GBIF)
    "search_species",
    "get_species_occurrences",
    "get_biodiversity_summary",
    "get_species_taxonomy",
    # Labor Statistics (ILO)
    "get_labor_indicators",
    "get_employment_by_gender",
    "get_labor_time_series",
    "search_labor_indicators",
    # Gender Statistics (World Bank)
    "get_gender_indicators",
    "compare_gender_gaps",
    "get_gender_time_series",
    "search_gender_indicators",
    # Agriculture & Forestry (FAO)
    "get_forest_statistics",
    "get_crop_production",
    "get_land_use",
    "search_fao_indicators",
    # Commodity Markets (USDA FAS)
    "get_commodity_production",
    "get_commodity_trade",
    "compare_commodity_producers",
    "list_fas_commodities",
    "search_commodity_data",
    # SDG Indicators (UN SDG API)
    "get_sdg_progress",
    "search_sdg_indicators",
    "get_sdg_series_data",
    "get_sdg_for_cba_principle",
    # Socio-economic
    "get_country_indicators",
    "get_world_bank_data",
    # Knowledge Base (CBA ME Indicators)
    "search_indicators",
    "search_methods",
    "get_indicator_details",
    "list_knowledge_base_stats",
    # Indicator Selection Tools
    "find_indicators_by_principle",
    "find_indicators_by_class",
    "find_indicators_by_measurement_approach",
    "find_feasible_methods",
    "list_indicators_by_component",
    "list_available_classes",
    "compare_indicators",
    "export_indicator_selection",
    # Use Cases
    "search_usecases",
    "get_usecase_details",
    "get_usecases_by_indicator",
]
