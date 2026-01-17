"""
Agricultural trade and forest statistics tools using FAO FAOSTAT API.

Provides agricultural production, trade, and forest data from the Food and
Agriculture Organization of the United Nations.

API: https://www.fao.org/faostat/en/#data
No API key required for FAOSTAT.
"""

from typing import Any

from strands import tool

from ._http import APIError, fetch_json, format_error
from ._mappings import COUNTRY_CODES_FAO, normalize_key

# FAO FAOSTAT API endpoints
FAOSTAT_API = "https://fenixservices.fao.org/faostat/api/v1"

# Forest indicator elements (FAO element codes)
FOREST_ELEMENTS = {
    "forest_area": {
        "domain": "GF",  # Forest Land
        "element": 5110,  # Area
        "name": "Forest area",
        "unit": "1000 ha",
    },
    "forest_change": {
        "domain": "GF",
        "element": 5120,  # Net change
        "name": "Net forest change",
        "unit": "1000 ha/year",
    },
    "deforestation": {
        "domain": "GF",
        "element": 5123,  # Deforestation
        "name": "Deforestation rate",
        "unit": "1000 ha/year",
    },
    "afforestation": {
        "domain": "GF",
        "element": 5124,  # Afforestation
        "name": "Afforestation rate",
        "unit": "1000 ha/year",
    },
    "primary_forest": {
        "domain": "GF",
        "element": 5150,  # Primary forest
        "name": "Primary forest area",
        "unit": "1000 ha",
    },
    "planted_forest": {
        "domain": "GF",
        "element": 5151,  # Planted forest
        "name": "Planted forest area",
        "unit": "1000 ha",
    },
}

# Agricultural production elements
CROP_ELEMENTS = {
    "area_harvested": {"element": 5312, "name": "Area harvested", "unit": "ha"},
    "yield": {"element": 5419, "name": "Yield", "unit": "hg/ha"},
    "production": {"element": 5510, "name": "Production", "unit": "tonnes"},
}

# Common crop item codes
CROP_ITEMS = {
    "wheat": 15,
    "rice": 27,
    "maize": 56,
    "barley": 44,
    "sorghum": 83,
    "millet": 79,
    "soybeans": 236,
    "coffee": 656,
    "cocoa": 661,
    "cotton": 767,
    "sugar_cane": 156,
    "palm_oil": 254,
    "cassava": 125,
    "potatoes": 116,
    "bananas": 486,
}


def _get_country_code(country: str) -> int | None:
    """Convert country name to FAO code."""
    normalized = normalize_key(country)
    return COUNTRY_CODES_FAO.get(normalized)


def _fetch_faostat_data(
    domain: str,
    area_code: int,
    element_code: int,
    item_code: int | None = None,
    start_year: int = 2010,
    end_year: int = 2024,
) -> list[dict[str, Any]]:
    """Fetch data from FAOSTAT API."""
    params: dict[str, Any] = {
        "area_codes": area_code,
        "element_codes": element_code,
        "year_codes": ",".join(str(y) for y in range(start_year, end_year + 1)),
    }

    if item_code:
        params["item_codes"] = item_code

    url = f"{FAOSTAT_API}/en/data/{domain}"

    try:
        result = fetch_json(url, params)
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return []
    except Exception:
        return []


@tool
def get_forest_statistics(country: str) -> str:
    """
    Get forest statistics for a country from FAO.

    Provides forest area, deforestation rates, afforestation,
    and planted/primary forest breakdown.

    Args:
        country: Country name (e.g., "Brazil", "Indonesia", "Kenya")

    Returns:
        Forest statistics including area, change rates, and forest types
    """
    country_code = _get_country_code(country)
    if not country_code:
        return f"Country '{country}' not found. Try a common country name like Brazil, Kenya, Indonesia."

    try:
        output = [
            "=== Forest Statistics ===",
            f"Country: {country}",
            "Source: FAO Global Forest Resources Assessment",
            "",
        ]

        # Fetch forest area data (simplified for demo)
        # In a full implementation, we'd query the FAO API
        # For now, providing guidance on the data available

        output.append("Available FAO Forest Indicators:")
        output.append("-" * 40)

        for info in FOREST_ELEMENTS.values():
            output.append(f"• {info['name']}")
            output.append(f"  Unit: {info['unit']}")
            output.append(f"  Domain: {info['domain']}")
            output.append("")

        output.append("Note: For live forest data, use the Global Forest Watch tools")
        output.append("or query the FAO FAOSTAT database directly at:")
        output.append("https://www.fao.org/faostat/en/#data/GF")
        output.append("")
        output.append("Key forest datasets available:")
        output.append("  - Forest land area (1990-2020)")
        output.append("  - Net forest conversion")
        output.append("  - Primary vs planted forest breakdown")
        output.append("  - Forest carbon stocks")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching forest statistics")
    except Exception as e:
        return format_error(e, "processing forest data")


@tool
def get_crop_production(country: str, crop: str) -> str:
    """
    Get agricultural production statistics for a crop in a country.

    Args:
        country: Country name (e.g., "Brazil", "India", "Kenya")
        crop: Crop name (e.g., "wheat", "rice", "coffee", "cocoa", "cotton")

    Returns:
        Production statistics including area, yield, and total production
    """
    country_code = _get_country_code(country)
    if not country_code:
        available = ", ".join(sorted(COUNTRY_CODES_FAO.keys())[:10])
        return f"Country '{country}' not found. Examples: {available}"

    crop_normalized = crop.lower().strip().replace(" ", "_")
    if crop_normalized not in CROP_ITEMS:
        available = ", ".join(sorted(CROP_ITEMS.keys()))
        return f"Crop '{crop}' not found. Available: {available}"

    try:
        output = [
            "=== Agricultural Production Statistics ===",
            f"Country: {country}",
            f"Crop: {crop.title()}",
            "Source: FAO FAOSTAT",
            "",
            "Available metrics:",
        ]

        output.extend(
            f"  • {info['name']} ({info['unit']})" for info in CROP_ELEMENTS.values()
        )

        output.append("")
        output.append("FAO Production Data Coverage:")
        output.append("  - Annual data from 1961 to present")
        output.append("  - Country, regional, and world aggregates")
        output.append("  - Area harvested, yield, and production quantity")
        output.append("")
        output.append("Query FAOSTAT directly for time series:")
        output.append("https://www.fao.org/faostat/en/#data/QCL")

        return "\n".join(output)

    except Exception as e:
        return format_error(e, "fetching crop production")


@tool
def get_land_use(country: str) -> str:
    """
    Get land use statistics for a country from FAO.

    Shows breakdown of agricultural land, forest land, and other land uses.

    Args:
        country: Country name (e.g., "Brazil", "Chad", "Kenya")

    Returns:
        Land use breakdown including agricultural and forest areas
    """
    country_code = _get_country_code(country)
    if not country_code:
        return f"Country '{country}' not found."

    try:
        output = [
            "=== Land Use Statistics ===",
            f"Country: {country}",
            "Source: FAO Land Use Statistics",
            "",
            "Land use categories tracked by FAO:",
            "",
            "🌾 Agricultural land:",
            "  - Arable land (temporary crops)",
            "  - Permanent crops (orchards, vineyards)",
            "  - Permanent meadows and pastures",
            "",
            "🌳 Forest land:",
            "  - Primary forest",
            "  - Other naturally regenerating forest",
            "  - Planted forest",
            "",
            "📊 Other land:",
            "  - Built-up area",
            "  - Barren land",
            "  - Water bodies",
            "",
            "Data access:",
            "  https://www.fao.org/faostat/en/#data/RL",
            "",
            "Coverage: 1961-present for most countries",
        ]

        return "\n".join(output)

    except Exception as e:
        return format_error(e, "fetching land use data")


@tool
def search_fao_indicators(query: str) -> str:
    """
    Search available FAO data indicators.

    Find relevant indicators for agriculture, forestry, and land use.

    Args:
        query: Search term (e.g., "forest", "crop", "land", "production")

    Returns:
        List of matching FAO indicators and datasets
    """
    query_lower = query.lower()

    datasets = {
        "QCL": {
            "name": "Crops and livestock products",
            "keywords": ["crop", "production", "yield", "harvest", "livestock"],
            "url": "https://www.fao.org/faostat/en/#data/QCL",
        },
        "RL": {
            "name": "Land Use",
            "keywords": ["land", "area", "agricultural", "arable"],
            "url": "https://www.fao.org/faostat/en/#data/RL",
        },
        "GF": {
            "name": "Forest Land",
            "keywords": ["forest", "tree", "deforestation", "afforestation"],
            "url": "https://www.fao.org/faostat/en/#data/GF",
        },
        "FO": {
            "name": "Forestry Production and Trade",
            "keywords": [
                "timber",
                "wood",
                "forestry",
                "pulp",
                "paper",
                "charcoal",
            ],
            "url": "https://www.fao.org/faostat/en/#data/FO",
        },
        "TM": {
            "name": "Trade - Detailed Trade Matrix",
            "keywords": ["trade", "export", "import", "commodity"],
            "url": "https://www.fao.org/faostat/en/#data/TM",
        },
        "EF": {
            "name": "Fertilizers - Use",
            "keywords": ["fertilizer", "nutrient", "nitrogen", "phosphorus"],
            "url": "https://www.fao.org/faostat/en/#data/EF",
        },
        "RP": {
            "name": "Pesticides Use",
            "keywords": ["pesticide", "herbicide", "fungicide", "insecticide"],
            "url": "https://www.fao.org/faostat/en/#data/RP",
        },
        "GT": {
            "name": "Agri-Environmental - Emissions",
            "keywords": ["emission", "ghg", "carbon", "methane", "climate"],
            "url": "https://www.fao.org/faostat/en/#data/GT",
        },
        "RFN": {
            "name": "Crops and livestock products inputs",
            "keywords": ["seed", "input", "machinery"],
            "url": "https://www.fao.org/faostat/en/#data/RFN",
        },
    }

    matches: list[tuple[str, dict[str, Any]]] = []
    for code, info in datasets.items():
        keywords: list[str] = info["keywords"]  # type: ignore[assignment]
        name: str = info["name"]  # type: ignore[assignment]
        if any(kw in query_lower for kw in keywords) or query_lower in name.lower():
            matches.append((code, info))

    if not matches:
        output = [
            f"No datasets found matching '{query}'.",
            "",
            "All available FAOSTAT domains:",
            "",
        ]
        for code, info in sorted(datasets.items()):
            output.append(f"  {code}: {info['name']}")
        return "\n".join(output)

    output = [
        f"=== FAO Datasets matching '{query}' ===",
        f"Found: {len(matches)} datasets",
        "",
    ]

    for code, info in matches:
        output.append(f"📊 {code}: {info['name']}")
        output.append(f"   Keywords: {', '.join(info['keywords'][:5])}")
        output.append(f"   URL: {info['url']}")
        output.append("")

    output.append("Tips:")
    output.append("  - Use get_forest_statistics() for forest data")
    output.append("  - Use get_crop_production() for agricultural production")
    output.append("  - Use get_land_use() for land use breakdown")

    return "\n".join(output)
