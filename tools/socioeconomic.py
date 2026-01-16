"""Socio-economic tools using World Bank and REST Countries APIs (free, no API key required)."""

import httpx

from strands import tool

# Country code mapping (common names to ISO codes)
COUNTRY_CODES = {
    "usa": "US",
    "united states": "US",
    "america": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "england": "GB",
    "china": "CN",
    "japan": "JP",
    "germany": "DE",
    "france": "FR",
    "india": "IN",
    "brazil": "BR",
    "russia": "RU",
    "canada": "CA",
    "australia": "AU",
    "italy": "IT",
    "spain": "ES",
    "mexico": "MX",
    "south korea": "KR",
    "korea": "KR",
    "indonesia": "ID",
    "netherlands": "NL",
    "switzerland": "CH",
    "sweden": "SE",
    "poland": "PL",
    "belgium": "BE",
    "argentina": "AR",
    "nigeria": "NG",
    "south africa": "ZA",
    "egypt": "EG",
    "pakistan": "PK",
    "bangladesh": "BD",
    "vietnam": "VN",
    "philippines": "PH",
    "thailand": "TH",
    "malaysia": "MY",
    "singapore": "SG",
    "new zealand": "NZ",
    "ireland": "IE",
    "portugal": "PT",
    "greece": "GR",
    "czech republic": "CZ",
    "romania": "RO",
    "hungary": "HU",
    "austria": "AT",
    "israel": "IL",
    "saudi arabia": "SA",
    "uae": "AE",
    "united arab emirates": "AE",
    "turkey": "TR",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "chile": "CL",
    "colombia": "CO",
    "peru": "PE",
    "venezuela": "VE",
    "ukraine": "UA",
}


def _get_country_code(country: str) -> str:
    """Get ISO country code from country name."""
    country_lower = country.lower().strip()
    if country_lower in COUNTRY_CODES:
        return COUNTRY_CODES[country_lower]
    # If already a 2-letter code
    if len(country) == 2:
        return country.upper()
    # Try the name directly
    return country


@tool
def get_country_indicators(country: str) -> str:
    """
    Get basic country information and socio-economic indicators.
    Uses REST Countries API for demographics and World Bank for economic data.

    Args:
        country: Country name (e.g., "United States", "Japan", "Brazil") or ISO code

    Returns:
        Country profile with population, GDP, area, languages, and other indicators
    """
    code = _get_country_code(country)

    # Get basic country info from REST Countries
    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(f"https://restcountries.com/v3.1/alpha/{code}")
            if response.status_code != 200:
                # Try by name
                response = client.get(
                    f"https://restcountries.com/v3.1/name/{country}",
                    params={"fullText": "false"},
                )

            if response.status_code != 200:
                return f"Could not find country: {country}"

            data = response.json()
            if isinstance(data, list):
                data = data[0]
        except Exception as e:
            return f"Error fetching country data: {str(e)}"

    name = data.get("name", {}).get("common", country)
    official_name = data.get("name", {}).get("official", name)

    # Extract data
    population = data.get("population", 0)
    area = data.get("area", 0)
    region = data.get("region", "Unknown")
    subregion = data.get("subregion", "Unknown")
    capital = data.get("capital", ["Unknown"])[0] if data.get("capital") else "Unknown"

    languages = data.get("languages", {})
    lang_list = ", ".join(languages.values()) if languages else "Unknown"

    currencies = data.get("currencies", {})
    curr_list = (
        ", ".join(
            [
                f"{v.get('name', k)} ({v.get('symbol', '')})"
                for k, v in currencies.items()
            ]
        )
        if currencies
        else "Unknown"
    )

    # Format population
    if population >= 1_000_000_000:
        pop_str = f"{population/1_000_000_000:.2f} billion"
    elif population >= 1_000_000:
        pop_str = f"{population/1_000_000:.2f} million"
    else:
        pop_str = f"{population:,}"

    # Format area
    area_str = f"{area:,.0f} km²" if area else "Unknown"

    # Population density
    density = population / area if area else 0
    density_str = f"{density:.1f} per km²" if density else "Unknown"

    return f"""🌍 Country Profile: {name}
Official Name: {official_name}

📍 Geography:
- Capital: {capital}
- Region: {region}
- Subregion: {subregion}
- Area: {area_str}

👥 Demographics:
- Population: {pop_str}
- Density: {density_str}

🗣️ Languages: {lang_list}
💰 Currency: {curr_list}"""


@tool
def get_world_bank_data(country: str, indicator: str = "gdp") -> str:
    """
    Get World Bank economic indicators for a country.

    Args:
        country: Country name or ISO code (e.g., "United States", "JP", "Brazil")
        indicator: Type of data to fetch. Options:
            - "gdp": GDP (current US$)
            - "gdp_per_capita": GDP per capita (current US$)
            - "gdp_growth": GDP growth (annual %)
            - "population": Total population
            - "inflation": Inflation rate (consumer prices annual %)
            - "unemployment": Unemployment rate (% of labor force)
            - "life_expectancy": Life expectancy at birth
            - "literacy": Literacy rate (% of adults)
            - "poverty": Poverty headcount ratio
            - "gini": Gini index (income inequality)
            - "co2": CO2 emissions (metric tons per capita)
            - "renewable_energy": Renewable energy consumption (%)
            - "internet": Internet users (% of population)
            - "mobile": Mobile cellular subscriptions (per 100 people)

    Returns:
        Historical data for the selected indicator (last 10 years available)
    """
    code = _get_country_code(country)

    # World Bank indicator codes
    indicators = {
        "gdp": ("NY.GDP.MKTP.CD", "GDP (current US$)"),
        "gdp_per_capita": ("NY.GDP.PCAP.CD", "GDP per capita (current US$)"),
        "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)"),
        "population": ("SP.POP.TOTL", "Total Population"),
        "inflation": ("FP.CPI.TOTL.ZG", "Inflation Rate (%)"),
        "unemployment": ("SL.UEM.TOTL.ZS", "Unemployment (% of labor force)"),
        "life_expectancy": ("SP.DYN.LE00.IN", "Life Expectancy (years)"),
        "literacy": ("SE.ADT.LITR.ZS", "Literacy Rate (% of adults)"),
        "poverty": ("SI.POV.NAHC", "Poverty Headcount Ratio (%)"),
        "gini": ("SI.POV.GINI", "Gini Index"),
        "co2": ("EN.ATM.CO2E.PC", "CO2 Emissions (tons per capita)"),
        "renewable_energy": ("EG.FEC.RNEW.ZS", "Renewable Energy (%)"),
        "internet": ("IT.NET.USER.ZS", "Internet Users (%)"),
        "mobile": ("IT.CEL.SETS.P2", "Mobile Subscriptions (per 100)"),
    }

    indicator_lower = indicator.lower().replace(" ", "_")
    if indicator_lower not in indicators:
        available = ", ".join(indicators.keys())
        return f"Unknown indicator: {indicator}. Available: {available}"

    wb_code, description = indicators[indicator_lower]

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(
                f"https://api.worldbank.org/v2/country/{code}/indicator/{wb_code}",
                params={"format": "json", "per_page": 20, "date": "2010:2024"},
            )

            if response.status_code != 200:
                return f"Error fetching World Bank data: {response.status_code}"

            data = response.json()

            if len(data) < 2 or not data[1]:
                return f"No data available for {country} - {description}"

            records = data[1]
        except Exception as e:
            return f"Error fetching World Bank data: {str(e)}"

    # Format the data
    country_name = (
        records[0].get("country", {}).get("value", country) if records else country
    )

    lines = [f"📊 {description} - {country_name}\n"]
    lines.append("Year  | Value")
    lines.append("-" * 30)

    for record in records:
        year = record.get("date", "")
        value = record.get("value")
        if value is not None:
            # Format based on indicator type
            if indicator_lower in ["gdp"]:
                if value >= 1_000_000_000_000:
                    formatted = f"${value/1_000_000_000_000:.2f}T"
                elif value >= 1_000_000_000:
                    formatted = f"${value/1_000_000_000:.2f}B"
                else:
                    formatted = f"${value/1_000_000:.2f}M"
            elif indicator_lower in ["gdp_per_capita"]:
                formatted = f"${value:,.0f}"
            elif indicator_lower == "population":
                if value >= 1_000_000_000:
                    formatted = f"{value/1_000_000_000:.2f}B"
                elif value >= 1_000_000:
                    formatted = f"{value/1_000_000:.2f}M"
                else:
                    formatted = f"{value:,.0f}"
            elif indicator_lower in ["gini"]:
                formatted = f"{value:.1f}"
            else:
                formatted = f"{value:.2f}"

            lines.append(f"{year}  | {formatted}")

    if len(lines) <= 3:
        return f"No recent data available for {country} - {description}"

    return "\n".join(lines)
