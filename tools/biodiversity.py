"""
Biodiversity tools using GBIF (Global Biodiversity Information Facility) API.

Provides species occurrence data, species search, and biodiversity metrics.
No API key required for basic queries.

API Documentation: https://techdocs.gbif.org/en/openapi/
"""

from strands import tool

from ._geo import geocode_or_parse
from ._http import APIError, fetch_json, format_error

# GBIF API base URLs
GBIF_API = "https://api.gbif.org/v1"
SPECIES_API = f"{GBIF_API}/species"
OCCURRENCE_API = f"{GBIF_API}/occurrence"

# Common taxonomic ranks
TAXONOMIC_RANKS = [
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
]

# Basis of record descriptions
BASIS_OF_RECORD = {
    "PRESERVED_SPECIMEN": "Museum/herbarium specimen",
    "HUMAN_OBSERVATION": "Human observation",
    "MACHINE_OBSERVATION": "Camera trap, sensor, etc.",
    "FOSSIL_SPECIMEN": "Fossil",
    "LIVING_SPECIMEN": "Living collection",
    "MATERIAL_SAMPLE": "DNA, tissue sample",
    "OCCURRENCE": "Generic occurrence",
    "MATERIAL_CITATION": "Literature citation",
}


def _search_species(query: str, limit: int = 10) -> list[dict]:
    """Search for species by name."""
    url = f"{SPECIES_API}/search"
    params = {
        "q": query,
        "limit": limit,
        "status": "ACCEPTED",  # Only accepted names, not synonyms
    }
    result = fetch_json(url, params)
    if isinstance(result, dict):
        return result.get("results", [])
    return []


def _get_species_by_key(taxon_key: int) -> dict:
    """Get species details by taxon key."""
    url = f"{SPECIES_API}/{taxon_key}"
    result = fetch_json(url)
    return result if isinstance(result, dict) else {}


def _match_species(name: str) -> dict:
    """Fuzzy match a species name to GBIF backbone."""
    url = f"{SPECIES_API}/match"
    params = {"name": name, "verbose": "true"}
    result = fetch_json(url, params)
    return result if isinstance(result, dict) else {}


def _search_occurrences(
    taxon_key: int | None = None,
    country: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 50,
    year: str | None = None,
    limit: int = 20,
) -> dict:
    """Search for species occurrences."""
    url = f"{OCCURRENCE_API}/search"
    params: dict[str, str | int | float] = {"limit": limit}

    if taxon_key:
        params["taxonKey"] = taxon_key
    if country:
        params["country"] = country.upper()[:2]  # ISO 2-letter code
    if lat is not None and lon is not None:
        # Use decimal lat/lon with radius in km
        params["decimalLatitude"] = f"{lat - radius_km/111},{lat + radius_km/111}"
        params["decimalLongitude"] = f"{lon - radius_km/111},{lon + radius_km/111}"
    if year:
        params["year"] = year

    result = fetch_json(url, params)
    return result if isinstance(result, dict) else {}


def _get_occurrence_counts(
    taxon_key: int | None = None,
    country: str | None = None,
) -> int:
    """Get total occurrence count for a taxon/country."""
    url = f"{OCCURRENCE_API}/count"
    params: dict[str, str | int] = {}
    if taxon_key:
        params["taxonKey"] = taxon_key
    if country:
        params["country"] = country.upper()[:2]

    result = fetch_json(url, params)
    if isinstance(result, int):
        return result
    return 0


@tool
def search_species(query: str, n_results: int = 10) -> str:
    """
    Search for species in the GBIF taxonomic backbone.

    Use this to find species by scientific or common name, and get their
    taxonomic classification and occurrence counts.

    Args:
        query: Species name to search (e.g., "Panthera leo", "lion", "oak tree")
        n_results: Number of results to return (default 10, max 50)

    Returns:
        List of matching species with taxonomy and global occurrence counts
    """
    n_results = min(max(1, n_results), 50)

    try:
        results = _search_species(query, n_results)

        if not results:
            return f"No species found matching '{query}'. Try a different spelling or use the scientific name."

        output = [
            "=== GBIF Species Search ===",
            f"Query: '{query}'",
            f"Found: {len(results)} species",
            "",
        ]

        for i, sp in enumerate(results, 1):
            key = sp.get("key", "")
            canonical = sp.get("canonicalName", sp.get("scientificName", "Unknown"))
            rank = sp.get("rank", "").title()
            status = sp.get("taxonomicStatus", "").replace("_", " ").title()

            output.append(f"--- {i}. {canonical} ---")
            output.append(f"GBIF Key: {key}")
            output.append(f"Rank: {rank} | Status: {status}")

            # Taxonomy
            taxonomy = []
            for rank_name in TAXONOMIC_RANKS:
                if rank_name in sp:
                    taxonomy.append(f"{rank_name.title()}: {sp[rank_name]}")
            if taxonomy:
                output.append("Taxonomy: " + " > ".join(taxonomy[:4]))

            # Occurrence count
            if key:
                try:
                    count = _get_occurrence_counts(taxon_key=key)
                    output.append(f"Global occurrences: {count:,}")
                except Exception:
                    pass

            # Vernacular names if available
            vernacular = sp.get("vernacularNames", [])
            if vernacular:
                names = [v.get("vernacularName", "") for v in vernacular[:3]]
                if names:
                    output.append(f"Common names: {', '.join(names)}")

            output.append("")

        output.append(
            "Use get_species_occurrences(taxon_key) to see where a species has been recorded."
        )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "searching GBIF species")
    except Exception as e:
        return format_error(e, "processing species search")


@tool
def get_species_occurrences(
    species: str,
    location: str | None = None,
    country: str | None = None,
    year: str | None = None,
    n_results: int = 20,
) -> str:
    """
    Get occurrence records for a species from GBIF.

    Search for where a species has been observed/collected. Can filter by
    location, country, or year range.

    Args:
        species: Species name (e.g., "Panthera leo") or GBIF taxon key
        location: Optional location to search near (city name or "lat,lon")
        country: Optional 2-letter country code (e.g., "KE" for Kenya)
        year: Optional year or range (e.g., "2020" or "2015,2023")
        n_results: Number of results (default 20, max 100)

    Returns:
        List of occurrence records with locations, dates, and sources
    """
    n_results = min(max(1, n_results), 100)

    try:
        # Resolve species to taxon key
        taxon_key: int | None = None
        species_name = species

        # Check if species is already a taxon key
        try:
            taxon_key = int(species)
            # Get species name from key
            sp_info = _get_species_by_key(taxon_key)
            species_name = sp_info.get("canonicalName", f"Taxon {taxon_key}")
        except ValueError:
            # Search for species
            results = _search_species(species, 1)
            if results:
                taxon_key = results[0].get("key")
                species_name = results[0].get("canonicalName", species)
            else:
                return (
                    f"Species '{species}' not found in GBIF. Try a different spelling."
                )

        # Parse location if provided
        lat: float | None = None
        lon: float | None = None
        location_str = ""

        if location:
            coords = geocode_or_parse(location)
            if coords is None:
                return f"Could not resolve location: {location}"
            lat, lon = coords
            location_str = f" near {location}"

        # Search occurrences
        data = _search_occurrences(
            taxon_key=taxon_key,
            country=country,
            lat=lat,
            lon=lon,
            year=year,
            limit=n_results,
        )

        total = data.get("count", 0)
        records = data.get("results", [])

        if not records:
            filter_desc = []
            if location:
                filter_desc.append(f"near {location}")
            if country:
                filter_desc.append(f"in {country}")
            if year:
                filter_desc.append(f"from {year}")
            filter_str = " ".join(filter_desc) if filter_desc else "worldwide"
            return f"No occurrences found for {species_name} {filter_str}."

        output = [
            "=== Species Occurrences ===",
            f"Species: {species_name}",
            f"Total records{location_str}: {total:,}",
            f"Showing: {len(records)} most recent",
            "",
        ]

        for i, rec in enumerate(records, 1):
            output.append(f"--- Record {i} ---")

            # Location
            rec_lat = rec.get("decimalLatitude")
            rec_lon = rec.get("decimalLongitude")
            locality = rec.get("locality", "")
            country_code = rec.get("countryCode", "")

            if rec_lat and rec_lon:
                output.append(f"Location: {rec_lat:.4f}, {rec_lon:.4f}")
            if locality:
                output.append(f"Locality: {locality[:80]}")
            if country_code:
                output.append(f"Country: {country_code}")

            # Date
            event_date = rec.get("eventDate", rec.get("year", "Unknown"))
            output.append(f"Date: {event_date}")

            # Basis of record
            basis = rec.get("basisOfRecord", "")
            basis_desc = BASIS_OF_RECORD.get(basis, basis)
            output.append(f"Type: {basis_desc}")

            # Dataset
            dataset = rec.get("datasetName", "")[:50]
            if dataset:
                output.append(f"Source: {dataset}")

            output.append("")

        # Summary by basis of record
        basis_counts: dict[str, int] = {}
        for rec in records:
            b = rec.get("basisOfRecord", "UNKNOWN")
            basis_counts[b] = basis_counts.get(b, 0) + 1

        if basis_counts:
            output.append("Record types in results:")
            for basis, count in sorted(basis_counts.items(), key=lambda x: -x[1]):
                desc = BASIS_OF_RECORD.get(basis, basis)
                output.append(f"  {desc}: {count}")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching occurrences")
    except Exception as e:
        return format_error(e, "processing occurrences")


@tool
def get_biodiversity_summary(
    location: str,
    radius_km: float = 50,
    taxonomic_group: str | None = None,
) -> str:
    """
    Get a biodiversity summary for a location.

    Provides species richness estimates and occurrence statistics for
    a geographic area. Useful for understanding local biodiversity.

    Args:
        location: Location to analyze (city name or "lat,lon")
        radius_km: Search radius in kilometers (default 50, max 200)
        taxonomic_group: Optional filter - "plants", "mammals", "birds", "insects", "fish", "reptiles", "amphibians"

    Returns:
        Biodiversity summary with species counts and common taxa
    """
    radius_km = min(max(1, radius_km), 200)

    # Taxonomic group filters (GBIF taxon keys for major groups)
    GROUP_KEYS = {
        "plants": 6,  # Plantae
        "mammals": 359,  # Mammalia
        "birds": 212,  # Aves
        "insects": 216,  # Insecta
        "fish": 204,  # Actinopterygii (bony fish)
        "reptiles": 358,  # Reptilia
        "amphibians": 131,  # Amphibia
        "fungi": 5,  # Fungi
    }

    try:
        coords = geocode_or_parse(location)
        if coords is None:
            return f"Could not resolve location: {location}"
        lat, lon = coords

        # Build search URL for faceted search
        url = f"{OCCURRENCE_API}/search"

        # Calculate bounding box
        lat_range = radius_km / 111  # ~111 km per degree
        lon_range = (
            radius_km / (111 * abs(lat) / 90 + 0.001)
            if abs(lat) < 89
            else radius_km / 111
        )

        params: dict[str, str | int] = {
            "decimalLatitude": f"{lat - lat_range},{lat + lat_range}",
            "decimalLongitude": f"{lon - lon_range},{lon + lon_range}",
            "facet": "speciesKey",
            "facetLimit": 100,
            "limit": 0,  # We only want facets, not actual records
        }

        if taxonomic_group:
            group_key = GROUP_KEYS.get(taxonomic_group.lower())
            if group_key:
                params["taxonKey"] = group_key

        result = fetch_json(url, params)
        if not isinstance(result, dict):
            return "Error: Unexpected response from GBIF"

        total_occurrences = result.get("count", 0)
        facets = result.get("facets", [])

        # Find species facet
        species_facet = None
        for f in facets:
            if f.get("field") == "SPECIES_KEY":
                species_facet = f.get("counts", [])
                break

        species_count = len(species_facet) if species_facet else 0

        group_label = f" ({taxonomic_group})" if taxonomic_group else ""
        output = [
            "=== Biodiversity Summary ===",
            f"Location: {location} ({lat:.4f}, {lon:.4f})",
            f"Search radius: {radius_km} km",
            f"Taxonomic filter: {taxonomic_group or 'All groups'}",
            "",
            f"Total occurrences{group_label}: {total_occurrences:,}",
            f"Species recorded: {species_count}+",
            "",
        ]

        # Get top species
        if species_facet:
            output.append("Most recorded species:")
            for i, sp in enumerate(species_facet[:15], 1):
                key = sp.get("name", "")
                count = sp.get("count", 0)

                # Get species name
                try:
                    sp_info = _get_species_by_key(int(key))
                    name = sp_info.get("canonicalName", f"Species {key}")
                    rank = sp_info.get("rank", "")
                    output.append(
                        f"  {i:2}. {name} ({rank.lower()}) - {count:,} records"
                    )
                except Exception:
                    output.append(f"  {i:2}. Taxon {key} - {count:,} records")

        # Get basis of record breakdown
        params_basis: dict[str, str | int] = {
            "decimalLatitude": f"{lat - lat_range},{lat + lat_range}",
            "decimalLongitude": f"{lon - lon_range},{lon + lon_range}",
            "facet": "basisOfRecord",
            "limit": 0,
        }
        if taxonomic_group and taxonomic_group.lower() in GROUP_KEYS:
            params_basis["taxonKey"] = GROUP_KEYS[taxonomic_group.lower()]

        result_basis = fetch_json(url, params_basis)
        if isinstance(result_basis, dict):
            basis_facets = result_basis.get("facets", [])
            for f in basis_facets:
                if f.get("field") == "BASIS_OF_RECORD":
                    output.append("")
                    output.append("Data sources:")
                    for b in f.get("counts", [])[:5]:
                        basis = b.get("name", "")
                        count = b.get("count", 0)
                        desc = BASIS_OF_RECORD.get(basis, basis)
                        output.append(f"  {desc}: {count:,}")
                    break

        output.append("")
        output.append(
            "Note: Species count is based on records in GBIF. Actual biodiversity may differ."
        )
        output.append(
            "Use search_species() or get_species_occurrences() for detailed queries."
        )

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching biodiversity data")
    except Exception as e:
        return format_error(e, "processing biodiversity summary")


@tool
def get_species_taxonomy(species: str) -> str:
    """
    Get detailed taxonomic information for a species.

    Provides the full taxonomic classification and related information
    from the GBIF Backbone Taxonomy.

    Args:
        species: Species name (scientific or common) or GBIF taxon key

    Returns:
        Complete taxonomic classification and metadata
    """
    try:
        taxon_key: int | None = None
        sp_info: dict = {}

        # Check if it's a taxon key
        try:
            taxon_key = int(species)
            sp_info = _get_species_by_key(taxon_key)
        except ValueError:
            # Match the name
            match_result = _match_species(species)
            if match_result.get("matchType") == "NONE":
                return f"No taxonomic match found for '{species}'. Try a different spelling."

            taxon_key = match_result.get("usageKey")
            sp_info = match_result

        if not sp_info:
            return f"Could not retrieve taxonomy for '{species}'."

        canonical = sp_info.get(
            "canonicalName", sp_info.get("scientificName", "Unknown")
        )
        authorship = sp_info.get("authorship", "")
        rank = sp_info.get("rank", "").title()
        status = (
            sp_info.get("status", sp_info.get("taxonomicStatus", ""))
            .replace("_", " ")
            .title()
        )
        match_type = sp_info.get("matchType", "EXACT")

        output = [
            "=== Species Taxonomy ===",
            f"Name: {canonical}",
        ]
        if authorship:
            output.append(f"Authority: {authorship}")
        output.append(f"Rank: {rank}")
        output.append(f"Status: {status}")
        if match_type != "EXACT":
            output.append(f"Match type: {match_type}")
        output.append(f"GBIF Key: {taxon_key}")
        output.append("")

        # Full classification
        output.append("Classification:")
        for rank_name in TAXONOMIC_RANKS:
            value = sp_info.get(rank_name)
            key = sp_info.get(f"{rank_name}Key")
            if value:
                key_str = f" [{key}]" if key else ""
                output.append(f"  {rank_name.title()}: {value}{key_str}")

        # Synonyms and alternatives
        if "alternatives" in sp_info:
            output.append("")
            output.append("Similar names found:")
            for alt in sp_info.get("alternatives", [])[:5]:
                alt_name = alt.get("canonicalName", alt.get("scientificName", ""))
                alt_status = alt.get("status", "").replace("_", " ").lower()
                confidence = alt.get("confidence", 0)
                output.append(
                    f"  - {alt_name} ({alt_status}, {confidence}% confidence)"
                )

        # Global occurrence count
        if taxon_key:
            try:
                count = _get_occurrence_counts(taxon_key=taxon_key)
                output.append("")
                output.append(f"Global GBIF records: {count:,}")
            except Exception:
                pass

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching taxonomy")
    except Exception as e:
        return format_error(e, "processing taxonomy")
