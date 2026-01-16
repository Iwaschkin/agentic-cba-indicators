"""
ISRIC SoilGrids API tools for soil property queries.

SoilGrids provides global soil property predictions at 250m resolution
for various depths (0-200cm). Free, no API key required.

API Documentation: https://rest.isric.org/soilgrids/v2.0/docs
"""

from strands import tool

from ._geo import format_location, geocode_or_parse
from ._http import APIError, fetch_json, format_error

# SoilGrids API base URL
SOILGRIDS_BASE = "https://rest.isric.org/soilgrids/v2.0"

# Available soil properties
SOIL_PROPERTIES = {
    "soc": (
        "Soil Organic Carbon",
        "g/kg",
        "dg/kg",
        10,
    ),  # name, display unit, API unit, divisor
    "bdod": ("Bulk Density", "kg/dm³", "cg/cm³", 100),
    "cec": ("Cation Exchange Capacity", "cmol(+)/kg", "mmol(+)/kg", 10),
    "cfvo": ("Coarse Fragments", "%", "cm³/dm³", 10),
    "clay": ("Clay Content", "%", "g/kg", 10),
    "sand": ("Sand Content", "%", "g/kg", 10),
    "silt": ("Silt Content", "%", "g/kg", 10),
    "nitrogen": ("Total Nitrogen", "g/kg", "cg/kg", 10),
    "phh2o": ("pH (H₂O)", "", "pH×10", 10),
    "ocd": ("Organic Carbon Density", "kg/m³", "hg/m³", 10),
}

# Standard depth intervals
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]

# Depth ranges for aggregation
DEPTH_MIDPOINTS = {
    "0-5cm": 2.5,
    "5-15cm": 10,
    "15-30cm": 22.5,
    "30-60cm": 45,
    "60-100cm": 80,
    "100-200cm": 150,
}

# USDA Soil Texture Triangle classes
TEXTURE_CLASSES = [
    ("Clay", lambda s, si, c: c >= 40 and s <= 45 and si < 40),
    ("Silty Clay", lambda s, si, c: c >= 40 and si >= 40),
    ("Sandy Clay", lambda s, si, c: c >= 35 and s > 45),
    ("Clay Loam", lambda s, si, c: 27 <= c < 40 and 20 <= s <= 45),
    ("Silty Clay Loam", lambda s, si, c: 27 <= c < 40 and s < 20),
    ("Sandy Clay Loam", lambda s, si, c: 20 <= c < 35 and s > 45 and si < 28),
    ("Loam", lambda s, si, c: 7 <= c < 27 and 28 <= si < 50 and s <= 52),
    ("Silt Loam", lambda s, si, c: (si >= 50 and c < 27) or (50 <= si < 80 and c < 12)),
    ("Silt", lambda s, si, c: si >= 80 and c < 12),
    ("Sandy Loam", lambda s, si, c: c < 20 and (s >= 52 or (43 <= s < 52 and si < 50))),
    ("Loamy Sand", lambda s, si, c: c < 15 and s >= 70 and s < 85),
    ("Sand", lambda s, si, c: c < 10 and s >= 85),
]


def _classify_texture(sand: float, silt: float, clay: float) -> str:
    """Classify soil texture using USDA texture triangle."""
    for name, condition in TEXTURE_CLASSES:
        if condition(sand, silt, clay):
            return name
    return "Loam"  # Default fallback


def _fetch_soil_data(
    lat: float, lon: float, properties: list[str], depths: list[str]
) -> dict:
    """
    Fetch soil data from SoilGrids API.

    Args:
        lat: Latitude
        lon: Longitude
        properties: List of soil properties to query
        depths: List of depth intervals

    Returns:
        API response with property values

    Raises:
        APIError: On API errors
    """
    url = f"{SOILGRIDS_BASE}/properties/query"

    # Build query parameters
    params = {
        "lon": lon,
        "lat": lat,
        "property": properties,
        "depth": depths,
        "value": "mean",
    }

    data = fetch_json(url, params)

    if not isinstance(data, dict):
        raise APIError("Unexpected response format from SoilGrids")

    if "properties" not in data or "layers" not in data.get("properties", {}):
        raise APIError("Invalid response structure from SoilGrids")

    return data


def _extract_value(layer: dict, depth: str) -> float | None:
    """Extract mean value for a specific depth from layer data."""
    depths_data = layer.get("depths", [])
    for d in depths_data:
        if d.get("label") == depth:
            values = d.get("values", {})
            return values.get("mean")
    return None


@tool
def get_soil_properties(
    location: str,
    properties: str = "soc,clay,sand,phh2o",
    depth: str = "0-30cm",
) -> str:
    """
    Get soil properties at a location from ISRIC SoilGrids.

    Available properties: soc (organic carbon), bdod (bulk density),
    cec (cation exchange), cfvo (coarse fragments), clay, sand, silt,
    nitrogen, phh2o (pH), ocd (organic carbon density).

    Args:
        location: City name or coordinates as "lat,lon"
        properties: Comma-separated property codes (default: "soc,clay,sand,phh2o")
        depth: Depth interval - "0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm", or "0-30cm" for averaged

    Returns:
        Soil property values at the specified depth
    """
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    # Parse properties
    prop_list = [p.strip().lower() for p in properties.split(",")]
    invalid = [p for p in prop_list if p not in SOIL_PROPERTIES]
    if invalid:
        available = ", ".join(SOIL_PROPERTIES.keys())
        return f"Unknown properties: {', '.join(invalid)}. Available: {available}"

    # Handle aggregated depth
    if depth == "0-30cm":
        depths_to_query = ["0-5cm", "5-15cm", "15-30cm"]
    else:
        if depth not in DEPTHS:
            return f"Invalid depth: {depth}. Available: {', '.join(DEPTHS)} or '0-30cm'"
        depths_to_query = [depth]

    try:
        data = _fetch_soil_data(lat, lon, prop_list, depths_to_query)

        layers = data["properties"]["layers"]
        location_str = format_location(lat, lon)

        output = [
            "=== Soil Properties ===",
            f"Location: {location} ({location_str})",
            f"Depth: {depth}",
            "Source: ISRIC SoilGrids (250m resolution)",
            "",
        ]

        for layer in layers:
            prop_name = layer.get("name", "unknown")
            if prop_name not in SOIL_PROPERTIES:
                continue

            display_name, unit, api_unit, divisor = SOIL_PROPERTIES[prop_name]

            # Get values for each depth and average if needed
            values = []
            for d in depths_to_query:
                val = _extract_value(layer, d)
                if val is not None:
                    values.append(val)

            if values:
                # Average across depths and convert units
                avg = sum(values) / len(values) / divisor
                output.append(f"{display_name}: {avg:.2f} {unit}")
            else:
                output.append(f"{display_name}: No data available")

        output.append("")
        output.append(
            "Note: Values are predictions with uncertainty. Use for guidance only."
        )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching soil properties")
    except Exception as e:
        return format_error(e, "processing soil data")


@tool
def get_soil_carbon(location: str) -> str:
    """
    Get soil organic carbon content at different depths from ISRIC SoilGrids.

    Provides SOC concentration and calculates total carbon stocks for
    standard depth intervals. Essential for carbon accounting and
    regenerative agriculture assessments.

    Args:
        location: City name or coordinates as "lat,lon"

    Returns:
        Soil organic carbon profile with depth and estimated stocks
    """
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    try:
        # Fetch SOC and bulk density for all depths
        data = _fetch_soil_data(lat, lon, ["soc", "bdod", "ocd"], DEPTHS)

        layers = data["properties"]["layers"]
        location_str = format_location(lat, lon)

        # Extract data by property
        soc_data = {}
        bdod_data = {}
        ocd_data = {}

        for layer in layers:
            prop_name = layer.get("name")
            if prop_name == "soc":
                for d in DEPTHS:
                    val = _extract_value(layer, d)
                    if val is not None:
                        soc_data[d] = val / 10  # Convert dg/kg to g/kg
            elif prop_name == "bdod":
                for d in DEPTHS:
                    val = _extract_value(layer, d)
                    if val is not None:
                        bdod_data[d] = val / 100  # Convert cg/cm³ to kg/dm³
            elif prop_name == "ocd":
                for d in DEPTHS:
                    val = _extract_value(layer, d)
                    if val is not None:
                        ocd_data[d] = val / 10  # Convert hg/m³ to kg/m³

        output = [
            "=== Soil Organic Carbon Profile ===",
            f"Location: {location} ({location_str})",
            "Source: ISRIC SoilGrids",
            "",
            f"{'Depth':<12} {'SOC':>10} {'Bulk Density':>14} {'OC Density':>12}",
            f"{'':12} {'(g/kg)':>10} {'(kg/dm³)':>14} {'(kg/m³)':>12}",
            "-" * 52,
        ]

        total_stock_30cm = 0
        total_stock_100cm = 0

        for depth in DEPTHS:
            soc = soc_data.get(depth)
            bd = bdod_data.get(depth)
            ocd = ocd_data.get(depth)

            soc_str = f"{soc:.1f}" if soc else "N/A"
            bd_str = f"{bd:.2f}" if bd else "N/A"
            ocd_str = f"{ocd:.1f}" if ocd else "N/A"

            output.append(f"{depth:<12} {soc_str:>10} {bd_str:>14} {ocd_str:>12}")

            # Calculate stock contribution (approximate)
            if ocd:
                # Extract depth range in cm
                parts = depth.replace("cm", "").split("-")
                thickness = (int(parts[1]) - int(parts[0])) / 100  # Convert to meters
                stock = ocd * thickness  # kg/m²

                if int(parts[1]) <= 30:
                    total_stock_30cm += stock
                if int(parts[1]) <= 100:
                    total_stock_100cm += stock

        output.append("-" * 52)
        output.append("")
        output.append("Estimated Carbon Stocks:")
        output.append(
            f"  0-30cm: {total_stock_30cm:.1f} kg C/m² ({total_stock_30cm * 10:.1f} t C/ha)"
        )
        output.append(
            f"  0-100cm: {total_stock_100cm:.1f} kg C/m² ({total_stock_100cm * 10:.1f} t C/ha)"
        )
        output.append("")
        output.append("Notes:")
        output.append("- SOC: Soil organic carbon concentration")
        output.append("- Higher SOC = better soil health and water retention")
        output.append("- Carbon stocks useful for emissions accounting")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching soil carbon data")
    except Exception as e:
        return format_error(e, "processing soil carbon data")


@tool
def get_soil_texture(location: str, depth: str = "0-30cm") -> str:
    """
    Get soil texture (sand, silt, clay fractions) and classify using USDA system.

    Soil texture affects water retention, drainage, and nutrient availability.
    Essential for irrigation planning and crop selection.

    Args:
        location: City name or coordinates as "lat,lon"
        depth: Depth interval (default "0-30cm" for topsoil average)

    Returns:
        Soil texture fractions and USDA texture class
    """
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    # Handle aggregated depth
    if depth == "0-30cm":
        depths_to_query = ["0-5cm", "5-15cm", "15-30cm"]
    else:
        if depth not in DEPTHS:
            return f"Invalid depth: {depth}. Available: {', '.join(DEPTHS)} or '0-30cm'"
        depths_to_query = [depth]

    try:
        data = _fetch_soil_data(lat, lon, ["sand", "silt", "clay"], depths_to_query)

        layers = data["properties"]["layers"]
        location_str = format_location(lat, lon)

        # Extract values
        sand_vals = []
        silt_vals = []
        clay_vals = []

        for layer in layers:
            prop_name = layer.get("name")
            for d in depths_to_query:
                val = _extract_value(layer, d)
                if val is not None:
                    # Convert g/kg to %
                    pct = val / 10
                    if prop_name == "sand":
                        sand_vals.append(pct)
                    elif prop_name == "silt":
                        silt_vals.append(pct)
                    elif prop_name == "clay":
                        clay_vals.append(pct)

        if not all([sand_vals, silt_vals, clay_vals]):
            return f"Insufficient texture data available for {location}"

        # Calculate averages
        sand = sum(sand_vals) / len(sand_vals)
        silt = sum(silt_vals) / len(silt_vals)
        clay = sum(clay_vals) / len(clay_vals)

        # Normalize to 100%
        total = sand + silt + clay
        if total > 0:
            sand = sand * 100 / total
            silt = silt * 100 / total
            clay = clay * 100 / total

        # Classify texture
        texture_class = _classify_texture(sand, silt, clay)

        output = [
            "=== Soil Texture Analysis ===",
            f"Location: {location} ({location_str})",
            f"Depth: {depth}",
            "Source: ISRIC SoilGrids",
            "",
            "Particle Size Distribution:",
            f"  Sand (2.0-0.05 mm): {sand:.1f}%",
            f"  Silt (0.05-0.002 mm): {silt:.1f}%",
            f"  Clay (<0.002 mm): {clay:.1f}%",
            "",
            f"USDA Texture Class: {texture_class}",
            "",
            "Texture Implications:",
        ]

        # Add texture-specific advice
        if "Sand" in texture_class:
            output.append("  - Good drainage, low water retention")
            output.append("  - Frequent irrigation may be needed")
            output.append("  - Low nutrient holding capacity")
        elif "Clay" in texture_class:
            output.append("  - High water and nutrient retention")
            output.append("  - May have drainage issues")
            output.append("  - Can be difficult to work when wet or dry")
        elif "Loam" in texture_class:
            output.append("  - Balanced drainage and retention")
            output.append("  - Generally good for most crops")
            output.append("  - Moderate nutrient holding capacity")
        elif "Silt" in texture_class:
            output.append("  - Good water retention")
            output.append("  - Prone to compaction and erosion")
            output.append("  - Good nutrient availability")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching soil texture data")
    except Exception as e:
        return format_error(e, "processing soil texture data")
