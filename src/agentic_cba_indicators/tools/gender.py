"""
Gender statistics tools using World Bank Gender Data Portal API.

Provides gender-disaggregated indicators for education, health,
employment, and economic participation.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
No API key required.
"""

from typing import Any

from strands import tool

from ._http import APIError, fetch_json, format_error

# World Bank API v2 base URL
WB_API = "https://api.worldbank.org/v2"

# Gender-specific indicators from WDI
GENDER_INDICATORS = {
    # Education
    "literacy_female": {
        "id": "SE.ADT.LITR.FE.ZS",
        "name": "Female literacy rate (% ages 15+)",
        "category": "Education",
    },
    "literacy_male": {
        "id": "SE.ADT.LITR.MA.ZS",
        "name": "Male literacy rate (% ages 15+)",
        "category": "Education",
    },
    "school_enrollment_primary_female": {
        "id": "SE.PRM.ENRR.FE",
        "name": "School enrollment, primary, female (% gross)",
        "category": "Education",
    },
    "school_enrollment_primary_male": {
        "id": "SE.PRM.ENRR.MA",
        "name": "School enrollment, primary, male (% gross)",
        "category": "Education",
    },
    "school_enrollment_secondary_female": {
        "id": "SE.SEC.ENRR.FE",
        "name": "School enrollment, secondary, female (% gross)",
        "category": "Education",
    },
    "school_enrollment_secondary_male": {
        "id": "SE.SEC.ENRR.MA",
        "name": "School enrollment, secondary, male (% gross)",
        "category": "Education",
    },
    "school_enrollment_tertiary_female": {
        "id": "SE.TER.ENRR.FE",
        "name": "School enrollment, tertiary, female (% gross)",
        "category": "Education",
    },
    "school_enrollment_tertiary_male": {
        "id": "SE.TER.ENRR.MA",
        "name": "School enrollment, tertiary, male (% gross)",
        "category": "Education",
    },
    # Employment
    "labor_force_female": {
        "id": "SL.TLF.CACT.FE.ZS",
        "name": "Labor force participation rate, female (% ages 15+)",
        "category": "Employment",
    },
    "labor_force_male": {
        "id": "SL.TLF.CACT.MA.ZS",
        "name": "Labor force participation rate, male (% ages 15+)",
        "category": "Employment",
    },
    "unemployment_female": {
        "id": "SL.UEM.TOTL.FE.ZS",
        "name": "Unemployment, female (% of female labor force)",
        "category": "Employment",
    },
    "unemployment_male": {
        "id": "SL.UEM.TOTL.MA.ZS",
        "name": "Unemployment, male (% of male labor force)",
        "category": "Employment",
    },
    "employment_agriculture_female": {
        "id": "SL.AGR.EMPL.FE.ZS",
        "name": "Employment in agriculture, female (% of female employment)",
        "category": "Employment",
    },
    "employment_agriculture_male": {
        "id": "SL.AGR.EMPL.MA.ZS",
        "name": "Employment in agriculture, male (% of male employment)",
        "category": "Employment",
    },
    "self_employed_female": {
        "id": "SL.EMP.SELF.FE.ZS",
        "name": "Self-employed, female (% of female employment)",
        "category": "Employment",
    },
    "self_employed_male": {
        "id": "SL.EMP.SELF.MA.ZS",
        "name": "Self-employed, male (% of male employment)",
        "category": "Employment",
    },
    "vulnerable_employment_female": {
        "id": "SL.EMP.VULN.FE.ZS",
        "name": "Vulnerable employment, female (% of female employment)",
        "category": "Employment",
    },
    "vulnerable_employment_male": {
        "id": "SL.EMP.VULN.MA.ZS",
        "name": "Vulnerable employment, male (% of male employment)",
        "category": "Employment",
    },
    # Health
    "life_expectancy_female": {
        "id": "SP.DYN.LE00.FE.IN",
        "name": "Life expectancy at birth, female (years)",
        "category": "Health",
    },
    "life_expectancy_male": {
        "id": "SP.DYN.LE00.MA.IN",
        "name": "Life expectancy at birth, male (years)",
        "category": "Health",
    },
    "mortality_adult_female": {
        "id": "SP.DYN.AMRT.FE",
        "name": "Mortality rate, adult, female (per 1,000)",
        "category": "Health",
    },
    "mortality_adult_male": {
        "id": "SP.DYN.AMRT.MA",
        "name": "Mortality rate, adult, male (per 1,000)",
        "category": "Health",
    },
    "maternal_mortality": {
        "id": "SH.STA.MMRT",
        "name": "Maternal mortality ratio (per 100,000 live births)",
        "category": "Health",
    },
    # Economic
    "account_female": {
        "id": "FX.OWN.TOTL.FE.ZS",
        "name": "Account ownership, female (% age 15+)",
        "category": "Economic",
    },
    "account_male": {
        "id": "FX.OWN.TOTL.MA.ZS",
        "name": "Account ownership, male (% age 15+)",
        "category": "Economic",
    },
    # Empowerment
    "parliament_seats_female": {
        "id": "SG.GEN.PARL.ZS",
        "name": "Proportion of seats held by women in parliament (%)",
        "category": "Empowerment",
    },
    "firms_female_ownership": {
        "id": "IC.FRM.FEMO.ZS",
        "name": "Firms with female participation in ownership (%)",
        "category": "Empowerment",
    },
    "firms_female_top_manager": {
        "id": "IC.FRM.FEMM.ZS",
        "name": "Firms with female top manager (%)",
        "category": "Empowerment",
    },
}

# Country name to ISO code mapping
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
    "world": "WLD",
}


def _get_country_code(country: str) -> str:
    """Convert country name to ISO 3-letter code."""
    normalized = country.lower().strip()
    if normalized in COUNTRY_CODES:
        return COUNTRY_CODES[normalized]
    if len(country) == 3 and country.isalpha():
        return country.upper()
    return country.upper()[:3]


def _fetch_wb_indicator(
    country: str, indicator_id: str, start_year: int = 2010, end_year: int = 2024
) -> list[dict[str, Any]]:
    """Fetch World Bank indicator data."""
    url = f"{WB_API}/country/{country}/indicator/{indicator_id}"
    params = {
        "format": "json",
        "date": f"{start_year}:{end_year}",
        "per_page": 100,
    }

    result = fetch_json(url, params)

    # WB API returns [metadata, data] array
    if isinstance(result, list) and len(result) >= 2:
        return result[1] if result[1] else []
    return []


def _get_latest_value(
    data: list[dict[str, Any]],
) -> tuple[Any | None, str | None]:
    """Get most recent non-null value and year from WB data."""
    for item in sorted(data, key=lambda x: x.get("date", ""), reverse=True):
        if item.get("value") is not None:
            return item["value"], item.get("date")
    return None, None


@tool
def get_gender_indicators(country: str, category: str | None = None) -> str:
    """
    Get gender statistics for a country from World Bank.

    Provides gender-disaggregated data on education, health, employment,
    and economic participation.

    Args:
        country: Country name (e.g., "Kenya", "Brazil") or ISO 3-letter code
        category: Optional filter - "Education", "Employment", "Health", "Economic", "Empowerment"

    Returns:
        Gender indicators with male/female comparisons
    """
    country_code = _get_country_code(country)

    # Filter by category if specified
    if category:
        category_lower = category.lower()
        indicators_to_fetch = {
            k: v
            for k, v in GENDER_INDICATORS.items()
            if v["category"].lower() == category_lower
        }
        if not indicators_to_fetch:
            valid = ", ".join(
                sorted({v["category"] for v in GENDER_INDICATORS.values()})
            )
            return f"Unknown category: '{category}'. Valid categories: {valid}"
    else:
        # Default to a selection of key indicators
        key_indicators = [
            "literacy_female",
            "literacy_male",
            "labor_force_female",
            "labor_force_male",
            "life_expectancy_female",
            "life_expectancy_male",
            "parliament_seats_female",
        ]
        indicators_to_fetch = {
            k: v for k, v in GENDER_INDICATORS.items() if k in key_indicators
        }

    try:
        output = [
            "=== Gender Statistics ===",
            f"Country: {country} ({country_code})",
            f"Category: {category or 'Key indicators'}",
            "Source: World Bank Gender Data Portal",
            "",
        ]

        # Group indicators by category
        by_category: dict[str, list[tuple[str, dict]]] = {}
        for key, info in indicators_to_fetch.items():
            cat = info["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((key, info))

        results_found = False

        for cat in sorted(by_category.keys()):
            output.append(f"📊 {cat}")
            output.append("-" * 40)

            for _key, info in by_category[cat]:
                try:
                    data = _fetch_wb_indicator(country_code, info["id"])
                    value, year = _get_latest_value(data)

                    if value is not None:
                        results_found = True
                        output.append(f"  {info['name']}")
                        output.append(f"    Value: {value:.1f} ({year})")
                    else:
                        output.append(f"  {info['name']}: No data")

                except Exception as e:
                    output.append(f"  {info['name']}: Error ({e})")

            output.append("")

        if not results_found:
            output.append("No gender data found for this country.")
            output.append("Try a different country or check the country name.")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching gender indicators")
    except Exception as e:
        return format_error(e, "processing gender data")


@tool
def compare_gender_gaps(country: str) -> str:
    """
    Compare gender gaps across key indicators for a country.

    Shows the difference between male and female outcomes in
    education, employment, and health.

    Args:
        country: Country name or ISO 3-letter code

    Returns:
        Gender gap analysis showing male-female differences
    """
    country_code = _get_country_code(country)

    # Paired indicators for comparison
    comparisons = [
        ("Literacy rate", "literacy_female", "literacy_male"),
        ("Labor force participation", "labor_force_female", "labor_force_male"),
        ("Unemployment rate", "unemployment_female", "unemployment_male"),
        ("Life expectancy", "life_expectancy_female", "life_expectancy_male"),
        (
            "School enrollment (primary)",
            "school_enrollment_primary_female",
            "school_enrollment_primary_male",
        ),
        (
            "School enrollment (secondary)",
            "school_enrollment_secondary_female",
            "school_enrollment_secondary_male",
        ),
        (
            "Agricultural employment",
            "employment_agriculture_female",
            "employment_agriculture_male",
        ),
        ("Bank account ownership", "account_female", "account_male"),
    ]

    try:
        output = [
            "=== Gender Gap Analysis ===",
            f"Country: {country} ({country_code})",
            "Source: World Bank",
            "",
            f"{'Indicator':<35} {'Female':>10} {'Male':>10} {'Gap':>10}",
            "-" * 67,
        ]

        for name, female_key, male_key in comparisons:
            female_info = GENDER_INDICATORS.get(female_key)
            male_info = GENDER_INDICATORS.get(male_key)

            if not female_info or not male_info:
                continue

            try:
                female_data = _fetch_wb_indicator(country_code, female_info["id"])
                male_data = _fetch_wb_indicator(country_code, male_info["id"])

                female_val, _female_year = _get_latest_value(female_data)
                male_val, _male_year = _get_latest_value(male_data)

                f_str = f"{female_val:.1f}" if female_val is not None else "N/A"
                m_str = f"{male_val:.1f}" if male_val is not None else "N/A"

                # Calculate gap (female - male)
                if female_val is not None and male_val is not None:
                    gap = float(female_val) - float(male_val)
                    gap_str = f"{gap:+.1f}"
                else:
                    gap_str = "N/A"

                output.append(f"{name:<35} {f_str:>10} {m_str:>10} {gap_str:>10}")

            except Exception:
                output.append(f"{name:<35} {'Error':>10} {'Error':>10} {'N/A':>10}")

        output.append("-" * 67)
        output.append("")
        output.append("Gap = Female - Male")
        output.append(
            "Positive gap: Women score higher | Negative gap: Men score higher"
        )
        output.append("")

        # Add single-gender indicators
        output.append("Additional indicators:")
        single_indicators = [
            "parliament_seats_female",
            "firms_female_ownership",
            "maternal_mortality",
        ]

        for key in single_indicators:
            info = GENDER_INDICATORS.get(key)
            if info:
                try:
                    data = _fetch_wb_indicator(country_code, info["id"])
                    value, year = _get_latest_value(data)
                    if value is not None:
                        output.append(f"  {info['name']}: {value:.1f} ({year})")
                except Exception:
                    pass

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching gender gap data")
    except Exception as e:
        return format_error(e, "processing gender gaps")


@tool
def get_gender_time_series(
    country: str,
    indicator: str,
    start_year: int = 2000,
    end_year: int = 2024,
) -> str:
    """
    Get time series for a gender indicator.

    Shows how a gender indicator has changed over time for a country.

    Args:
        country: Country name or ISO 3-letter code
        indicator: Indicator key (e.g., "literacy_female", "labor_force_female")
        start_year: Start year (default 2000)
        end_year: End year (default 2024)

    Returns:
        Time series data by year
    """
    country_code = _get_country_code(country)

    # Normalize indicator name
    indicator_key = indicator.lower().replace(" ", "_").replace("-", "_")

    if indicator_key not in GENDER_INDICATORS:
        categories: dict[str, list[str]] = {}
        for k, v in GENDER_INDICATORS.items():
            cat = v["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(k)

        output = [f"Unknown indicator: '{indicator}'", "", "Available indicators:"]
        for cat, keys in sorted(categories.items()):
            output.append(f"\n{cat}:")
            output.extend(f"  - {k}" for k in sorted(keys))
        return "\n".join(output)

    info = GENDER_INDICATORS[indicator_key]

    try:
        data = _fetch_wb_indicator(country_code, info["id"], start_year, end_year)

        if not data:
            return f"No data found for {info['name']} in {country} ({start_year}-{end_year})."

        # Sort by year
        sorted_data = sorted(data, key=lambda x: x.get("date", ""))

        output = [
            f"=== {info['name']} ===",
            f"Country: {country} ({country_code})",
            f"Category: {info['category']}",
            f"Period: {start_year} - {end_year}",
            "",
            f"{'Year':<10} {'Value':>12}",
            "-" * 24,
        ]

        values = []
        for item in sorted_data:
            year = item.get("date", "")
            value = item.get("value")

            if value is not None:
                values.append(float(value))
                output.append(f"{year:<10} {value:>12.1f}")

        if values:
            output.append("-" * 24)
            output.append(f"{'Average':<10} {sum(values) / len(values):>12.1f}")
            output.append(f"{'Min':<10} {min(values):>12.1f}")
            output.append(f"{'Max':<10} {max(values):>12.1f}")

            if len(values) >= 2:
                change = values[-1] - values[0]
                direction = (
                    "increased"
                    if change > 0
                    else "decreased"
                    if change < 0
                    else "unchanged"
                )
                output.append("")
                output.append(f"Overall change: {direction} by {abs(change):.1f}")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching gender time series")
    except Exception as e:
        return format_error(e, "processing time series")


@tool
def search_gender_indicators(query: str) -> str:
    """
    Search available gender indicators by keyword.

    Find relevant gender indicators based on topic keywords like
    "education", "employment", "health", "literacy", etc.

    Args:
        query: Search term (e.g., "education", "employment", "mortality")

    Returns:
        List of matching gender indicators
    """
    query_lower = query.lower()

    matches = []
    for key, info in GENDER_INDICATORS.items():
        searchable = f"{key} {info['name']} {info['category']}".lower()
        if query_lower in searchable:
            matches.append((key, info))

    if not matches:
        categories = sorted({v["category"] for v in GENDER_INDICATORS.values()})
        return (
            f"No indicators found matching '{query}'.\n\n"
            f"Available categories: {', '.join(categories)}\n\n"
            "Try searching for: education, employment, health, economic, empowerment, "
            "literacy, mortality, labor, unemployment"
        )

    output = [
        f"=== Gender Indicators matching '{query}' ===",
        f"Found: {len(matches)} indicators",
        "",
    ]

    # Group by category
    by_category: dict[str, list[tuple[str, dict]]] = {}
    for key, info in matches:
        cat = info["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((key, info))

    for cat in sorted(by_category.keys()):
        output.append(f"📊 {cat}")
        for key, info in by_category[cat]:
            output.append(f"  • {key}")
            output.append(f"    {info['name']}")
            output.append(f"    ID: {info['id']}")
        output.append("")

    output.append("Use get_gender_indicators(country, category='...') to fetch data.")
    output.append("Use get_gender_time_series(country, indicator='...') for trends.")

    return "\n".join(output)
