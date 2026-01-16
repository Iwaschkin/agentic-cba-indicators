"""
Labor statistics tools using ILOSTAT (ILO Statistics) API.

Provides labor market indicators including employment, unemployment,
wages, and working conditions data.

API Documentation: https://rplumber.ilo.org/
No API key required.
"""

from typing import Any

from strands import tool

from ._http import APIError, fetch_json, format_error

# ILO API base URL
ILO_API = "https://rplumber.ilo.org"

# Key labor indicators with IDs and descriptions
LABOR_INDICATORS = {
    # Employment
    "employment_rate": {
        "id": "EMP_DWAP_SEX_AGE_RT_A",
        "name": "Employment-to-population ratio",
        "unit": "%",
        "description": "Percentage of working-age population that is employed",
    },
    "labor_force_participation": {
        "id": "EAP_DWAP_SEX_AGE_RT_A",
        "name": "Labour force participation rate",
        "unit": "%",
        "description": "Percentage of working-age population in the labor force",
    },
    "unemployment_rate": {
        "id": "UNE_DEAP_SEX_AGE_RT_A",
        "name": "Unemployment rate",
        "unit": "%",
        "description": "Percentage of labor force that is unemployed",
    },
    # Vulnerable employment
    "informal_employment": {
        "id": "EMP_NIFL_SEX_RT_A",
        "name": "Informal employment rate",
        "unit": "%",
        "description": "Share of employment in informal sector",
    },
    "working_poverty": {
        "id": "SDG_0111_SEX_AGE_RT_A",
        "name": "Working poverty rate (below $2.15/day)",
        "unit": "%",
        "description": "Employed persons living below extreme poverty line",
    },
    # Youth
    "youth_unemployment": {
        "id": "SDG_0852_SEX_AGE_RT_A",
        "name": "Youth unemployment rate",
        "unit": "%",
        "description": "Unemployment rate for ages 15-24",
    },
    "youth_neet": {
        "id": "EIP_NEET_SEX_RT_A",
        "name": "Youth NEET rate",
        "unit": "%",
        "description": "Youth not in education, employment, or training",
    },
    # Gender
    "women_managers": {
        "id": "SDG_0552_NOC_RT_A",
        "name": "Women in managerial positions",
        "unit": "%",
        "description": "Proportion of women in senior and middle management",
    },
    # Wages
    "average_wages": {
        "id": "EAR_4MTH_SEX_CUR_NB_A",
        "name": "Average monthly earnings",
        "unit": "Local currency",
        "description": "Average monthly earnings of employees",
    },
    # Working conditions
    "excessive_hours": {
        "id": "HOW_TEMP_SEX_ECO_NB_A",
        "name": "Workers with excessive hours",
        "unit": "%",
        "description": "Employed working 49+ hours per week",
    },
    # Child labor
    "child_labor": {
        "id": "SDG_0871_SEX_AGE_RT_A",
        "name": "Child labor rate",
        "unit": "%",
        "description": "Percentage of children (5-17) in child labor",
    },
    # Safety
    "fatal_injuries": {
        "id": "INJ_FATL_SEX_MIG_RT_A",
        "name": "Fatal occupational injuries rate",
        "unit": "per 100,000",
        "description": "Rate of fatal occupational injuries",
    },
}

# ISO country codes for common countries
COUNTRY_CODES = {
    "brazil": "BRA",
    "chad": "TCD",
    "china": "CHN",
    "ethiopia": "ETH",
    "france": "FRA",
    "germany": "DEU",
    "ghana": "GHA",
    "india": "IND",
    "indonesia": "IDN",
    "japan": "JPN",
    "kenya": "KEN",
    "mexico": "MEX",
    "nigeria": "NGA",
    "south africa": "ZAF",
    "spain": "ESP",
    "tanzania": "TZA",
    "uganda": "UGA",
    "united kingdom": "GBR",
    "uk": "GBR",
    "usa": "USA",
    "united states": "USA",
    "vietnam": "VNM",
}


def _get_country_code(country: str) -> str:
    """Convert country name to ISO 3-letter code."""
    normalized = country.lower().strip()

    # Check our mapping
    if normalized in COUNTRY_CODES:
        return COUNTRY_CODES[normalized]

    # If already 3-letter code, return uppercase
    if len(country) == 3 and country.isalpha():
        return country.upper()

    # Return as-is (API might accept it)
    return country.upper()[:3]


def _fetch_indicator(
    indicator_id: str,
    country: str | None = None,
    sex: str | None = None,
    time_from: int | None = None,
    time_to: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch data for a specific indicator."""
    url = f"{ILO_API}/data/indicator/"

    params: dict[str, str | int] = {
        "id": indicator_id,
        "format": ".json",
        "type": "label",  # Use labels instead of codes
    }

    if country:
        params["ref_area"] = _get_country_code(country)
    if sex:
        sex_code = {"male": "SEX_M", "female": "SEX_F", "total": "SEX_T"}.get(
            sex.lower(), "SEX_T"
        )
        params["sex"] = sex_code
    if time_from:
        params["timefrom"] = time_from
    if time_to:
        params["timeto"] = time_to

    result = fetch_json(url, params)
    if isinstance(result, list):
        return result
    return []


@tool
def get_labor_indicators(country: str, indicators: str | None = None) -> str:
    """
    Get key labor market indicators for a country.

    Provides employment, unemployment, and labor force statistics
    from the International Labour Organization (ILO).

    Args:
        country: Country name (e.g., "Kenya", "Brazil") or ISO 3-letter code
        indicators: Optional comma-separated list of specific indicators:
                   employment_rate, unemployment_rate, labor_force_participation,
                   informal_employment, working_poverty, youth_unemployment,
                   youth_neet, women_managers, child_labor

    Returns:
        Labor market statistics with most recent available data
    """
    country_code = _get_country_code(country)

    # Determine which indicators to fetch
    if indicators:
        indicator_keys = [k.strip() for k in indicators.split(",")]
        # Validate
        invalid = [k for k in indicator_keys if k not in LABOR_INDICATORS]
        if invalid:
            valid_list = ", ".join(LABOR_INDICATORS.keys())
            return f"Unknown indicators: {', '.join(invalid)}\n\nValid options: {valid_list}"
    else:
        # Default to core indicators
        indicator_keys = [
            "employment_rate",
            "unemployment_rate",
            "labor_force_participation",
            "informal_employment",
            "youth_unemployment",
        ]

    try:
        output = [
            "=== Labor Market Indicators ===",
            f"Country: {country} ({country_code})",
            "Source: ILOSTAT (ILO)",
            "",
        ]

        results_found = False

        for key in indicator_keys:
            if key not in LABOR_INDICATORS:
                continue

            info = LABOR_INDICATORS[key]
            indicator_id = info["id"]

            try:
                data = _fetch_indicator(
                    indicator_id,
                    country=country_code,
                    sex="total",
                    time_from=2015,  # Recent data
                )

                if data:
                    results_found = True
                    # Get most recent value
                    # Sort by time descending
                    sorted_data = sorted(
                        data, key=lambda x: x.get("time", ""), reverse=True
                    )

                    latest = sorted_data[0]
                    value = latest.get("obs_value")
                    year = latest.get("time", "")
                    unit = info["unit"]

                    output.append(f"📊 {info['name']}")
                    output.append(f"   Value: {value} {unit} ({year})")
                    output.append(f"   {info['description']}")

                    # Show trend if we have multiple years
                    if len(sorted_data) >= 2:
                        prev = sorted_data[1]
                        prev_value = prev.get("obs_value")
                        prev_year = prev.get("time", "")
                        if prev_value and value:
                            try:
                                change = float(value) - float(prev_value)
                                direction = (
                                    "↑" if change > 0 else "↓" if change < 0 else "→"
                                )
                                output.append(
                                    f"   Trend: {direction} {abs(change):.1f} pp from {prev_year}"
                                )
                            except (ValueError, TypeError):
                                pass

                    output.append("")
                else:
                    output.append(f"📊 {info['name']}: No data available")
                    output.append("")

            except Exception as e:
                output.append(f"📊 {info['name']}: Error fetching data ({e})")
                output.append("")

        if not results_found:
            output.append("No labor statistics found for this country.")
            output.append("Try a different country or check the country name spelling.")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching labor indicators")
    except Exception as e:
        return format_error(e, "processing labor data")


@tool
def get_employment_by_gender(country: str, year: int | None = None) -> str:
    """
    Get gender-disaggregated employment statistics.

    Compares employment outcomes between men and women including
    employment rates, unemployment, and labor force participation.

    Args:
        country: Country name or ISO 3-letter code
        year: Optional specific year (default: most recent)

    Returns:
        Gender comparison of employment statistics
    """
    country_code = _get_country_code(country)

    # Indicators to compare by gender
    gender_indicators = [
        ("labor_force_participation", "Labor force participation"),
        ("employment_rate", "Employment rate"),
        ("unemployment_rate", "Unemployment rate"),
        ("women_managers", "Managers (% women)"),
    ]

    try:
        output = [
            "=== Employment by Gender ===",
            f"Country: {country} ({country_code})",
            "Source: ILOSTAT (ILO)",
            "",
            f"{'Indicator':<35} {'Male':>10} {'Female':>10} {'Gap':>10}",
            "-" * 67,
        ]

        for key, name in gender_indicators:
            if key not in LABOR_INDICATORS:
                continue

            info = LABOR_INDICATORS[key]
            indicator_id = info["id"]

            # Skip women_managers - it's already female-specific
            if key == "women_managers":
                try:
                    data = _fetch_indicator(
                        indicator_id, country=country_code, time_from=2015
                    )
                    if data:
                        sorted_data = sorted(
                            data, key=lambda x: x.get("time", ""), reverse=True
                        )
                        value = sorted_data[0].get("obs_value", "N/A")
                        output.append(f"{name:<35} {'N/A':>10} {value:>10} {'N/A':>10}")
                except Exception:
                    pass
                continue

            try:
                # Fetch male data
                male_data = _fetch_indicator(
                    indicator_id, country=country_code, sex="male", time_from=2015
                )
                # Fetch female data
                female_data = _fetch_indicator(
                    indicator_id, country=country_code, sex="female", time_from=2015
                )

                male_val: str | float = "N/A"
                female_val: str | float = "N/A"

                if male_data:
                    sorted_male = sorted(
                        male_data, key=lambda x: x.get("time", ""), reverse=True
                    )
                    male_val = sorted_male[0].get("obs_value", "N/A")

                if female_data:
                    sorted_female = sorted(
                        female_data, key=lambda x: x.get("time", ""), reverse=True
                    )
                    female_val = sorted_female[0].get("obs_value", "N/A")

                # Calculate gap
                gap: str | float = "N/A"
                try:
                    if isinstance(male_val, (int, float)) and isinstance(
                        female_val, (int, float)
                    ):
                        gap = float(male_val) - float(female_val)
                        gap_str = f"{gap:+.1f}"
                    else:
                        gap_str = "N/A"
                except (ValueError, TypeError):
                    gap_str = "N/A"

                m_str = f"{male_val}" if male_val != "N/A" else "N/A"
                f_str = f"{female_val}" if female_val != "N/A" else "N/A"

                output.append(f"{name:<35} {m_str:>10} {f_str:>10} {gap_str:>10}")

            except Exception:
                output.append(f"{name:<35} {'Error':>10} {'Error':>10} {'N/A':>10}")

        output.append("")
        output.append("Gap = Male - Female (positive means higher for men)")
        output.append("Data shown is most recent available (2015 onwards)")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching gender employment data")
    except Exception as e:
        return format_error(e, "processing gender data")


@tool
def get_labor_time_series(
    country: str,
    indicator: str,
    start_year: int = 2010,
    end_year: int | None = None,
) -> str:
    """
    Get time series data for a labor indicator.

    Shows how a labor market indicator has changed over time for a country.

    Args:
        country: Country name or ISO 3-letter code
        indicator: Indicator name - one of:
                  employment_rate, unemployment_rate, labor_force_participation,
                  informal_employment, working_poverty, youth_unemployment,
                  youth_neet, women_managers, child_labor
        start_year: Start year for time series (default 2010)
        end_year: End year (default: latest available)

    Returns:
        Time series data with values by year
    """
    country_code = _get_country_code(country)

    # Normalize indicator name
    indicator_key = indicator.lower().replace(" ", "_").replace("-", "_")

    if indicator_key not in LABOR_INDICATORS:
        valid_list = ", ".join(LABOR_INDICATORS.keys())
        return f"Unknown indicator: '{indicator}'\n\nValid options:\n{valid_list}"

    info = LABOR_INDICATORS[indicator_key]
    indicator_id = info["id"]

    try:
        data = _fetch_indicator(
            indicator_id,
            country=country_code,
            sex="total",
            time_from=start_year,
            time_to=end_year,
        )

        if not data:
            return f"No data found for {info['name']} in {country} ({start_year}-{end_year or 'present'})."

        # Sort by year
        sorted_data = sorted(data, key=lambda x: x.get("time", ""))

        output = [
            f"=== {info['name']} ===",
            f"Country: {country} ({country_code})",
            f"Period: {start_year} - {end_year or 'present'}",
            f"Unit: {info['unit']}",
            "",
            f"{'Year':<10} {'Value':>12}",
            "-" * 24,
        ]

        values: list[float] = []
        for row in sorted_data:
            year = row.get("time", "")
            value = row.get("obs_value")

            if value is not None:
                try:
                    val_float = float(value)
                    values.append(val_float)
                    output.append(f"{year:<10} {val_float:>12.1f}")
                except (ValueError, TypeError):
                    output.append(f"{year:<10} {value:>12}")

        # Calculate summary statistics
        if values:
            output.append("-" * 24)
            output.append(f"{'Average':<10} {sum(values)/len(values):>12.1f}")
            output.append(f"{'Min':<10} {min(values):>12.1f}")
            output.append(f"{'Max':<10} {max(values):>12.1f}")

            # Trend
            if len(values) >= 2:
                change = values[-1] - values[0]
                direction = (
                    "increased"
                    if change > 0
                    else "decreased" if change < 0 else "unchanged"
                )
                output.append("")
                output.append(
                    f"Overall change: {direction} by {abs(change):.1f} {info['unit']}"
                )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching labor time series")
    except Exception as e:
        return format_error(e, "processing time series data")


@tool
def search_labor_indicators(query: str) -> str:
    """
    Search available labor indicators by keyword.

    Find relevant ILO indicators based on topic keywords like
    "unemployment", "wages", "child labor", "safety", etc.

    Args:
        query: Search term (e.g., "youth", "wages", "informal", "safety")

    Returns:
        List of matching labor indicators with descriptions
    """
    query_lower = query.lower()

    matches = []
    for key, info in LABOR_INDICATORS.items():
        # Search in key, name, and description
        searchable = f"{key} {info['name']} {info['description']}".lower()
        if query_lower in searchable:
            matches.append((key, info))

    if not matches:
        output = [
            f"No indicators found matching '{query}'.",
            "",
            "Available categories:",
            "  - Employment: employment_rate, labor_force_participation",
            "  - Unemployment: unemployment_rate, youth_unemployment",
            "  - Vulnerable work: informal_employment, working_poverty",
            "  - Youth: youth_unemployment, youth_neet, child_labor",
            "  - Gender: women_managers",
            "  - Conditions: excessive_hours, average_wages, fatal_injuries",
        ]
        return "\n".join(output)

    output = [
        f"=== Labor Indicators matching '{query}' ===",
        f"Found: {len(matches)} indicators",
        "",
    ]

    for key, info in matches:
        output.append(f"📊 {key}")
        output.append(f"   Name: {info['name']}")
        output.append(f"   Description: {info['description']}")
        output.append(f"   Unit: {info['unit']}")
        output.append(f"   ILO ID: {info['id']}")
        output.append("")

    output.append("Use get_labor_indicators(country, indicators='...') to fetch data.")

    return "\n".join(output)
