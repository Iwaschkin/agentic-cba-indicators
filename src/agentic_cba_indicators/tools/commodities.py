"""
USDA Foreign Agricultural Service (FAS) tools.

Provides access to commodity production, supply, and distribution data
from the PSD (Production, Supply & Distribution) database and trade data
from GATS (Global Agricultural Trade System).

**Requires API Key:** Get a free key from https://api.data.gov/signup/

Set the environment variable USDA_FAS_API_KEY with your key.
"""

import os
from typing import Any

import httpx
from strands import tool

from ._http import DEFAULT_TIMEOUT, create_client
from ._timeout import timeout

# API configuration
FAS_BASE_URL = "https://api.fas.usda.gov"
API_KEY_HEADER = "X-Api-Key"

# Common PSD commodity codes for CBA-relevant crops
# Full list available via /api/psd/commodities endpoint
PSD_COMMODITIES: dict[str, dict[str, str]] = {
    # Fiber crops
    "cotton": {"code": "2631000", "name": "Cotton"},
    # Grains
    "corn": {"code": "0440000", "name": "Corn"},
    "wheat": {"code": "0410000", "name": "Wheat"},
    "rice": {"code": "0422110", "name": "Rice, Milled"},
    "barley": {"code": "0430000", "name": "Barley"},
    "sorghum": {"code": "0459100", "name": "Sorghum"},
    # Oilseeds
    "soybeans": {"code": "2222000", "name": "Oilseed, Soybean"},
    "sunflower": {"code": "2226000", "name": "Oilseed, Sunflowerseed"},
    "rapeseed": {"code": "2224000", "name": "Oilseed, Rapeseed"},
    "palm": {"code": "4243000", "name": "Palm Oil"},
    # Tropical crops
    "coffee": {"code": "0711100", "name": "Coffee, Green"},
    "cocoa": {"code": "0721000", "name": "Cocoa Beans"},
    "sugar": {"code": "0612000", "name": "Sugar, Centrifugal"},
    # Livestock products
    "beef": {"code": "0111000", "name": "Beef and Veal"},
    "pork": {"code": "0112000", "name": "Pork"},
    "poultry": {"code": "0113000", "name": "Poultry Meat"},
}

# PSD attribute categories
# Full list via /api/psd/commodityAttributes
PSD_ATTRIBUTES: dict[int, str] = {
    # Production
    20: "Area Harvested",
    28: "Beginning Stocks",
    125: "Production",
    # Supply
    57: "Imports",
    88: "Total Supply",
    # Distribution
    86: "Total Domestic Consumption",
    130: "Exports",
    176: "Ending Stocks",
}

# Country codes (2-letter ISO used by FAS)
COUNTRY_CODES: dict[str, str] = {
    "afghanistan": "AF",
    "algeria": "AG",
    "argentina": "AR",
    "australia": "AS",
    "bangladesh": "BG",
    "brazil": "BR",
    "burkina faso": "UV",
    "cameroon": "CM",
    "canada": "CA",
    "chad": "CD",
    "china": "CH",
    "colombia": "CO",
    "cote d'ivoire": "IV",
    "ivory coast": "IV",
    "egypt": "EG",
    "ethiopia": "ET",
    "france": "FR",
    "germany": "GM",
    "ghana": "GH",
    "guatemala": "GT",
    "honduras": "HO",
    "india": "IN",
    "indonesia": "ID",
    "iran": "IR",
    "italy": "IT",
    "japan": "JA",
    "kenya": "KE",
    "mali": "ML",
    "mexico": "MX",
    "morocco": "MO",
    "myanmar": "BM",
    "nepal": "NP",
    "nicaragua": "NU",
    "nigeria": "NI",
    "pakistan": "PK",
    "peru": "PE",
    "philippines": "RP",
    "russia": "RS",
    "senegal": "SG",
    "south africa": "SF",
    "spain": "SP",
    "sudan": "SU",
    "tanzania": "TZ",
    "thailand": "TH",
    "turkey": "TU",
    "uganda": "UG",
    "ukraine": "UP",
    "united kingdom": "UK",
    "united states": "US",
    "usa": "US",
    "vietnam": "VM",
    "zambia": "ZA",
    "zimbabwe": "ZI",
}


def _get_api_key() -> str | None:
    """Get the USDA FAS API key from environment."""
    return os.environ.get("USDA_FAS_API_KEY")


def _make_request(endpoint: str, params: dict | None = None) -> dict[str, Any] | list:
    """Make an authenticated request to the FAS API."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "USDA FAS API key not found. Set USDA_FAS_API_KEY environment variable. "
            "Get a free key at https://api.data.gov/signup/"
        )

    url = f"{FAS_BASE_URL}{endpoint}"
    headers = {API_KEY_HEADER: api_key}

    with create_client(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _resolve_commodity(commodity: str) -> tuple[str, str]:
    """Resolve commodity name to PSD code."""
    commodity_lower = commodity.lower().strip()

    # Direct match
    if commodity_lower in PSD_COMMODITIES:
        info = PSD_COMMODITIES[commodity_lower]
        return info["code"], info["name"]

    # Partial match
    for key, info in PSD_COMMODITIES.items():
        if commodity_lower in key or key in commodity_lower:
            return info["code"], info["name"]

    # Assume it's already a code
    return commodity, commodity


def _resolve_country(country: str) -> str:
    """Resolve country name to FAS 2-letter code."""
    country_lower = country.lower().strip()

    # Direct match
    if country_lower in COUNTRY_CODES:
        return COUNTRY_CODES[country_lower]

    # Check if already a 2-letter code
    if len(country) == 2:
        return country.upper()

    # Partial match
    for name, code in COUNTRY_CODES.items():
        if country_lower in name or name in country_lower:
            return code

    return country.upper()[:2]


@tool
@timeout(30)
def get_commodity_production(
    commodity: str, country: str = "world", year: int | None = None
) -> str:
    """
    Get production, supply, and distribution data for an agricultural commodity.

    Uses the USDA PSD (Production, Supply & Distribution) database which contains
    forecasts and historical data for major commodities since 1960.

    Common commodities: cotton, corn, wheat, rice, soybeans, coffee, cocoa, sugar,
    palm, beef, pork, poultry

    Args:
        commodity: Commodity name (e.g., "cotton", "coffee", "cocoa") or PSD code
        country: Country name or 2-letter code (default "world" for global data)
        year: Market year (default: current year). PSD has data since 1960.

    Returns:
        Production, supply, and distribution data including area harvested,
        production, imports, exports, and ending stocks

    Note: Requires USDA_FAS_API_KEY environment variable
    """
    from datetime import datetime

    if year is None:
        year = datetime.now().year

    try:
        commodity_code, commodity_name = _resolve_commodity(commodity)

        # Build endpoint based on country
        if country.lower() == "world":
            endpoint = f"/api/psd/commodity/{commodity_code}/world/year/{year}"
            location_label = "World"
        else:
            country_code = _resolve_country(country)
            endpoint = (
                f"/api/psd/commodity/{commodity_code}"
                f"/country/{country_code}/year/{year}"
            )
            location_label = country.title()

        data = _make_request(endpoint)

        if not data:
            return f"No data found for {commodity_name} in {location_label} for {year}."

        # Parse response - data is a list of records
        records = data if isinstance(data, list) else [data]

        # Group by attribute
        results: dict[str, dict[str, Any]] = {}
        for record in records:
            attr_id = record.get("attributeId")
            if attr_id is None:
                continue
            attr_name = PSD_ATTRIBUTES.get(int(attr_id), f"Attribute {attr_id}")
            value = record.get("value")
            unit_id = record.get("unitId")

            if value is not None:
                results[attr_name] = {
                    "value": value,
                    "unit_id": unit_id,
                }

        # Build output
        output = [
            f"=== {commodity_name} - {location_label} ({year}) ===",
            "Source: USDA FAS Production, Supply & Distribution Database\n",
        ]

        # Organized by category
        production_attrs = ["Area Harvested", "Beginning Stocks", "Production"]
        supply_attrs = ["Imports", "Total Supply"]
        distribution_attrs = [
            "Total Domestic Consumption",
            "Exports",
            "Ending Stocks",
        ]

        if any(attr in results for attr in production_attrs):
            output.append("📊 Production:")
            for attr in production_attrs:
                if attr in results:
                    val = results[attr]["value"]
                    output.append(f"  • {attr}: {val:,.0f}")

        if any(attr in results for attr in supply_attrs):
            output.append("\n📦 Supply:")
            for attr in supply_attrs:
                if attr in results:
                    val = results[attr]["value"]
                    output.append(f"  • {attr}: {val:,.0f}")

        if any(attr in results for attr in distribution_attrs):
            output.append("\n📤 Distribution:")
            for attr in distribution_attrs:
                if attr in results:
                    val = results[attr]["value"]
                    output.append(f"  • {attr}: {val:,.0f}")

        # Note about units
        output.append("\n⚠️ Units: 1000 MT (metric tons) for grains/oilseeds,")
        output.append("   480 lb bales for cotton, 1000 bags for coffee")

        return "\n".join(output)

    except ValueError as e:
        return str(e)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "Authentication failed. Check your USDA_FAS_API_KEY."
        elif e.response.status_code == 404:
            return f"No data found for commodity '{commodity}' in {year}."
        return f"API error: {e.response.status_code}"


@tool
@timeout(30)
def get_commodity_trade(
    commodity: str, country: str, years: int = 5, trade_type: str = "both"
) -> str:
    """
    Get trade data (imports/exports) for a commodity over multiple years.

    Shows trade trends useful for understanding market dynamics and
    commodity flow patterns relevant to CBA projects.

    Args:
        commodity: Commodity name (e.g., "cotton", "coffee", "cocoa")
        country: Country name or 2-letter code
        years: Number of years of historical data (default 5)
        trade_type: "imports", "exports", or "both" (default)

    Returns:
        Trade trends showing imports and/or exports over time

    Note: Requires USDA_FAS_API_KEY environment variable
    """
    from datetime import datetime

    current_year = datetime.now().year

    try:
        commodity_code, commodity_name = _resolve_commodity(commodity)
        country_code = _resolve_country(country)

        # Collect data for each year
        imports_data: dict[int, float] = {}
        exports_data: dict[int, float] = {}

        for yr in range(current_year - years + 1, current_year + 1):
            endpoint = (
                f"/api/psd/commodity/{commodity_code}/country/{country_code}/year/{yr}"
            )

            try:
                data = _make_request(endpoint)
                records = data if isinstance(data, list) else [data]

                for record in records:
                    attr_id = record.get("attributeId")
                    value = record.get("value")

                    if value is not None:
                        if attr_id == 57:  # Imports
                            imports_data[yr] = value
                        elif attr_id == 130:  # Exports
                            exports_data[yr] = value
            except Exception:
                continue

        if not imports_data and not exports_data:
            return f"No trade data found for {commodity_name} in {country}."

        # Build output
        output = [
            f"=== {commodity_name} Trade - {country.title()} ===",
            f"Period: {current_year - years + 1} to {current_year}",
            "Source: USDA FAS PSD Database\n",
        ]

        if trade_type in ["imports", "both"] and imports_data:
            output.append("📥 Imports (1000 MT):")
            output.extend(
                f"  {yr}: {imports_data[yr]:,.0f}" for yr in sorted(imports_data.keys())
            )

            # Calculate trend
            if len(imports_data) >= 2:
                years_list = sorted(imports_data.keys())
                first_val = imports_data[years_list[0]]
                last_val = imports_data[years_list[-1]]
                if first_val > 0:
                    change = ((last_val - first_val) / first_val) * 100
                    trend = "📈" if change > 0 else "📉"
                    output.append(f"  Trend: {trend} {change:+.1f}%")
            output.append("")

        if trade_type in ["exports", "both"] and exports_data:
            output.append("📤 Exports (1000 MT):")
            output.extend(
                f"  {yr}: {exports_data[yr]:,.0f}" for yr in sorted(exports_data.keys())
            )

            # Calculate trend
            if len(exports_data) >= 2:
                years_list = sorted(exports_data.keys())
                first_val = exports_data[years_list[0]]
                last_val = exports_data[years_list[-1]]
                if first_val > 0:
                    change = ((last_val - first_val) / first_val) * 100
                    trend = "📈" if change > 0 else "📉"
                    output.append(f"  Trend: {trend} {change:+.1f}%")

        return "\n".join(output)

    except ValueError as e:
        return str(e)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"


@tool
@timeout(30)
def compare_commodity_producers(commodity: str, year: int | None = None) -> str:
    """
    Compare production across major producing countries for a commodity.

    Useful for understanding global market share and identifying key
    producing regions for CBA indicator benchmarking.

    Args:
        commodity: Commodity name (e.g., "cotton", "coffee", "cocoa")
        year: Market year (default: current year)

    Returns:
        Top producing countries with production volumes and market share

    Note: Requires USDA_FAS_API_KEY environment variable
    """
    from datetime import datetime

    if year is None:
        year = datetime.now().year

    try:
        commodity_code, commodity_name = _resolve_commodity(commodity)

        # Get data for all countries
        endpoint = f"/api/psd/commodity/{commodity_code}/country/all/year/{year}"
        data = _make_request(endpoint)

        if not data:
            return f"No data found for {commodity_name} in {year}."

        records = data if isinstance(data, list) else [data]

        # Extract production by country
        production_by_country: dict[str, float] = {}
        for record in records:
            if record.get("attributeId") == 125:  # Production
                country_code = record.get("countryCode", "")
                value = record.get("value", 0)
                if value and value > 0:
                    production_by_country[country_code] = value

        if not production_by_country:
            return f"No production data found for {commodity_name} in {year}."

        # Get country names
        try:
            countries_data = _make_request("/api/psd/countries")
            country_names = {
                c.get("countryCode"): c.get("countryName")
                for c in countries_data
                if isinstance(c, dict)
            }
        except Exception:
            country_names = {}

        # Sort by production (descending)
        sorted_producers = sorted(
            production_by_country.items(), key=lambda x: x[1], reverse=True
        )

        # Calculate total for market share
        total_production = sum(production_by_country.values())

        # Build output
        output = [
            f"=== Top {commodity_name} Producers ({year}) ===",
            "Source: USDA FAS PSD Database\n",
            "Rank | Country | Production | Market Share",
            "-----|---------|------------|-------------",
        ]

        for i, (code, production) in enumerate(sorted_producers[:15], 1):
            country_name = country_names.get(code, code) or code
            share = (production / total_production * 100) if total_production > 0 else 0
            output.append(
                f"{i:4} | {country_name[:15]:<15} | {production:>10,.0f} | {share:>5.1f}%"
            )

        output.append(f"\nTotal Global Production: {total_production:,.0f}")
        output.append("Units: 1000 MT (metric tons) or commodity-specific units")

        return "\n".join(output)

    except ValueError as e:
        return str(e)
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code}"


@tool
@timeout(30)
def list_fas_commodities() -> str:
    """
    List available commodities in the USDA FAS PSD database.

    Use this to discover available commodity codes and names before
    querying production or trade data.

    Returns:
        List of CBA-relevant commodities with their codes

    Note: Requires USDA_FAS_API_KEY environment variable
    """
    try:
        # Try to get full list from API
        data = _make_request("/api/psd/commodities")

        output = [
            "=== USDA FAS PSD Commodities ===",
            "Full database has 50+ commodities. Key CBA-relevant ones:\n",
        ]

        # Show pre-mapped commodities
        output.append("📦 Pre-configured (use these names directly):")
        for name, info in sorted(PSD_COMMODITIES.items()):
            output.append(f"  • {name}: {info['name']} (code: {info['code']})")

        output.append("\n💡 Tip: You can also use the commodity code directly.")
        output.append("    Example: get_commodity_production('2631000', 'Brazil')")

        if data:
            output.append(f"\n📊 Total commodities in API: {len(data)}")

        return "\n".join(output)

    except ValueError as e:
        return str(e)
    except Exception as e:
        # Fall back to showing pre-configured list
        output = [
            "=== Available Commodities ===",
            "(Pre-configured for CBA analysis)\n",
        ]

        categories = {
            "🌱 Fiber Crops": ["cotton"],
            "🌾 Grains": ["corn", "wheat", "rice", "barley", "sorghum"],
            "🫘 Oilseeds": ["soybeans", "sunflower", "rapeseed", "palm"],
            "☕ Tropical": ["coffee", "cocoa", "sugar"],
            "🥩 Livestock": ["beef", "pork", "poultry"],
        }

        for category, items in categories.items():
            output.append(f"{category}:")
            for item in items:
                info = PSD_COMMODITIES[item]
                output.append(f"  • {item}: {info['name']}")
            output.append("")

        output.append(f"Note: API call failed ({e}), showing cached list.")
        return "\n".join(output)


@tool
@timeout(30)
def search_commodity_data(query: str, n_results: int = 10) -> str:
    """
    Search for commodity-related information across available datasets.

    Searches commodity names, country codes, and provides guidance on
    available data types.

    Args:
        query: Search term (commodity name, country, or data type)
        n_results: Maximum results to return (default 10)

    Returns:
        Matching commodities, countries, or data availability info
    """
    query_lower = query.lower().strip()

    output = [f"=== Search Results for '{query}' ===\n"]

    # Search commodities
    matching_commodities = []
    for name, info in PSD_COMMODITIES.items():
        if query_lower in name or query_lower in info["name"].lower():
            matching_commodities.append((name, info))

    if matching_commodities:
        output.append("📦 Matching Commodities:")
        for name, info in matching_commodities[:n_results]:
            output.append(f"  • {name}: {info['name']} (code: {info['code']})")
        output.append("")

    # Search countries
    matching_countries = []
    for name, code in COUNTRY_CODES.items():
        if query_lower in name:
            matching_countries.append((name, code))

    if matching_countries:
        output.append("🌍 Matching Countries:")
        for name, code in matching_countries[:n_results]:
            output.append(f"  • {name.title()}: {code}")
        output.append("")

    # Suggest related tools
    output.append("📊 Available Data Types:")
    output.append("  • Production, Supply & Distribution (PSD) - since 1960")
    output.append("  • Global trade data (imports/exports)")
    output.append("  • Country rankings by production")
    output.append("")

    output.append("💡 Example Queries:")
    output.append("  • get_commodity_production('cotton', 'Chad', 2024)")
    output.append("  • get_commodity_trade('coffee', 'Brazil', years=5)")
    output.append("  • compare_commodity_producers('cocoa')")

    if not matching_commodities and not matching_countries:
        output.append(f"\nNo exact matches found for '{query}'.")
        output.append(
            "Try broader terms or use list_fas_commodities() to see all options."
        )

    return "\n".join(output)
    return "\n".join(output)
    return "\n".join(output)
