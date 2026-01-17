"""
UN SDG API tools for Sustainable Development Goal indicator data.

Provides access to official SDG indicator progress data from the
UN Statistics Division. Free, no API key required.

API Documentation: https://unstats.un.org/sdgs/UNSDGAPIV5/swagger/
"""

from strands import tool

from ._http import APIError, fetch_json, format_error
from ._mappings import COUNTRY_CODES_SDG, normalize_key

# UN SDG API base URL
SDG_BASE = "https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg"

# SDG Goals with descriptions
SDG_GOALS = {
    1: "No Poverty",
    2: "Zero Hunger",
    3: "Good Health and Well-being",
    4: "Quality Education",
    5: "Gender Equality",
    6: "Clean Water and Sanitation",
    7: "Affordable and Clean Energy",
    8: "Decent Work and Economic Growth",
    9: "Industry, Innovation and Infrastructure",
    10: "Reduced Inequalities",
    11: "Sustainable Cities and Communities",
    12: "Responsible Consumption and Production",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace, Justice and Strong Institutions",
    17: "Partnerships for the Goals",
}

# Mapping CBA Principles to relevant SDG Goals
CBA_TO_SDG = {
    "1": {  # Natural Environment
        "goals": [6, 13, 14, 15],
        "description": "Environmental protection and climate action",
    },
    "2": {  # Social Well-being
        "goals": [1, 2, 3, 4, 5, 10],
        "description": "Health, education, equity and inclusion",
    },
    "3": {  # Economic Prosperity
        "goals": [8, 9, 12],
        "description": "Decent work, industry and sustainable consumption",
    },
    "4": {  # Diversity
        "goals": [14, 15],
        "description": "Biodiversity and ecosystem diversity",
    },
    "5": {  # Connectivity
        "goals": [9, 11, 15],
        "description": "Infrastructure and ecological connectivity",
    },
    "6": {  # Adaptive Capacity
        "goals": [13, 11],
        "description": "Climate resilience and risk reduction",
    },
    "7": {  # Harmony
        "goals": [12, 15, 16, 17],
        "description": "Sustainable practices and partnerships",
    },
}


def _get_geo_code(country: str) -> int | None:
    """Convert country name to UN GeoArea code."""
    normalized = normalize_key(country)
    return COUNTRY_CODES_SDG.get(normalized)


def _fetch_goals() -> list[dict]:
    """Fetch list of SDG goals."""
    url = f"{SDG_BASE}/Goal/List"
    result = fetch_json(url)
    return result if isinstance(result, list) else []


def _fetch_targets(goal: int) -> list[dict]:
    """Fetch targets for a specific goal."""
    url = f"{SDG_BASE}/Goal/{goal}/Target/List"
    result = fetch_json(url)
    return result if isinstance(result, list) else []


def _fetch_series_data(
    series_code: str, geo_area: int, page_size: int = 50
) -> list[dict]:
    """Fetch time series data for a specific indicator series."""
    url = f"{SDG_BASE}/Series/Data"
    params = {
        "seriesCode": series_code,
        "geoAreaCode": geo_area,
        "pageSize": page_size,
    }
    result = fetch_json(url, params)
    return result if isinstance(result, list) else []


@tool
def get_sdg_progress(country: str, goal: int | None = None) -> str:
    """
    Get SDG indicator progress for a country.

    Provides summary of Sustainable Development Goal progress including
    available indicators and recent data points.

    Args:
        country: Country name (e.g., "Kenya", "Brazil") or region (e.g., "Africa", "World")
        goal: Specific SDG goal number (1-17). If not provided, shows overview of all goals.

    Returns:
        SDG progress summary with available indicators and values
    """
    geo_code = _get_geo_code(country)
    if not geo_code:
        # Try numeric code directly
        try:
            geo_code = int(country)
        except ValueError:
            return f"Unknown country: {country}. Try common names like: Kenya, Brazil, India, or 'World' for global data."

    try:
        output = [
            "=== SDG Progress Report ===",
            f"Country/Region: {country.title()}",
            "",
        ]

        if goal:
            # Detailed view for specific goal
            if goal not in SDG_GOALS:
                return f"Invalid goal number: {goal}. Valid range is 1-17."

            goal_name = SDG_GOALS[goal]
            output.append(f"Goal {goal}: {goal_name}")
            output.append("=" * 50)
            output.append("")

            # Fetch targets for this goal
            try:
                targets = _fetch_targets(goal)
                if isinstance(targets, list):
                    output.append(f"Targets ({len(targets)}):")
                    for target in targets[:10]:  # Limit display
                        code = target.get("code", "")
                        title = target.get("title", "")
                        if len(title) > 80:
                            title = title[:77] + "..."
                        output.append(f"  {code}: {title}")
                    if len(targets) > 10:
                        output.append(f"  ... and {len(targets) - 10} more targets")
            except Exception:
                output.append("(Target details not available)")

            output.append("")

            # CBA alignment
            for principle, mapping in CBA_TO_SDG.items():
                if goal in mapping["goals"]:
                    output.append(
                        f"CBA Alignment: Principle {principle} ({mapping['description']})"
                    )
                    break

        else:
            # Overview of all goals
            output.append("SDG Goals Overview:")
            output.append("")
            for g, name in SDG_GOALS.items():
                output.append(f"  Goal {g:2d}: {name}")

            output.append("")
            output.append("CBA Principle Alignment:")
            output.append("")
            for principle, mapping in CBA_TO_SDG.items():
                goal_list = ", ".join(str(g) for g in mapping["goals"])
                output.append(f"  Principle {principle}: Goals {goal_list}")
                output.append(f"    → {mapping['description']}")

        output.append("")
        output.append("Use search_sdg_indicators(query) to find specific indicators.")
        output.append(
            "Use get_sdg_series_data(series_code, country) for time series data."
        )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching SDG data")
    except Exception as e:
        return format_error(e, "processing SDG data")


@tool
def search_sdg_indicators(query: str, goal: int | None = None) -> str:
    """
    Search for SDG indicators by keyword.

    Finds SDG indicator series related to your search query.
    Results include series codes that can be used with get_sdg_series_data.

    Args:
        query: Search term (e.g., "poverty", "water", "education", "emissions")
        goal: Optional goal number to limit search (1-17)

    Returns:
        Matching SDG indicators with series codes and descriptions
    """
    try:
        # Fetch all series
        url = f"{SDG_BASE}/Series/List"
        all_series = fetch_json(url)

        if not isinstance(all_series, list):
            return "Unable to retrieve SDG indicator list."

        # Filter by query
        query_lower = query.lower()
        matches = []

        for series in all_series:
            code = series.get("code", "")
            description = series.get("description", "")
            goal_code = series.get("goal", "")

            # Filter by goal if specified
            if goal:
                try:
                    series_goal = (
                        int(goal_code.split(".")[0])
                        if "." in str(goal_code)
                        else int(goal_code)
                    )
                    if series_goal != goal:
                        continue
                except (ValueError, AttributeError):
                    pass

            # Check if query matches
            if query_lower in description.lower() or query_lower in code.lower():
                matches.append(
                    {
                        "code": code,
                        "description": description,
                        "goal": goal_code,
                    }
                )

        if not matches:
            return f"No SDG indicators found matching '{query}'. Try broader terms like 'poverty', 'health', 'water', 'education'."

        output = [
            "=== SDG Indicator Search Results ===",
            f"Query: '{query}'" + (f" (Goal {goal})" if goal else ""),
            f"Found: {len(matches)} indicators",
            "",
        ]

        # Limit results
        display_matches = matches[:15]

        for match in display_matches:
            desc = match["description"]
            if len(desc) > 100:
                desc = desc[:97] + "..."
            output.append(f"[{match['code']}] Goal {match['goal']}")
            output.append(f"  {desc}")
            output.append("")

        if len(matches) > 15:
            output.append(f"... and {len(matches) - 15} more indicators")
            output.append("Try a more specific query to narrow results.")

        output.append("")
        output.append(
            "Use get_sdg_series_data(series_code, country) to get data for a specific indicator."
        )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "searching SDG indicators")
    except Exception as e:
        return format_error(e, "processing SDG search")


@tool
def get_sdg_series_data(series_code: str, country: str, years: int = 10) -> str:
    """
    Get time series data for a specific SDG indicator.

    Retrieves historical data points for an indicator series.
    Use search_sdg_indicators() first to find the series code.

    Args:
        series_code: SDG series code (e.g., "SI_POV_DAY1", "EN_ATM_CO2")
        country: Country name or "World" for global data
        years: Number of recent years to include (default 10)

    Returns:
        Time series data with values, units, and trend information
    """
    geo_code = _get_geo_code(country)
    if not geo_code:
        try:
            geo_code = int(country)
        except ValueError:
            return f"Unknown country: {country}. Use common country names or 'World'."

    try:
        data = _fetch_series_data(series_code, geo_code)

        if not isinstance(data, dict) or "data" not in data:
            return f"No data found for series {series_code} in {country}."

        records = data.get("data", [])
        if not records:
            return f"No data points available for {series_code} in {country}."

        # Get series metadata
        series_info = data.get("series", {})
        description = series_info.get("description", series_code)
        goal = series_info.get("goal", "")
        unit = ""

        # Extract time series values
        time_series = {}
        for record in records:
            year = record.get("timePeriodStart")
            value = record.get("value")
            if year and value is not None:
                time_series[year] = value
                if not unit:
                    unit = record.get("units", "")

        if not time_series:
            return f"No valid data points for {series_code} in {country}."

        # Sort by year and get recent
        sorted_years = sorted(time_series.keys(), reverse=True)[:years]
        sorted_years.reverse()  # Chronological order

        output = [
            "=== SDG Indicator Data ===",
            f"Series: {series_code}",
            f"Description: {description[:100]}{'...' if len(description) > 100 else ''}",
            f"Goal: {goal}",
            f"Country: {country.title()}",
            f"Unit: {unit}" if unit else "",
            "",
            "Time Series:",
            "",
        ]

        # Display data
        values = []
        for year in sorted_years:
            val = time_series[year]
            values.append(val)
            output.append(
                f"  {year}: {val:,.2f}"
                if isinstance(val, float)
                else f"  {year}: {val}"
            )

        # Calculate trend
        if len(values) >= 2:
            first = values[0]
            last = values[-1]
            if first and last and first != 0:
                change = ((last - first) / abs(first)) * 100
                trend = "↑" if change > 0 else "↓" if change < 0 else "→"
                output.append("")
                output.append(f"Trend: {trend} {abs(change):.1f}% change over period")

        output.append("")

        # CBA principle mapping
        if goal:
            try:
                goal_num = int(str(goal).split(".")[0])
                for principle, mapping in CBA_TO_SDG.items():
                    if goal_num in mapping["goals"]:
                        output.append(
                            f"CBA Alignment: Principle {principle} - {mapping['description']}"
                        )
                        break
            except ValueError:
                pass

        return "\n".join(output)

    except APIError as e:
        return format_error(e, f"fetching data for {series_code}")
    except Exception as e:
        return format_error(e, "processing SDG series data")


@tool
def get_sdg_for_cba_principle(principle: str) -> str:
    """
    Get SDG goals and indicators aligned with a CBA principle.

    Maps Cost-Benefit Analysis principles to relevant SDG goals
    to help identify which SDG indicators are relevant for your assessment.

    Args:
        principle: CBA principle number (1-7) or name
            1 = Natural Environment
            2 = Social Well-being
            3 = Economic Prosperity
            4 = Diversity
            5 = Connectivity
            6 = Adaptive Capacity
            7 = Harmony

    Returns:
        SDG goals aligned with the CBA principle and suggested indicators
    """
    # Map principle names to numbers
    principle_names = {
        "natural environment": "1",
        "social well-being": "2",
        "social wellbeing": "2",
        "economic prosperity": "3",
        "diversity": "4",
        "connectivity": "5",
        "adaptive capacity": "6",
        "harmony": "7",
    }

    p_str = str(principle).strip().lower()
    if p_str in principle_names:
        p_str = principle_names[p_str]

    if p_str not in CBA_TO_SDG:
        principles_list = "\n".join(
            f"  {k}: {v['description']}" for k, v in CBA_TO_SDG.items()
        )
        return f"Unknown principle: {principle}\n\nAvailable principles:\n{principles_list}"

    mapping = CBA_TO_SDG[p_str]
    goals = mapping["goals"]
    desc = mapping["description"]

    output = [
        f"=== CBA Principle {p_str} → SDG Alignment ===",
        f"Focus: {desc}",
        "",
        "Aligned SDG Goals:",
        "",
    ]

    for goal in goals:
        goal_int = goal if isinstance(goal, int) else int(str(goal))
        goal_name = SDG_GOALS.get(goal_int, "Unknown")
        output.append(f"  Goal {goal}: {goal_name}")

    output.append("")
    output.append("Suggested Indicator Searches:")
    output.append("")

    # Suggest searches based on principle
    suggestions = {
        "1": ["emissions", "forest", "water quality", "biodiversity"],
        "2": ["poverty", "health", "education", "inequality"],
        "3": ["employment", "GDP", "productivity", "income"],
        "4": ["species", "ecosystem", "genetic"],
        "5": ["infrastructure", "transport", "protected area"],
        "6": ["disaster", "resilience", "climate adaptation"],
        "7": ["sustainable", "partnership", "resource efficiency"],
    }

    output.extend(
        f"  - search_sdg_indicators('{term}')" for term in suggestions.get(p_str, [])
    )

    output.append("")
    output.append("Use these to find specific indicators for your CBA assessment.")

    return "\n".join(output)
