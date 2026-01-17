# Tools Reference

Complete documentation of all available tools in the Agentic CBA Indicators system, organized by functional category.

## Table of Contents

- [Weather \& Climate](#weather--climate)
- [Soil Properties](#soil-properties)
- [Biodiversity \& Species](#biodiversity--species)
- [Forestry \& Forest Watch](#forestry--forest-watch)
- [Agricultural Data](#agricultural-data)
- [Labor Statistics](#labor-statistics)
- [Gender Statistics](#gender-statistics)
- [SDG Indicators](#sdg-indicators)
- [Commodity Markets](#commodity-markets)
- [Socio-economic Data](#socio-economic-data)
- [CBA Knowledge Base](#cba-knowledge-base)
- [Internal Help Tools](#internal-help-tools)

---

## Weather & Climate

Weather, climate, and agricultural meteorology tools using free APIs.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| Open-Meteo | [open-meteo.com/en/docs](https://open-meteo.com/en/docs) | No |
| NASA POWER | [power.larc.nasa.gov/docs](https://power.larc.nasa.gov/docs/) | No |

### Tools (7)

#### `get_current_weather`

Get current weather conditions for a city.

**Parameters:**
- `city` (str): Name of the city (e.g., "London", "New York", "Tokyo")

**Returns:** Current weather including temperature, humidity, wind, and conditions.

---

#### `get_weather_forecast`

Get weather forecast for a city.

**Parameters:**
- `city` (str): Name of the city
- `days` (int, optional): Number of days to forecast (1-16, default 7)

**Returns:** Weather forecast with daily high/low temperatures and conditions.

---

#### `get_climate_data`

Get climate normals (30-year averages) for a city. Shows monthly average temperatures, precipitation, and other climate indicators.

**Parameters:**
- `city` (str): Name of the city

**Returns:** Climate normals including monthly temperatures and precipitation.

---

#### `get_historical_climate`

Get historical weather data for a specific date range.

**Parameters:**
- `city` (str): Name of the city
- `start_date` (str): Start date (YYYY-MM-DD)
- `end_date` (str): End date (YYYY-MM-DD)

**Returns:** Historical weather data for the specified period.

---

#### `get_agricultural_climate`

Get agricultural climate parameters from NASA POWER for a location. Includes temperature, precipitation, humidity, and wind data optimized for agricultural applications.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `start_date` (str): Start date (YYYY-MM-DD), max 2 years ago
- `end_date` (str): End date (YYYY-MM-DD)

**Returns:** Daily agricultural climate parameters from NASA POWER.

---

#### `get_solar_radiation`

Get solar radiation and photosynthetically active radiation (PAR) data from NASA POWER. Useful for crop growth modeling and solar energy assessments.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `start_date` (str): Start date (YYYY-MM-DD)
- `end_date` (str): End date (YYYY-MM-DD)

**Returns:** Daily solar radiation metrics including PAR and UV index.

---

#### `get_evapotranspiration`

Calculate reference evapotranspiration (ET₀) using the FAO Penman-Monteith method. Uses NASA POWER data for the calculation.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `start_date` (str): Start date (YYYY-MM-DD)
- `end_date` (str): End date (YYYY-MM-DD)

**Returns:** Daily reference evapotranspiration (ET₀) values in mm/day.

---

## Soil Properties

Soil property data from ISRIC SoilGrids at 250m resolution.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| ISRIC SoilGrids | [rest.isric.org/soilgrids/v2.0/docs](https://rest.isric.org/soilgrids/v2.0/docs) | No |

### Tools (3)

#### `get_soil_properties`

Get comprehensive soil properties for a location from ISRIC SoilGrids. Provides data for multiple depth layers (0-200cm).

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates

**Returns:** Soil properties including organic carbon, pH, texture (clay/sand/silt), bulk density, CEC, and nitrogen content at various depths.

---

#### `get_soil_carbon`

Get detailed soil organic carbon data for a location. Includes carbon stocks and sequestration potential estimates.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `depth` (str, optional): Specific depth layer (e.g., "0-30cm") or "all" (default)

**Returns:** Soil organic carbon content (g/kg) and density (kg/m³) by depth.

---

#### `get_soil_texture`

Get soil texture classification and particle size distribution. Returns USDA texture class and clay/sand/silt percentages.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates

**Returns:** USDA soil texture class and particle size distribution at various depths.

---

## Biodiversity & Species

Species occurrence data and biodiversity metrics from GBIF.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| GBIF (Global Biodiversity Information Facility) | [techdocs.gbif.org/en/openapi](https://techdocs.gbif.org/en/openapi/) | No |

### Tools (4)

#### `search_species`

Search for species by common or scientific name.

**Parameters:**
- `query` (str): Species name to search (common or scientific)
- `limit` (int, optional): Maximum results (default 10, max 50)

**Returns:** Matching species with scientific names, common names, and taxonomic classification.

---

#### `get_species_occurrences`

Get species occurrence records for a location. Returns georeferenced observations from museums, citizen science, and research.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `radius_km` (float, optional): Search radius in km (default 50, max 200)
- `species` (str, optional): Filter by species name

**Returns:** Species occurrences with dates, coordinates, and data sources.

---

#### `get_biodiversity_summary`

Get a biodiversity summary for a location including species richness and taxonomic breakdown.

**Parameters:**
- `location` (str): City name or "lat,lon" coordinates
- `radius_km` (float, optional): Search radius (default 50, max 200)

**Returns:** Biodiversity metrics including species counts by taxonomic group.

---

#### `get_species_taxonomy`

Get detailed taxonomic information for a species.

**Parameters:**
- `species` (str): Scientific or common name

**Returns:** Full taxonomic hierarchy (kingdom to species) and IUCN conservation status if available.

---

## Forestry & Forest Watch

Forest monitoring data from Global Forest Watch.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| Global Forest Watch | [data-api.globalforestwatch.org/docs](https://data-api.globalforestwatch.org/docs) | Yes (free) |

Get a free API key from [GFW Data API](https://data-api.globalforestwatch.org/). Set the environment variable `GFW_API_KEY`.

### Tools (4)

#### `get_tree_cover_loss_trends`

Get annual tree cover loss trends for a country over a specified time window. Essential for M&E baselines and tracking deforestation.

**Parameters:**
- `country` (str): Country name or ISO 3166-1 alpha-3 code
- `window_years` (int, optional): Analysis window - 5 or 10 years (default 10)
- `canopy_threshold` (int, optional): Minimum canopy cover % (default 30)

**Returns:** Annual tree cover loss in hectares with trend analysis.

---

#### `get_tree_cover_loss_by_driver`

Analyze tree cover loss by driver category for a country. Identifies causes: commodity-driven deforestation, shifting agriculture, forestry, wildfire, or urbanization.

**Parameters:**
- `country` (str): Country name or ISO code
- `start_year` (int, optional): Start year (default 2001)
- `end_year` (int, optional): End year (default current year - 1)

**Returns:** Tree cover loss breakdown by driver category with percentages.

---

#### `get_forest_carbon_stock`

Get forest carbon stock estimates for a country. Includes above-ground, below-ground, and total carbon density.

**Parameters:**
- `country` (str): Country name or ISO code

**Returns:** Carbon stock estimates in Mg C/ha (megatons carbon per hectare).

---

#### `get_forest_extent`

Get current forest extent and historical changes for a country. Shows total forest area, tree cover percentage, and changes over time.

**Parameters:**
- `country` (str): Country name or ISO code
- `baseline_year` (int, optional): Baseline year for comparison (default 2000)

**Returns:** Forest extent in hectares, percent of land area, and change since baseline.

---

## Agricultural Data

Agricultural production, trade, and land use data from FAO.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| FAOSTAT | [fao.org/faostat/en/#data](https://www.fao.org/faostat/en/#data) | No |

### Tools (4)

#### `get_forest_statistics`

Get FAO forest statistics for a country including forest area, change rates, and carbon stocks.

**Parameters:**
- `country` (str): Country name or ISO code
- `indicator` (str, optional): Specific indicator (forest_area, deforestation, carbon_stock, etc.)

**Returns:** Forest statistics from FAO Global Forest Resources Assessment.

---

#### `get_crop_production`

Get crop production statistics for a country from FAOSTAT.

**Parameters:**
- `country` (str): Country name or ISO code
- `crop` (str): Crop name (e.g., "wheat", "rice", "cotton")
- `years` (int, optional): Number of recent years (default 5)

**Returns:** Production quantity, area harvested, and yield data.

---

#### `get_land_use`

Get land use statistics for a country showing agricultural land, forest, and other categories.

**Parameters:**
- `country` (str): Country name or ISO code

**Returns:** Land use breakdown by category (agricultural, forest, other) in hectares.

---

#### `search_fao_indicators`

Search available FAO data indicators. Find relevant indicators for agriculture, forestry, and land use.

**Parameters:**
- `query` (str): Search term (e.g., "forest", "crop", "land", "production")

**Returns:** Matching FAO indicators with codes and descriptions.

---

## Labor Statistics

Labor market indicators from ILO (International Labour Organization).

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| ILOSTAT | [rplumber.ilo.org](https://rplumber.ilo.org/) | No |

### Tools (4)

#### `get_labor_indicators`

Get key labor market indicators for a country including employment rates, unemployment, and informal employment.

**Parameters:**
- `country` (str): Country name or ISO code
- `indicators` (list, optional): Specific indicators to retrieve

**Returns:** Labor statistics including employment rate, unemployment, labor force participation, and informal employment.

---

#### `get_employment_by_gender`

Get employment statistics disaggregated by gender for a country.

**Parameters:**
- `country` (str): Country name or ISO code

**Returns:** Employment metrics comparing male and female participation, unemployment, and wage gaps.

---

#### `get_labor_time_series`

Get historical time series for a labor indicator.

**Parameters:**
- `country` (str): Country name or ISO code
- `indicator` (str): Indicator name (e.g., "employment_rate", "unemployment_rate")
- `years` (int, optional): Number of years (default 10)

**Returns:** Annual time series data for the specified indicator.

---

#### `search_labor_indicators`

Search available ILO labor indicators by keyword.

**Parameters:**
- `query` (str): Search term (e.g., "wage", "youth", "agriculture")

**Returns:** Matching indicators with codes and descriptions.

---

## Gender Statistics

Gender-disaggregated indicators from World Bank Gender Data Portal.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| World Bank Gender Data | [datahelpdesk.worldbank.org](https://datahelpdesk.worldbank.org/knowledgebase/topics/125589) | No |

### Tools (4)

#### `get_gender_indicators`

Get gender indicators for a country across education, health, employment, and economic participation.

**Parameters:**
- `country` (str): Country name or ISO code
- `category` (str, optional): Filter by category (education, health, employment, economic)

**Returns:** Gender indicators with male/female comparisons and gender parity indices.

---

#### `compare_gender_gaps`

Compare gender gaps across multiple countries for a specific indicator.

**Parameters:**
- `countries` (list): List of country names or ISO codes
- `indicator` (str): Indicator to compare (e.g., "literacy", "labor_force_participation")

**Returns:** Cross-country comparison of gender gaps.

---

#### `get_gender_time_series`

Get historical time series for a gender indicator.

**Parameters:**
- `country` (str): Country name or ISO code
- `indicator` (str): Indicator name
- `years` (int, optional): Number of years (default 10)

**Returns:** Time series showing progress on gender equality.

---

#### `search_gender_indicators`

Search available gender indicators by keyword.

**Parameters:**
- `query` (str): Search term (e.g., "education", "maternal", "ownership")

**Returns:** Matching indicators with codes and descriptions.

---

## SDG Indicators

UN Sustainable Development Goals indicator data.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| UN SDG API | [unstats.un.org/sdgs/UNSDGAPIV5/swagger](https://unstats.un.org/sdgs/UNSDGAPIV5/swagger/) | No |

### Tools (4)

#### `get_sdg_progress`

Get SDG progress for a country across all 17 goals.

**Parameters:**
- `country` (str): Country name or ISO code

**Returns:** Progress summary for each SDG goal with key indicators.

---

#### `search_sdg_indicators`

Search SDG indicators by keyword or goal number.

**Parameters:**
- `query` (str): Search term or goal number (e.g., "poverty", "2" for Zero Hunger)

**Returns:** Matching SDG indicators with codes, descriptions, and goal mapping.

---

#### `get_sdg_series_data`

Get detailed data for a specific SDG indicator series.

**Parameters:**
- `country` (str): Country name or ISO code
- `series_code` (str): SDG series code (e.g., "SI_POV_DAY1")
- `years` (int, optional): Number of recent years (default 10)

**Returns:** Time series data for the specified SDG indicator.

---

#### `get_sdg_for_cba_principle`

Get relevant SDG indicators for a CBA principle. Maps CBA sustainability principles to corresponding SDG goals and indicators.

**Parameters:**
- `principle` (str): CBA principle number (1-7) or name

**Returns:** SDG goals and indicators relevant to the specified CBA principle.

---

## Commodity Markets

Commodity production and trade data from USDA Foreign Agricultural Service.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| USDA FAS PSD | [api.fas.usda.gov](https://api.fas.usda.gov) | Yes (free) |
| USDA FAS GATS | [api.fas.usda.gov](https://api.fas.usda.gov) | Yes (free) |

Get a free API key from [api.data.gov/signup](https://api.data.gov/signup/). Set the environment variable `USDA_FAS_API_KEY`.

### Tools (5)

#### `get_commodity_production`

Get production, supply, and distribution data for a commodity from USDA PSD database.

**Parameters:**
- `commodity` (str): Commodity name (cotton, corn, wheat, coffee, cocoa, etc.)
- `country` (str, optional): Country name or ISO code (default: global)
- `years` (int, optional): Number of years (default 5)

**Returns:** Production, exports, imports, consumption, and ending stocks.

---

#### `get_commodity_trade`

Get trade data for a commodity from USDA GATS database.

**Parameters:**
- `commodity` (str): Commodity name
- `country` (str): Country name or ISO code
- `partner` (str, optional): Trading partner country
- `years` (int, optional): Number of years (default 5)

**Returns:** Import/export volumes and values by partner country.

---

#### `compare_commodity_producers`

Compare production across top producing countries for a commodity.

**Parameters:**
- `commodity` (str): Commodity name
- `top_n` (int, optional): Number of top producers (default 10)

**Returns:** Ranking of producers by production volume with market share.

---

#### `list_fas_commodities`

List all available commodities in the USDA FAS database.

**Returns:** List of commodities with codes and names.

---

#### `search_commodity_data`

Search commodity data by keyword.

**Parameters:**
- `query` (str): Search term (e.g., "organic", "certified", "fair trade")

**Returns:** Matching commodities and data series.

---

## Socio-economic Data

General socio-economic indicators from World Bank and REST Countries.

### External Data Sources

| Source | API Documentation | API Key Required |
|--------|-------------------|------------------|
| World Bank WDI | [datahelpdesk.worldbank.org](https://datahelpdesk.worldbank.org/) | No |
| REST Countries | [restcountries.com](https://restcountries.com/) | No |

### Tools (2)

#### `get_country_indicators`

Get basic country information and socio-economic indicators including demographics, GDP, area, languages, and currencies.

**Parameters:**
- `country` (str): Country name or ISO code

**Returns:** Country profile with population, GDP, area, languages, region, and basic economic indicators.

---

#### `get_world_bank_data`

Get World Bank development indicators for a country.

**Parameters:**
- `country` (str): Country name or ISO code
- `indicator` (str): WDI indicator code (e.g., "NY.GDP.PCAP.CD" for GDP per capita)
- `years` (int, optional): Number of years (default 10)

**Returns:** Time series data for the specified indicator.

---

## CBA Knowledge Base

Local knowledge base tools for CBA ME Indicators using ChromaDB vector store.

### Data Sources

The knowledge base is populated from the CBA ME Indicators Excel workbook containing:
- **Indicators collection**: 224 indicators with principles, criteria, and measurement methods
- **Methods collection**: Measurement methods with accuracy, cost, and ease ratings
- **Use cases collection**: Example indicator selections from real projects

### Tools (15)

#### `search_indicators`

Search the CBA ME Indicators knowledge base for relevant indicators by topic (environmental, social, economic).

**Parameters:**
- `query` (str): Natural language search query
- `n_results` (int, optional): Number of results (default 5, max 20)

**Returns:** Matching indicators with components, classes, units, and principle coverage.

---

#### `search_methods`

Search for measurement methods in the CBA ME knowledge base.

**Parameters:**
- `query` (str): Search query about measurement methods
- `n_results` (int, optional): Number of results (default 5, max 20)

**Returns:** Methods with evaluation criteria (accuracy, ease, cost) and citations.

---

#### `get_indicator_details`

Get full details for a specific indicator by ID.

**Parameters:**
- `indicator_id` (int): The indicator ID number (1-224)

**Returns:** Complete indicator details including all measurement methods.

---

#### `list_knowledge_base_stats`

Show statistics about the knowledge base contents.

**Returns:** Summary of indexed indicators, methods, and use cases.

---

#### `find_indicators_by_principle`

Find indicators covering a specific CBA principle (1-7).

**Parameters:**
- `principle` (str): Principle number (1-7) or name
- `include_criteria` (bool, optional): Show criteria details (default False)
- `n_results` (int, optional): Maximum results (default 20, max 50)

**Returns:** Indicators covering the principle with criteria breakdown.

---

#### `find_indicators_by_class`

Find indicators belonging to a specific class.

**Parameters:**
- `class_name` (str): Class name (e.g., "Biodiversity", "Soil carbon")
- `n_results` (int, optional): Maximum results (default 30, max 100)

**Returns:** Indicators in the specified class with details.

---

#### `find_indicators_by_measurement_approach`

Find indicators measurable using a specific approach.

**Parameters:**
- `approach` (str): Measurement approach (field, lab, remote, participatory, audit)
- `n_results` (int, optional): Maximum results (default 30, max 100)

**Returns:** Indicators compatible with the measurement approach.

---

#### `find_feasible_methods`

Find measurement methods filtered by practical constraints.

**Parameters:**
- `indicator` (str): Indicator ID or name
- `max_cost` (str, optional): Maximum cost - "Low", "Medium", "High", or "any"
- `min_ease` (str, optional): Minimum ease - "Low", "Medium", "High", or "any"
- `min_accuracy` (str, optional): Minimum accuracy - "Low", "Medium", "High", or "any"

**Returns:** Filtered methods matching the constraints.

---

#### `list_indicators_by_component`

List indicators for a component category (Biotic, Abiotic, Socio-economic).

**Parameters:**
- `component` (str): Component name
- `n_results` (int, optional): Maximum results (default 30, max 100)

**Returns:** Indicators grouped by class within the component.

---

#### `list_available_classes`

List all indicator classes available in the knowledge base.

**Returns:** Classes organized by component with indicator counts.

---

#### `compare_indicators`

Compare multiple indicators side-by-side.

**Parameters:**
- `indicator_ids` (list): List of 2-5 indicator IDs to compare

**Returns:** Comparison table with measurement approaches, principle coverage, and method quality.

---

#### `export_indicator_selection`

Generate a markdown report of selected indicators for documentation.

**Parameters:**
- `indicator_ids` (list): List of indicator IDs (max 20)
- `include_methods` (bool, optional): Include measurement methods (default True)

**Returns:** Markdown-formatted report with indicator details and methods.

---

#### `search_usecases`

Search example use case projects in the knowledge base.

**Parameters:**
- `query` (str): Search query about projects, commodities, or outcomes
- `n_results` (int, optional): Number of results (default 5, max 20)

**Returns:** Matching use cases with outcomes and indicator selections.

---

#### `get_usecase_details`

Get full details for a specific use case project.

**Parameters:**
- `use_case_slug` (str): Project slug (e.g., "regen_cotton_chad")

**Returns:** Complete project details with all outcomes and indicators.

---

#### `get_usecases_by_indicator`

Find all use cases that include a specific indicator.

**Parameters:**
- `indicator` (str): Indicator ID or name

**Returns:** Use cases and outcomes that selected this indicator.

---

## Internal Help Tools

Tools for agent self-discovery of available capabilities.

### Tools (4)

#### `list_tools`

List all available tools with one-line summaries.

**Returns:** Tool names and brief descriptions.

---

#### `list_tools_by_category`

List tools organized by functional category.

**Parameters:**
- `category` (str, optional): Category to filter by (weather, soil, forestry, etc.)

**Returns:** Tools in the category, or category overview if none specified.

---

#### `search_tools`

Search for tools by keyword in name or description.

**Parameters:**
- `query` (str): Search term

**Returns:** Matching tools with descriptions.

---

#### `describe_tool`

Get detailed documentation for a specific tool.

**Parameters:**
- `name` (str): Tool function name (e.g., "get_current_weather")

**Returns:** Full docstring with parameters and return values.

---

## API Keys Summary

| Tool Category | API Key Environment Variable | Get Key From |
|---------------|------------------------------|--------------|
| Forestry (GFW) | `GFW_API_KEY` | [Global Forest Watch](https://data-api.globalforestwatch.org/) |
| Commodities (USDA FAS) | `USDA_FAS_API_KEY` | [api.data.gov](https://api.data.gov/signup/) |
| All others | None required | Free, public APIs |

## Tool Sets

The system provides two pre-configured tool sets:

### REDUCED_TOOLS (22 tools)

A curated subset suitable for models with limited context windows. Includes:
- Internal help tools (4)
- Weather basics (3)
- Soil properties (2)
- Socio-economic (2)
- Knowledge base core (6)
- Indicator selection (5)

### FULL_TOOLS (60 tools)

Complete tool set for models with large context windows. Includes all tools across all categories.

Configure tool set in `providers.yaml`:

```yaml
agent:
  tool_set: reduced  # or "full"
```
