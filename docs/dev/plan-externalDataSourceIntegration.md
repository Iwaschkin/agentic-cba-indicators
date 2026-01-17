# External Data Source Integration Plan

## Prioritization Matrix

| API | Effort | Value | CBA Indicator Coverage | Priority Score |
|-----|--------|-------|------------------------|----------------|
| **NASA POWER** | Low | High | ~30 Abiotic (microclimate, water) | ⭐⭐⭐⭐⭐ |
| **ISRIC SoilGrids** | Low | High | ~45 Abiotic (soil quality, carbon) | ⭐⭐⭐⭐⭐ |
| **UN SDG API** | Low | High | Cross-cutting (all 7 Principles) | ⭐⭐⭐⭐⭐ |
| **GBIF** | Low | High | ~40 Biotic (biodiversity, species) | ⭐⭐⭐⭐ |
| **ILO STAT** | Medium | High | ~25 Socio-economic (labor, wages) | ⭐⭐⭐⭐ |
| **USDA FAS** | Medium | Medium | ~15 Economic (commodity markets) | ⭐⭐⭐ |
| **WB Gender** | Low | Medium | ~20 Social (equity, inclusion) | ⭐⭐⭐ |
| **Global Forest Watch** | Medium | Medium | ~15 Biotic/Abiotic (forests) | ⭐⭐⭐ |
| **FAO AQUASTAT** | Medium | Medium | ~12 Abiotic (water resources) | ⭐⭐ |
| **IUCN Red List** | Medium | Low | Overlaps with GBIF | ⭐⭐ |
| **FAO STAT** | Medium | Low | API unstable, overlaps WB | ⭐ |
| **Global Surface Water** | High | Low | Requires raster processing | ⭐ |
| **OpenLandMap** | High | Low | Covered by SoilGrids | ⭐ |

---

## Recommended Implementation Phases

### Phase 1: Core Coverage (3-4 days total)

| API | Why First | Unique Value |
|-----|-----------|--------------|
| **NASA POWER** | No auth, excellent docs | Only source for point-level climate data (solar, evapotranspiration) |
| **ISRIC SoilGrids** | No auth, simple REST | Only source for soil properties at coordinates |
| **UN SDG API** | No auth, direct CBA alignment | Official SDG progress - validates project impact claims |

**Combined coverage:** ~75 indicators + direct SDG mapping

### Phase 2: Biodiversity & Labor (3-4 days total)

| API | Why Second | Unique Value |
|-----|------------|--------------|
| **GBIF** | No auth for queries | Species occurrence - essential for biodiversity indicators |
| **ILO STAT** | No auth, flexible | Labor conditions, wages, working hours - fills socio-economic gap |

**Combined coverage:** +65 indicators (140 total)

### Phase 3: Specialized Depth (4-5 days total)

| API | Why Third | Unique Value |
|-----|-----------|--------------|
| **WB Gender** | Builds on existing WB tools | Gender-disaggregated metrics for equity indicators |
| **USDA FAS** | API key but straightforward | Commodity-specific data for cotton/coffee/cocoa projects |
| **Global Forest Watch** | More complex queries | Deforestation alerts, forest carbon - high demand for agroforestry |

---

## Value Analysis by CBA Principle

| Principle | Current Gap | Best APIs to Fill |
|-----------|-------------|-------------------|
| **1. Natural Environment** | Climate data, soil properties | NASA POWER, SoilGrids |
| **2. Social Well-being** | Labor, gender equity | ILO STAT, WB Gender |
| **3. Economic Prosperity** | Commodity markets | USDA FAS, (already have WB) |
| **4. Diversity** | Species data | GBIF, (IUCN if needed) |
| **5. Connectivity** | Forest fragmentation | Global Forest Watch |
| **6. Adaptive Capacity** | Climate variability | NASA POWER |
| **7. Harmony** | SDG alignment | UN SDG API |

---

## API Technical Details

### Phase 1 APIs

#### NASA POWER
- **URL:** https://power.larc.nasa.gov/
- **Auth:** None required
- **Rate Limits:** HTTP 429 throttling on excessive requests
- **Data Format:** JSON, CSV, ASCII, NetCDF
- **Query:** Point (lat/lon), time range, 140+ parameters
- **Docs:** Excellent - Swagger-style, tutorials
- **Example:** `GET https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=5.39&latitude=51.57&start=20230101&end=20231231&format=JSON`

#### ISRIC SoilGrids
- **URL:** https://rest.isric.org/soilgrids/v2.0/docs
- **Auth:** None required
- **Rate Limits:** Not documented
- **Data Format:** JSON (point), GeoTIFF (bulk)
- **Query:** Coordinates, 6 depths, 10+ soil properties
- **Docs:** Good - OpenAPI spec
- **Example:** `GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon=5.39&lat=51.57&property=soc&depth=0-5cm&value=mean`

#### UN SDG API
- **URL:** https://unstats.un.org/sdgs/UNSDGAPIV5/swagger/
- **Auth:** None required
- **Rate Limits:** Not documented
- **Data Format:** JSON, CSV, Excel
- **Query:** Goal, Target, Indicator, Country, Time
- **Docs:** Good - Swagger UI
- **Example:** `GET https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Series/Data?seriesCode=SI_COV_LMKT&geoAreaCode=4`

### Phase 2 APIs

#### GBIF
- **URL:** https://api.gbif.org/
- **Auth:** None for queries; Basic for downloads
- **Rate Limits:** Adaptive HTTP 429
- **Data Format:** JSON
- **Query:** Species, coordinates, country, year
- **Docs:** Excellent - techdocs.gbif.org
- **Example:** `GET https://api.gbif.org/v1/occurrence/search?country=TZ&year=2020,2024&limit=20`

#### ILO STAT
- **URL:** https://rplumber.ilo.org/
- **Auth:** None required
- **Rate Limits:** Not documented
- **Data Format:** JSON, CSV, Excel, SDMX
- **Query:** Indicator, country, sex, age, time
- **Docs:** Good
- **Example:** `GET https://rplumber.ilo.org/data/indicator/?id=SDG_0852_SEX_AGE_RT_A&ref_area=USA&format=.csv`

### Phase 3 APIs

#### World Bank Gender
- **URL:** https://genderdata.worldbank.org/
- **Auth:** None required
- **Uses:** Standard World Bank API with source=14
- **Example:** `GET https://api.worldbank.org/v2/sources/14/country/all/indicator/SE.ADT.LITR.ZS?format=json`

#### USDA FAS
- **URL:** https://apps.fas.usda.gov/opendataweb/home
- **Auth:** API Key (free via api.data.gov)
- **Data Format:** JSON
- **Query:** Commodity, country, year
- **Example:** `GET https://api.fas.usda.gov/api/psd/commodity/0440000/country/all/year/2024` (with API key header)

#### Global Forest Watch
- **URL:** https://data-api.globalforestwatch.org/
- **Auth:** API Key (free, domain-tiered)
- **Data Format:** JSON, GeoJSON, CSV
- **Query:** Dataset, geostore, SQL
- **Docs:** Excellent - OpenAPI spec

---

## Suggested Tool Structure

Each API should follow the existing pattern in `tools/`:

```
tools/
├── weather.py          # Existing - Open-Meteo
├── climate.py          # Existing - Climate normals
├── socioeconomic.py    # Existing - World Bank, REST Countries
├── knowledge_base.py   # Existing - ChromaDB RAG
├── nasa_power.py       # NEW - Climate/agricultural parameters
├── soilgrids.py        # NEW - Soil properties
├── sdg.py              # NEW - UN SDG indicators
├── biodiversity.py     # NEW - GBIF species data
├── labor.py            # NEW - ILO statistics
├── commodities.py      # NEW - USDA FAS (Phase 3)
├── forestry.py         # NEW - Global Forest Watch (Phase 3)
```

---

## Tool Function Signatures (Phase 1)

### nasa_power.py
```python
@tool
def get_agricultural_climate(lat: float, lon: float, start_date: str, end_date: str) -> str:
    """Get agricultural climate parameters for a location."""

@tool
def get_solar_radiation(lat: float, lon: float, year: int) -> str:
    """Get solar radiation and related parameters for agricultural planning."""
```

### soilgrids.py
```python
@tool
def get_soil_properties(lat: float, lon: float, properties: list[str] = None) -> str:
    """Get soil properties at a location from ISRIC SoilGrids."""

@tool
def get_soil_carbon(lat: float, lon: float) -> str:
    """Get soil organic carbon content at different depths."""
```

### sdg.py
```python
@tool
def get_sdg_progress(country: str, goal: int = None) -> str:
    """Get SDG indicator progress for a country."""

@tool
def search_sdg_indicators(query: str) -> str:
    """Search for SDG indicators by keyword."""
```

---

## Next Steps

1. [ ] Implement Phase 1 APIs (NASA POWER, SoilGrids, UN SDG)
2. [ ] Add tools to main.py agent configuration
3. [ ] Test with sample queries matching CBA indicators
4. [ ] Update system prompt with new tool capabilities
5. [ ] Document API limitations and caveats
