"""
Knowledge Base tools using ChromaDB and Ollama embeddings.

Provides semantic search over the CBA ME Indicators database.
Data is ingested from Excel files using scripts/ingest_excel.py.
"""

from __future__ import annotations

import os
import re
import time
from typing import TYPE_CHECKING, Any, TypedDict, cast

import chromadb
from strands import tool

from agentic_cba_indicators.logging_config import get_logger
from agentic_cba_indicators.paths import get_kb_path

from ._embedding import get_embedding as _get_embedding

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

# Module logger
logger = get_logger(__name__)


class IndicatorDataDict(TypedDict):
    """Type for indicator comparison data."""

    id: int
    name: str
    meta: dict[str, Any]
    method_meta: dict[str, Any]


class ChromaDBError(Exception):
    """Raised when ChromaDB operations fail after retries."""


# Retry settings for ChromaDB operations
_CHROMADB_RETRIES = int(os.environ.get("CHROMADB_RETRIES", "3"))
_CHROMADB_BACKOFF = float(os.environ.get("CHROMADB_BACKOFF", "0.5"))

# Search result limits (prevents excessive context in LLM prompts)
_MAX_SEARCH_RESULTS_DEFAULT = 20  # Standard search functions
_MAX_SEARCH_RESULTS_MEDIUM = 50  # Principle/class browsing functions
_MAX_SEARCH_RESULTS_LARGE = 100  # Component listing, comparison functions

# Similarity threshold for indicator name matching (cosine distance)
# Distance < 0.7 corresponds to ~65%+ similarity
_INDICATOR_MATCH_THRESHOLD = 0.7

# Default similarity threshold for filtering low-relevance results
# Cosine similarity below this threshold indicates weak semantic match
_DEFAULT_SIMILARITY_THRESHOLD = 0.3

# Patterns for detecting exact-match queries (indicator IDs, principle codes)
_INDICATOR_ID_PATTERN = re.compile(r"^(?:indicator\s*)?(\d{1,3})$", re.IGNORECASE)
_PRINCIPLE_CODE_PATTERN = re.compile(r"^(\d\.\d)$")


def _extract_exact_match_term(query: str) -> str | None:
    """Extract exact-match term from query if it looks like an ID or code.

    Returns the term to use with $contains filter, or None for semantic search.
    """
    query = query.strip()

    # Check for indicator ID pattern (e.g., "107", "indicator 107")
    if match := _INDICATOR_ID_PATTERN.match(query):
        return f"ID: {match.group(1)}"

    # Check for principle/criteria code (e.g., "2.1", "6.2")
    if _PRINCIPLE_CODE_PATTERN.match(query):
        return query

    return None


def _get_chroma_client() -> ClientAPI:
    """Get or create ChromaDB client with retry logic.

    Retries on transient failures (file locking, resource exhaustion).
    Retry count and backoff configurable via CHROMADB_RETRIES and CHROMADB_BACKOFF env vars.

    Returns:
        ChromaDB PersistentClient instance

    Raises:
        ChromaDBError: If client creation fails after retries
    """
    kb_path = get_kb_path()
    last_error: Exception | None = None

    for attempt in range(_CHROMADB_RETRIES + 1):
        try:
            return chromadb.PersistentClient(path=str(kb_path))
        except Exception as e:
            last_error = e
            # Check for known transient errors
            error_str = str(e).lower()
            is_transient = any(
                pattern in error_str
                for pattern in ["locked", "busy", "timeout", "connection", "resource"]
            )

            if not is_transient or attempt >= _CHROMADB_RETRIES:
                # Non-transient error or max retries reached
                raise ChromaDBError(f"ChromaDB client creation failed: {e}") from e

            # Wait before retry with exponential backoff
            delay = _CHROMADB_BACKOFF * (2**attempt)
            logger.debug(
                "ChromaDB client creation failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                _CHROMADB_RETRIES + 1,
                delay,
                e,
            )
            time.sleep(delay)

    # Should not reach here, but just in case
    raise ChromaDBError(
        f"ChromaDB client creation failed after {_CHROMADB_RETRIES + 1} attempts: {last_error}"
    )


def _get_collection(name: str) -> chromadb.Collection:
    """Get a ChromaDB collection with retry logic.

    Retries on transient failures (file locking, resource exhaustion).

    Args:
        name: Collection name to get or create

    Returns:
        ChromaDB Collection instance

    Raises:
        ChromaDBError: If collection access fails after retries
    """
    last_error: Exception | None = None

    for attempt in range(_CHROMADB_RETRIES + 1):
        try:
            client = _get_chroma_client()
            return client.get_or_create_collection(name=name)
        except ChromaDBError:
            # Re-raise our own errors without wrapping
            raise
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            is_transient = any(
                pattern in error_str
                for pattern in ["locked", "busy", "timeout", "connection", "resource"]
            )

            if not is_transient or attempt >= _CHROMADB_RETRIES:
                raise ChromaDBError(
                    f"ChromaDB collection '{name}' access failed: {e}"
                ) from e

            delay = _CHROMADB_BACKOFF * (2**attempt)
            logger.debug(
                "ChromaDB collection '%s' access failed (attempt %d/%d), retrying in %.1fs: %s",
                name,
                attempt + 1,
                _CHROMADB_RETRIES + 1,
                delay,
                e,
            )
            time.sleep(delay)

    raise ChromaDBError(
        f"ChromaDB collection '{name}' access failed after {_CHROMADB_RETRIES + 1} attempts: {last_error}"
    )


@tool
def search_indicators(
    query: str, n_results: int = 5, min_similarity: float = 0.3
) -> str:
    """
    Search the CBA ME Indicators knowledge base for relevant indicators.

    Use this to find indicators related to specific topics like:
    - Environmental measurements (soil, water, biodiversity)
    - Social assessments (labor, community, gender)
    - Economic indicators (income, productivity, costs)
    - Specific principles (Natural Environment, Human Rights, etc.)

    For exact ID lookups, use "indicator 107" or just "107".

    Args:
        query: Natural language search query describing what you're looking for
        n_results: Number of results to return (default 5, max 20)
        min_similarity: Minimum similarity threshold (0.0-1.0, default 0.3)

    Returns:
        Matching indicators with their components, classes, units, and coverage
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_DEFAULT)
    min_similarity = max(0.0, min(1.0, min_similarity))

    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run the ingestion script first: python scripts/ingest_excel.py"

        # Check for exact-match patterns (indicator IDs, principle codes)
        exact_term = _extract_exact_match_term(query)

        # Initialize result variables - use Any to avoid ChromaDB Metadata type issues
        docs: list[Any] = []
        metas: list[Any] = []
        dists: list[float] = []

        if exact_term:
            # Use keyword filtering for exact matches
            results = collection.get(
                where_document={"$contains": exact_term},
                include=["documents", "metadatas"],
            )
            docs = results.get("documents") or []
            metas = results.get("metadatas") or []
            # No distances for exact match, treat as 100% relevance
            dists = [0.0] * len(docs)

        if not exact_term or not docs:
            # Semantic search (either no exact term, or exact match found nothing)
            query_embedding = _get_embedding(query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            dists = (results.get("distances") or [[]])[0]

        if not docs:
            return "No matching indicators found."

        output_lines: list[str] = []
        result_count = 0

        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            meta = cast("dict[str, Any]", meta)
            dist = cast("float", dist)
            # Cosine distance: 0 = identical, 2 = opposite. Similarity = 1 - distance.
            similarity = max(0.0, 1 - dist)

            # Filter by similarity threshold
            if similarity < min_similarity:
                continue

            result_count += 1
            output_lines.append(
                f"--- Result {result_count} (relevance: {similarity:.0%}) ---"
            )
            output_lines.append(f"ID: {meta.get('id', 'N/A')}")
            output_lines.append(f"Component: {meta.get('component', 'N/A')}")
            output_lines.append(f"Class: {meta.get('class', 'N/A')}")
            output_lines.append(f"Unit: {meta.get('unit', 'N/A')}")
            output_lines.append(
                f"Principles covered: {meta.get('total_principles', 0)}"
            )
            output_lines.append(f"Criteria covered: {meta.get('total_criteria', 0)}")
            output_lines.append(f"\nDescription:\n{doc}\n")

        if result_count == 0:
            return "No matching indicators found above similarity threshold."

        header = f"Found {result_count} matching indicators:\n"
        return header + "\n".join(output_lines)

    except Exception as e:
        return f"Error searching knowledge base: {e!s}"


@tool
def search_methods(
    query: str, n_results: int = 5, min_similarity: float = 0.3, oa_only: bool = False
) -> str:
    """
    Search for measurement methods in the CBA ME knowledge base.

    Use this to find HOW to measure specific indicators, including:
    - Field methods, lab methods, remote sensing approaches
    - Method accuracy, ease of use, and cost considerations
    - Specific measurement procedures and citations

    Args:
        query: Search query about measurement methods or techniques
        n_results: Number of results to return (default 5, max 20)
        min_similarity: Minimum similarity threshold (0.0-1.0, default 0.3)
        oa_only: If True, only return indicators with Open Access citations

    Returns:
        Matching methods with evaluation criteria and citations
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_DEFAULT)
    min_similarity = max(0.0, min(1.0, min_similarity))

    try:
        collection = _get_collection("methods")

        if collection.count() == 0:
            return "Methods collection is empty. Run the ingestion script first."

        query_embedding = _get_embedding(query)

        # Build query with optional OA filter
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if oa_only:
            query_kwargs["where"] = {"has_oa_citations": True}

        results = collection.query(**query_kwargs)

        docs = results.get("documents")
        metas = results.get("metadatas")
        dists = results.get("distances")

        if not docs or not docs[0]:
            return "No matching methods found."

        output_lines: list[str] = []
        result_count = 0

        for doc, meta, dist in zip(
            docs[0],
            metas[0] if metas else [],
            dists[0] if dists else [],
            strict=False,
        ):
            meta = cast("dict[str, Any]", meta)
            dist = cast("float", dist)
            # Cosine distance: 0 = identical, 2 = opposite. Similarity = 1 - distance.
            similarity = max(0.0, 1 - dist)

            # Filter by similarity threshold
            if similarity < min_similarity:
                continue

            result_count += 1
            output_lines.append(
                f"--- Result {result_count} (relevance: {similarity:.0%}) ---"
            )
            output_lines.append(f"Indicator ID: {meta.get('indicator_id', 'N/A')}")
            output_lines.append(f"Indicator: {meta.get('indicator', 'N/A')}")
            output_lines.append(f"Number of Methods: {meta.get('method_count', 'N/A')}")
            output_lines.append(
                f"Has High Accuracy: {'Yes' if meta.get('has_high_accuracy') else 'No'}"
            )
            output_lines.append(
                f"Has Low Cost: {'Yes' if meta.get('has_low_cost') else 'No'}"
            )
            output_lines.append(
                f"Has High Ease: {'Yes' if meta.get('has_high_ease') else 'No'}"
            )
            output_lines.append(f"\n{doc}\n")

        if result_count == 0:
            return "No matching methods found above similarity threshold."

        header = f"Found {result_count} matching method groups:\n"
        return header + "\n".join(output_lines)

    except Exception as e:
        return f"Error searching methods: {e!s}"


@tool
def get_indicator_details(indicator_id: int) -> str:
    """
    Get full details for a specific indicator by ID.

    Use after searching to get complete information about an indicator,
    including all measurement methods available for it.

    Args:
        indicator_id: The indicator ID number (1-224)

    Returns:
        Complete indicator details and all associated measurement methods
    """
    try:
        # Get indicator
        indicators = _get_collection("indicators")
        indicator_results = indicators.get(
            ids=[f"indicator:{indicator_id}"], include=["documents", "metadatas"]
        )

        ind_docs = indicator_results.get("documents")
        ind_metas = indicator_results.get("metadatas")

        if not ind_docs or not ind_docs[0]:
            return f"Indicator ID {indicator_id} not found."

        doc = ind_docs[0]
        meta = cast("dict[str, Any]", ind_metas[0] if ind_metas else {})

        output = [
            f"=== Indicator {indicator_id} ===",
            f"Component: {meta.get('component', 'N/A')}",
            f"Class: {meta.get('class', 'N/A')}",
            f"Unit: {meta.get('unit', 'N/A')}",
            f"\nDescription:\n{doc}",
            "\nMeasurement Categories:",
            f"  - Field methods: {'Yes' if meta.get('field_methods') else 'No'}",
            f"  - Lab methods: {'Yes' if meta.get('lab_methods') else 'No'}",
            f"  - Remote sensing: {'Yes' if meta.get('remote_sensing') else 'No'}",
            f"  - Social/participatory: {'Yes' if meta.get('social_participatory') else 'No'}",
            f"  - Production audits: {'Yes' if meta.get('production_audits') else 'No'}",
            "\nPrinciple Coverage:",
            f"  Total principles: {meta.get('total_principles', 0)}",
            f"  Total criteria: {meta.get('total_criteria', 0)}",
        ]

        # Get methods for this indicator (now stored as grouped document)
        methods = _get_collection("methods")
        method_results = methods.get(
            ids=[f"methods_for_indicator:{indicator_id}"],
            include=["documents", "metadatas"],
        )

        method_docs = method_results.get("documents")
        method_metas = method_results.get("metadatas")

        if method_docs and method_docs[0]:
            mmeta = cast("dict[str, Any]", method_metas[0] if method_metas else {})
            mdoc = method_docs[0]
            output.append(
                f"\n=== Measurement Methods ({mmeta.get('method_count', 0)} total) ==="
            )
            output.append(
                f"Has High Accuracy Methods: {'Yes' if mmeta.get('has_high_accuracy') else 'No'}"
            )
            output.append(
                f"Has Low Cost Methods: {'Yes' if mmeta.get('has_low_cost') else 'No'}"
            )
            output.append(
                f"Has High Ease Methods: {'Yes' if mmeta.get('has_high_ease') else 'No'}"
            )
            output.append(f"\n{mdoc}")
        else:
            output.append("\nNo measurement methods available for this indicator.")

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving indicator: {e!s}"


@tool
def list_knowledge_base_stats() -> str:
    """
    Show statistics about the knowledge base contents.

    Returns:
        Summary of indexed indicators, methods, and Open Access coverage
    """
    try:
        client = _get_chroma_client()
        collections = client.list_collections()

        if not collections:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        output = ["=== Knowledge Base Statistics ===\n"]

        # Collection counts
        for coll_info in collections:
            collection = client.get_collection(coll_info.name)
            output.append(f"Collection: {coll_info.name}")
            output.append(f"  Documents: {collection.count()}")

        # Open Access statistics from methods collection
        try:
            methods_coll = client.get_collection("methods")
            methods_data = methods_coll.get(include=["metadatas"])
            metadatas = methods_data.get("metadatas") if methods_data else None
            if metadatas:
                total_oa = sum(
                    cast("int", cast("dict[str, Any]", m).get("oa_count", 0))
                    for m in metadatas
                )
                total_citations = sum(
                    cast("int", cast("dict[str, Any]", m).get("citation_count", 0))
                    for m in metadatas
                )
                indicators_with_oa = sum(
                    1
                    for m in metadatas
                    if cast("dict[str, Any]", m).get("has_oa_citations")
                )

                if total_citations > 0:
                    output.append("\nOpen Access Coverage:")
                    output.append(f"  Total OA citations: {total_oa}")
                    output.append(
                        f"  Coverage: {total_oa}/{total_citations} ({total_oa / total_citations:.1%})"
                    )
                    output.append(
                        f"  Indicators with OA: {indicators_with_oa}/{len(metadatas)}"
                    )
        except Exception:
            pass  # OA stats optional if collection doesn't exist

        output.append(
            "\n\nUse search_indicators() or search_methods() to query the knowledge base."
        )

        return "\n".join(output)

    except Exception as e:
        return f"Error getting stats: {e!s}"


@tool
def search_usecases(query: str, n_results: int = 5, min_similarity: float = 0.3) -> str:
    """
    Search for example use case projects in the knowledge base.

    Use this to find real-world examples of CBA indicator selection for:
    - Specific commodities (cotton, coffee, cocoa, etc.)
    - Specific regions or countries (Africa, Chad, Brazil, etc.)
    - Specific outcomes (soil health, biodiversity, income, etc.)

    Args:
        query: Search query about projects, commodities, or outcomes
        n_results: Number of results to return (default 5, max 20)
        min_similarity: Minimum similarity threshold (0.0-1.0, default 0.3)

    Returns:
        Matching use case projects with their outcomes and selected indicators
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_DEFAULT)
    min_similarity = max(0.0, min(1.0, min_similarity))

    try:
        collection = _get_collection("usecases")

        if collection.count() == 0:
            return (
                "Use cases collection is empty. Run: python scripts/ingest_usecases.py"
            )

        query_embedding = _get_embedding(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")
        dists = results.get("distances")

        if not docs or not docs[0]:
            return "No matching use cases found."

        output_lines: list[str] = []
        result_count = 0

        for doc, meta, dist in zip(
            docs[0],
            metas[0] if metas else [],
            dists[0] if dists else [],
            strict=False,
        ):
            meta = cast("dict[str, Any]", meta)
            dist = cast("float", dist)
            # Cosine distance: 0 = identical, 2 = opposite. Similarity = 1 - distance.
            similarity = max(0.0, 1 - dist)

            # Filter by similarity threshold
            if similarity < min_similarity:
                continue

            result_count += 1
            doc_type = meta.get("doc_type", "unknown")

            output_lines.append(
                f"--- Result {result_count} (relevance: {similarity:.0%}) ---"
            )
            output_lines.append(f"Project: {meta.get('use_case_name', 'N/A')}")
            output_lines.append(
                f"Country: {meta.get('country', 'N/A')} ({meta.get('region', 'N/A')})"
            )
            output_lines.append(f"Commodity: {meta.get('commodity', 'N/A')}")

            if doc_type == "overview":
                output_lines.append("Type: Project Overview")
                output_lines.append(f"Outcomes: {meta.get('outcome_count', 0)}")
            else:
                output_lines.append(f"Type: Outcome {meta.get('outcome_id', 'N/A')}")
                output_lines.append(f"Indicators: {meta.get('indicator_count', 0)}")

            output_lines.append(f"\n{doc}\n")

        if result_count == 0:
            return "No matching use cases found above similarity threshold."

        header = f"Found {result_count} matching use case documents:\n"
        return header + "\n".join(output_lines)

    except Exception as e:
        return f"Error searching use cases: {e!s}"


@tool
def get_usecase_details(use_case_slug: str) -> str:
    """
    Get full details for a specific use case project.

    Use after searching to get complete information about a project,
    including all outcomes and their selected indicators.

    Args:
        use_case_slug: The project slug (e.g., "regen_cotton_chad")

    Returns:
        Complete project details with all outcomes and indicators
    """
    try:
        collection = _get_collection("usecases")

        if collection.count() == 0:
            return "Use cases collection is empty."

        # Get all documents for this use case
        results = collection.get(
            where={"use_case_slug": use_case_slug},
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs:
            return f"Use case '{use_case_slug}' not found."

        # Separate overview from outcomes
        overview = None
        outcomes: list[tuple[str, dict[str, Any]]] = []

        for doc, meta in zip(docs, metas or [], strict=False):
            meta = cast("dict[str, Any]", meta)
            if meta.get("doc_type") == "overview":
                overview = (doc, meta)
            else:
                outcomes.append((doc, meta))

        # Sort outcomes by outcome_id
        outcomes.sort(key=lambda x: x[1].get("outcome_id", ""))

        output: list[str] = []

        if overview:
            doc, meta = overview
            output.append(f"=== {meta.get('use_case_name', 'Unknown Project')} ===")
            output.append(f"Country: {meta.get('country', 'N/A')}")
            output.append(f"Region: {meta.get('region', 'N/A')}")
            output.append(f"Commodity: {meta.get('commodity', 'N/A')}")
            output.append(f"Total Outcomes: {meta.get('outcome_count', len(outcomes))}")
            output.append(f"\n{doc}")

        if outcomes:
            output.append(f"\n{'=' * 40}")
            output.append(f"OUTCOMES ({len(outcomes)} total)")
            output.append(f"{'=' * 40}")

            for doc, meta in outcomes:
                output.append(f"\n--- Outcome {meta.get('outcome_id', 'N/A')} ---")
                output.append(f"Indicators selected: {meta.get('indicator_count', 0)}")
                output.append(doc)

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving use case: {e!s}"


def _resolve_indicator_id(indicator: str | int) -> tuple[int | None, str | None]:
    """
    Resolve an indicator name or ID to a valid indicator ID.

    Returns:
        Tuple of (indicator_id, indicator_name) or (None, error_message)
    """
    # If already an int, validate it exists
    if isinstance(indicator, int):
        collection = _get_collection("indicators")
        get_results = collection.get(
            ids=[f"indicator:{indicator}"], include=["metadatas"]
        )
        metas = get_results.get("metadatas")
        if metas and metas[0]:
            return indicator, None
        return None, f"Indicator ID {indicator} not found"

    # Try to parse as int
    try:
        indicator_id = int(indicator)
        return _resolve_indicator_id(indicator_id)
    except ValueError:
        pass

    # Search by name using semantic search
    query_embedding = _get_embedding(indicator)
    collection = _get_collection("indicators")

    query_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        include=["metadatas", "documents", "distances"],
    )

    query_metas = query_results.get("metadatas")
    query_dists = query_results.get("distances")
    query_docs = query_results.get("documents")

    if not query_metas or not query_metas[0]:
        return None, f"No indicator found matching '{indicator}'"

    # Check if it's a reasonable match using similarity threshold
    distance = cast("float", query_dists[0][0]) if query_dists else 1.0
    if distance > _INDICATOR_MATCH_THRESHOLD:
        return (
            None,
            f"No close match found for '{indicator}'. Best match was too different.",
        )

    meta = cast("dict[str, Any]", query_metas[0][0])
    indicator_id = cast("int", meta.get("id"))

    # Extract indicator name from document
    doc = cast("str", query_docs[0][0]) if query_docs and query_docs[0] else ""
    name_line = [line for line in doc.split("\n") if line.startswith("Indicator:")]
    indicator_name = (
        name_line[0].replace("Indicator:", "").strip() if name_line else "Unknown"
    )

    return indicator_id, indicator_name


@tool
def get_usecases_by_indicator(indicator: str) -> str:
    """
    Find all use case projects that include a specific indicator.

    Use this to see real-world examples of how an indicator has been used.
    You can provide either the indicator ID number OR the indicator name.

    Args:
        indicator: The indicator ID number (e.g., "107") OR name (e.g., "Soil organic carbon")

    Returns:
        List of use cases and outcomes that selected this indicator
    """
    import json

    try:
        # Resolve indicator to ID
        indicator_id, name_or_error = _resolve_indicator_id(indicator)

        if indicator_id is None:
            return name_or_error or "Unknown error"

        # If we got a name back, show what we matched
        matched_info = ""
        if name_or_error and isinstance(name_or_error, str):
            matched_info = f" (matched: '{name_or_error}')"

        collection = _get_collection("usecases")

        if collection.count() == 0:
            return "Use cases collection is empty."

        # Get all outcome documents (not overviews)
        results = collection.get(
            where={"doc_type": "outcome"},
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs:
            return "No outcome documents found."

        # Filter for outcomes containing this indicator
        matching: list[tuple[str, dict[str, Any]]] = []
        for doc, meta in zip(docs, metas or [], strict=False):
            meta = cast("dict[str, Any]", meta)
            indicator_ids_json = str(meta.get("indicator_ids_json", "[]"))
            try:
                indicator_ids = json.loads(indicator_ids_json)
                if indicator_id in indicator_ids:
                    matching.append((doc, meta))
            except json.JSONDecodeError:
                continue

        if not matching:
            return f"No use cases found using indicator {indicator_id}{matched_info}."

        output = [
            f"Found {len(matching)} outcomes using indicator {indicator_id}{matched_info}:\n"
        ]

        for doc, meta in matching:
            output.append(f"--- {meta.get('use_case_name', 'Unknown')} ---")
            output.append(f"Country: {meta.get('country', 'N/A')}")
            output.append(f"Commodity: {meta.get('commodity', 'N/A')}")
            output.append(f"Outcome: {meta.get('outcome_id', 'N/A')}")
            output.append(f"\n{doc}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error searching by indicator: {e!s}"


# =============================================================================
# Principle and Criteria Constants (mirrored from ingest_excel.py)
# =============================================================================

PRINCIPLES = {
    "1": "Natural Environment",
    "2": "Social Well-being",
    "3": "Economic Prosperity",
    "4": "Diversity",
    "5": "Connectivity",
    "6": "Adaptive Capacity",
    "7": "Harmony",
}

CRITERIA = {
    "1.1": "Avoid ecosystem degradation",
    "1.2": "Minimize GHG emissions and enhance sinks",
    "1.3": "Shift to environmentally sustainable practices",
    "1.4": "Shift to renewable and bio-based processes",
    "2.1": "Enhance human health and wellbeing",
    "2.2": "Enhance equity and inclusion",
    "2.3": "Shift to just governance",
    "3.1": "Enhance economic prosperity",
    "3.2": "Enhance livelihoods",
    "4.1": "Conserve and restore ecological diversity",
    "4.2": "Support and enhance social and cultural diversity",
    "4.3": "Enhance economic diversity",
    "5.1": "Restore ecological connectivity",
    "5.2": "Enhance social connectivity",
    "6.1": "Reduce socioecological risks",
    "6.2": "Enhance innovation capacity",
    "7.1": "Enhance nature-based solutions",
    "7.2": "Balance trade-offs between and among humans and nature",
    "7.3": "Harness local context, culture, and knowledge",
    "7.4": "Enhance multi-level compliance",
}


# =============================================================================
# Tool #1: Find Indicators by Principle
# =============================================================================


@tool
def find_indicators_by_principle(
    principle: str, include_criteria: bool = False, n_results: int = 20
) -> str:
    """
    Find all indicators that cover a specific CBA principle.

    Use this to discover indicators relevant to particular sustainability goals:
    - "1" or "Natural Environment" - Environmental protection indicators
    - "2" or "Social Well-being" - Health, equity, governance indicators
    - "3" or "Economic Prosperity" - Income, livelihood indicators
    - "4" or "Diversity" - Biodiversity, cultural diversity indicators
    - "5" or "Connectivity" - Ecological and social connectivity
    - "6" or "Adaptive Capacity" - Risk reduction, innovation indicators
    - "7" or "Harmony" - Nature-based solutions, trade-offs, compliance

    Args:
        principle: Principle number (1-7) or name (e.g., "Natural Environment")
        include_criteria: If True, also show which specific criteria each indicator covers
        n_results: Maximum number of indicators to return (default 20, max 50)

    Returns:
        List of indicators covering the specified principle with their details
    """
    import json

    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_MEDIUM)

    # Resolve principle input to ID
    principle_id = None
    principle_input = principle.strip()

    # Try direct ID match
    if principle_input in PRINCIPLES:
        principle_id = principle_input
    else:
        # Try name match (case-insensitive)
        for pid, pname in PRINCIPLES.items():
            if (
                pname.lower() in principle_input.lower()
                or principle_input.lower() in pname.lower()
            ):
                principle_id = pid
                break

    if not principle_id:
        principle_list = "\n".join(
            [f"  {pid}. {pname}" for pid, pname in PRINCIPLES.items()]
        )
        return f"Unknown principle: '{principle}'\n\nAvailable principles:\n{principle_list}"

    principle_name = PRINCIPLES[principle_id]

    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        # Query by principle flag
        results = collection.get(
            where={f"principle_{principle_id}": True},
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs:
            return f"No indicators found covering Principle {principle_id}: {principle_name}"

        # Sort by total criteria covered (descending)
        items: list[tuple[str, dict[str, Any]]] = [
            (doc, cast("dict[str, Any]", meta))
            for doc, meta in zip(docs, metas or [], strict=False)
        ]
        items.sort(key=lambda x: x[1].get("total_criteria", 0), reverse=True)

        # Limit results
        items = items[:n_results]

        output = [
            f"Found {len(items)} indicators covering Principle {principle_id}: {principle_name}\n"
        ]

        for doc, meta in items:
            indicator_id = meta.get("id", "N/A")
            component = meta.get("component", "N/A")
            ind_class = meta.get("class", "N/A")

            # Extract indicator name from document
            doc_lines = doc.split("\n")
            indicator_name = (
                doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
            )

            output.append(f"[{indicator_id}] {indicator_name}")
            output.append(f"    Component: {component} | Class: {ind_class}")
            output.append(
                f"    Principles: {meta.get('total_principles', 0)} | Criteria: {meta.get('total_criteria', 0)}"
            )

            if include_criteria:
                # Show which criteria this indicator covers for this principle
                criteria_json = meta.get("criteria_json", "{}")
                try:
                    criteria = json.loads(criteria_json)
                    relevant_criteria = {
                        cid: marking
                        for cid, marking in criteria.items()
                        if cid.startswith(f"{principle_id}.")
                    }
                    if relevant_criteria:
                        output.append(f"    Criteria for Principle {principle_id}:")
                        for cid, marking in sorted(relevant_criteria.items()):
                            label = "(Primary)" if marking == "P" else ""
                            cname = CRITERIA.get(cid, "")
                            output.append(f"      - {cid} {cname} {label}")
                except json.JSONDecodeError:
                    pass

            output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"Error searching by principle: {e!s}"


# =============================================================================
# Tool #3: Method Feasibility Filter
# =============================================================================


@tool
def find_feasible_methods(
    indicator: str,
    max_cost: str = "any",
    min_ease: str = "any",
    min_accuracy: str = "any",
) -> str:
    """
    Find measurement methods for an indicator filtered by practical constraints.

    Use this to find methods that match your project's resources and capabilities.

    Args:
        indicator: Indicator ID (e.g., "107") or name (e.g., "Soil organic carbon")
        max_cost: Maximum acceptable cost - "Low", "Medium", "High", or "any"
        min_ease: Minimum ease of use - "Low", "Medium", "High", or "any"
        min_accuracy: Minimum accuracy required - "Low", "Medium", "High", or "any"

    Returns:
        Filtered list of measurement methods with their evaluation criteria
    """
    # Resolve indicator to ID
    indicator_id, name_or_error = _resolve_indicator_id(indicator)

    if indicator_id is None:
        return name_or_error or "Unknown error"

    try:
        collection = _get_collection("methods")

        if collection.count() == 0:
            return "Methods collection is empty. Run: python scripts/ingest_excel.py"

        # Get the methods document for this indicator
        results = collection.get(
            ids=[f"methods_for_indicator:{indicator_id}"],
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs or not docs[0]:
            return f"No measurement methods found for indicator {indicator_id}."

        doc = docs[0]
        meta = cast("dict[str, Any]", metas[0] if metas else {})

        # Parse the document to extract individual methods
        # The document format has "--- Method N ---" separators
        method_sections = doc.split("--- Method ")
        methods: list[dict[str, str]] = []

        for section in method_sections[1:]:  # Skip header
            lines = section.strip().split("\n")
            method_info = {"number": lines[0].split(" ")[0] if lines else "?"}

            for line in lines[1:]:
                if line.startswith("Method (General):"):
                    method_info["general"] = line.replace(
                        "Method (General):", ""
                    ).strip()
                elif line.startswith("Method (Specific):"):
                    method_info["specific"] = line.replace(
                        "Method (Specific):", ""
                    ).strip()
                elif line.startswith("Notes:"):
                    method_info["notes"] = line.replace("Notes:", "").strip()
                elif line.startswith("Evaluation:"):
                    eval_str = line.replace("Evaluation:", "").strip()
                    for part in eval_str.split(","):
                        part = part.strip()
                        if part.startswith("Accuracy:"):
                            method_info["accuracy"] = part.replace(
                                "Accuracy:", ""
                            ).strip()
                        elif part.startswith("Ease:"):
                            method_info["ease"] = part.replace("Ease:", "").strip()
                        elif part.startswith("Cost:"):
                            method_info["cost"] = part.replace("Cost:", "").strip()
                elif line.startswith("References:"):
                    method_info["references"] = line.replace("References:", "").strip()

            methods.append(method_info)

        # Define level ordering for filtering
        level_order = {"Low": 1, "Medium": 2, "High": 3}

        def passes_filter(method: dict) -> bool:
            # Cost filter (lower is better, so we want cost <= max_cost)
            if max_cost.lower() != "any":
                method_cost = method.get("cost", "")
                max_level = level_order.get(max_cost.capitalize(), 3)
                method_level = level_order.get(method_cost, 3)
                if method_level > max_level:
                    return False

            # Ease filter (higher is better, so we want ease >= min_ease)
            if min_ease.lower() != "any":
                method_ease = method.get("ease", "")
                min_level = level_order.get(min_ease.capitalize(), 1)
                method_level = level_order.get(method_ease, 1)
                if method_level < min_level:
                    return False

            # Accuracy filter (higher is better)
            if min_accuracy.lower() != "any":
                method_accuracy = method.get("accuracy", "")
                min_level = level_order.get(min_accuracy.capitalize(), 1)
                method_level = level_order.get(method_accuracy, 1)
                if method_level < min_level:
                    return False

            return True

        # Filter methods
        filtered = [m for m in methods if passes_filter(m)]

        # Build output
        indicator_name = meta.get("indicator", f"Indicator {indicator_id}")

        output = [f"Measurement Methods for: {indicator_name}"]
        output.append(
            f"Filter: Cost≤{max_cost}, Ease≥{min_ease}, Accuracy≥{min_accuracy}"
        )
        output.append(f"Results: {len(filtered)} of {len(methods)} methods match\n")

        if not filtered:
            output.append("No methods match your criteria. Try relaxing the filters.")
            output.append("\nAll methods for this indicator:")
            output.extend(
                f"  - {m.get('general', 'Unknown')} (Cost: {m.get('cost', '?')}, Ease: {m.get('ease', '?')}, Accuracy: {m.get('accuracy', '?')})"
                for m in methods[:5]
            )
        else:
            for i, m in enumerate(filtered, 1):
                output.append(f"--- Method {i} ---")
                if m.get("general"):
                    output.append(f"General: {m['general']}")
                if m.get("specific"):
                    output.append(f"Specific: {m['specific']}")
                if m.get("notes"):
                    output.append(f"Notes: {m['notes']}")
                output.append(
                    f"Evaluation: Cost={m.get('cost', '?')}, Ease={m.get('ease', '?')}, Accuracy={m.get('accuracy', '?')}"
                )
                if m.get("references"):
                    output.append(f"References: {m['references']}")
                output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"Error filtering methods: {e!s}"


# =============================================================================
# Tool #5: List Indicators by Component
# =============================================================================


@tool
def list_indicators_by_component(component: str, n_results: int = 30) -> str:
    """
    List all indicators for a specific component category.

    Components organize indicators by their measurement domain:
    - "Biotic" - Living systems: biodiversity, species, ecosystem health
    - "Abiotic" - Physical environment: soil, water, climate, air
    - "Socio-economic" - Human systems: income, labor, community, gender

    Args:
        component: Component name - "Biotic", "Abiotic", or "Socio-economic"
        n_results: Maximum indicators to return (default 30, max 100)

    Returns:
        List of indicators grouped by class within the component
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_LARGE)

    # Normalize component input
    component_map = {
        "biotic": "Biotic",
        "abiotic": "Abiotic",
        "socio-economic": "Socio-economic",
        "socioeconomic": "Socio-economic",
        "social": "Socio-economic",
        "economic": "Socio-economic",
    }

    component_normalized = component_map.get(component.lower().strip())

    if not component_normalized:
        return f"Unknown component: '{component}'\n\nAvailable components:\n  - Biotic (living systems)\n  - Abiotic (physical environment)\n  - Socio-economic (human systems)"

    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        results = collection.get(
            where={"component": component_normalized},
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs:
            return f"No indicators found for component: {component_normalized}"

        # Group by class
        by_class: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for doc, meta in zip(docs, metas or [], strict=False):
            meta = cast("dict[str, Any]", meta)
            ind_class = str(meta.get("class", "Unknown"))
            if ind_class not in by_class:
                by_class[ind_class] = []
            by_class[ind_class].append((doc, meta))

        # Sort classes alphabetically
        sorted_classes = sorted(by_class.keys())

        output = [f"=== {component_normalized} Indicators ==="]
        output.append(f"Total: {len(docs)} indicators across {len(by_class)} classes\n")

        count = 0
        for ind_class in sorted_classes:
            if count >= n_results:
                break

            items = by_class[ind_class]
            output.append(f"📁 {ind_class} ({len(items)} indicators)")

            for doc, meta in items:
                if count >= n_results:
                    break

                indicator_id = meta.get("id", "?")
                doc_lines = doc.split("\n")
                indicator_name = (
                    doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
                )
                unit = meta.get("unit", "")

                output.append(f"  [{indicator_id}] {indicator_name}")
                if unit:
                    output.append(f"       Unit: {unit}")

                count += 1

            output.append("")

        if count < len(docs):
            output.append(f"... and {len(docs) - count} more indicators")

        return "\n".join(output)

    except Exception as e:
        return f"Error listing indicators: {e!s}"


# =============================================================================
# Tool #6: Export Indicator Selection (Markdown)
# =============================================================================


@tool
def export_indicator_selection(
    indicator_ids: list[int], include_methods: bool = True
) -> str:
    """
    Generate a formatted markdown report of selected indicators.

    Use this to create documentation for your indicator selection that can be
    saved, shared, or included in project reports.

    Args:
        indicator_ids: List of indicator IDs to include (e.g., [17, 107, 45])
        include_methods: Whether to include measurement methods (default True)

    Returns:
        Markdown-formatted report with indicator details and methods
    """
    import json

    if not indicator_ids:
        return "No indicator IDs provided. Please specify a list of indicator IDs."

    if len(indicator_ids) > 20:
        return "Too many indicators. Please limit to 20 or fewer for export."

    try:
        indicators_coll = _get_collection("indicators")
        methods_coll = _get_collection("methods")

        output = ["# CBA Indicator Selection Report\n"]
        output.append(f"**Indicators selected:** {len(indicator_ids)}\n")
        output.append("---\n")

        found_count = 0

        for ind_id in indicator_ids:
            # Get indicator
            ind_results = indicators_coll.get(
                ids=[f"indicator:{ind_id}"],
                include=["documents", "metadatas"],
            )

            ind_docs = ind_results.get("documents")
            ind_metas = ind_results.get("metadatas")

            if not ind_docs or not ind_docs[0]:
                output.append(f"## ⚠️ Indicator {ind_id} - Not Found\n")
                continue

            found_count += 1
            doc = ind_docs[0]
            meta = cast("dict[str, Any]", ind_metas[0] if ind_metas else {})

            # Extract indicator name
            doc_lines = doc.split("\n")
            indicator_name = (
                doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
            )

            output.append(f"## {ind_id}. {indicator_name}\n")

            # Basic info table
            output.append("| Property | Value |")
            output.append("|----------|-------|")
            output.append(f"| Component | {meta.get('component', 'N/A')} |")
            output.append(f"| Class | {meta.get('class', 'N/A')} |")
            output.append(f"| Unit | {meta.get('unit', 'N/A')} |")
            output.append(f"| Principles Covered | {meta.get('total_principles', 0)} |")
            output.append(f"| Criteria Covered | {meta.get('total_criteria', 0)} |")
            output.append("")

            # Measurement approaches
            approaches = []
            if meta.get("field_methods"):
                approaches.append("Field methods")
            if meta.get("lab_methods"):
                approaches.append("Lab methods")
            if meta.get("remote_sensing"):
                approaches.append("Remote sensing")
            if meta.get("social_participatory"):
                approaches.append("Social/participatory")
            if meta.get("production_audits"):
                approaches.append("Production audits")

            if approaches:
                output.append(f"**Measurement approaches:** {', '.join(approaches)}\n")

            # Principles and criteria
            principles_json = str(meta.get("principles_json", "[]"))
            criteria_json = str(meta.get("criteria_json", "{}"))

            try:
                principles = json.loads(principles_json)
                criteria = json.loads(criteria_json)

                if principles:
                    output.append("**Principles:**")
                    for pid in sorted(principles):
                        pname = PRINCIPLES.get(pid, "Unknown")
                        output.append(f"- {pid}. {pname}")

                        # Show criteria for this principle
                        for cid, marking in sorted(criteria.items()):
                            if cid.startswith(f"{pid}."):
                                cname = CRITERIA.get(cid, "")
                                label = " *(Primary)*" if marking == "P" else ""
                                output.append(f"  - {cid} {cname}{label}")

                    output.append("")

            except json.JSONDecodeError:
                pass

            # Methods
            if include_methods:
                method_results = methods_coll.get(
                    ids=[f"methods_for_indicator:{ind_id}"],
                    include=["documents", "metadatas"],
                )

                method_docs = method_results.get("documents")
                method_metas = method_results.get("metadatas")

                if method_docs and method_docs[0]:
                    method_meta = cast(
                        "dict[str, Any]", method_metas[0] if method_metas else {}
                    )
                    method_count = int(method_meta.get("method_count", 0))

                    output.append(
                        f"### Measurement Methods ({method_count} available)\n"
                    )

                    # Summary of method quality
                    quality_notes = []
                    if method_meta.get("has_high_accuracy"):
                        quality_notes.append("✅ High accuracy methods available")
                    if method_meta.get("has_low_cost"):
                        quality_notes.append("💰 Low cost options available")
                    if method_meta.get("has_high_ease"):
                        quality_notes.append("👍 Easy-to-use methods available")

                    if quality_notes:
                        output.extend(f"- {note}" for note in quality_notes)
                        output.append("")

                    # Parse and include top methods with OA links
                    method_doc = method_docs[0]
                    method_sections = method_doc.split("--- Method ")

                    for section in method_sections[1:4]:  # Limit to first 3 methods
                        lines = section.strip().split("\n")
                        output.append(f"**Method {lines[0].split(' ')[0]}**")

                        for line in lines[1:]:
                            if (
                                line.startswith("Method (")
                                or line.startswith("Notes:")
                                or line.startswith("Evaluation:")
                            ):
                                output.append(f"- {line}")
                            elif line.startswith("References:"):
                                # Process references to add OA badges and PDF links
                                refs_text = line.replace("References:", "").strip()
                                if refs_text and refs_text != "None":
                                    # Parse citations (semicolon-separated)
                                    citations = [
                                        c.strip() for c in refs_text.split(";")
                                    ]
                                    formatted_citations = []
                                    for citation in citations:
                                        if not citation:
                                            continue
                                        # Check for OA badge and PDF link patterns
                                        if "🔓" in citation and "[PDF]" in citation:
                                            # Already formatted with OA
                                            formatted_citations.append(citation)
                                        elif citation == "None" or citation == "N/A":
                                            continue
                                        else:
                                            # Regular citation without OA
                                            formatted_citations.append(citation)

                                    if formatted_citations:
                                        output.append(
                                            f"- References: {'; '.join(formatted_citations)}"
                                        )

                        output.append("")

                    if method_count > 3:
                        output.append(f"*... and {method_count - 3} more methods*\n")

            output.append("---\n")

        # Summary
        output.append("## Summary\n")
        output.append(f"- **Total indicators selected:** {len(indicator_ids)}")
        output.append(f"- **Indicators found:** {found_count}")
        if found_count < len(indicator_ids):
            output.append(
                f"- **Indicators not found:** {len(indicator_ids) - found_count}"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error generating export: {e!s}"


# =============================================================================
# Tool: List Available Classes
# =============================================================================


@tool
def list_available_classes() -> str:
    """
    List all indicator classes available in the knowledge base.

    Classes are thematic groupings within each component:
    - Biotic: Biodiversity, Ecosystems, Traits, etc.
    - Abiotic: Soil quality, Soil carbon, Water quality, Microclimate, etc.
    - Socio-economic: Financial well-being, Human capital, Social capital, etc.

    Use this to discover what categories of indicators are available before
    searching or filtering.

    Returns:
        List of all classes organized by component with indicator counts
    """
    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        results = collection.get(include=["metadatas"])
        metas = results.get("metadatas") or []

        # Group by component -> class
        by_component: dict[str, dict[str, int]] = {}
        for meta in metas:
            meta = cast("dict[str, Any]", meta)
            component = str(meta.get("component", "Unknown"))
            ind_class = str(meta.get("class", "Unknown"))

            if component not in by_component:
                by_component[component] = {}
            if ind_class not in by_component[component]:
                by_component[component][ind_class] = 0
            by_component[component][ind_class] += 1

        output = ["=== Available Indicator Classes ===\n"]

        # Sort components in logical order
        component_order = ["Biotic", "Abiotic", "Socio-economic"]
        for component in component_order:
            if component not in by_component:
                continue

            classes = by_component[component]
            total = sum(classes.values())
            output.append(f"📦 {component} ({total} indicators)")

            for cls_name in sorted(classes.keys()):
                count = classes[cls_name]
                output.append(f"   └─ {cls_name} ({count})")

            output.append("")

        output.append(
            "Use find_indicators_by_class(class_name) to browse indicators in a specific class."
        )

        return "\n".join(output)

    except Exception as e:
        return f"Error listing classes: {e!s}"


# =============================================================================
# Tool: Find Indicators by Class
# =============================================================================


@tool
def find_indicators_by_class(class_name: str, n_results: int = 30) -> str:
    """
    Find all indicators belonging to a specific class.

    Classes are thematic groupings like:
    - Biodiversity, Ecosystems, Traits (Biotic)
    - Soil quality, Soil carbon, Water quality, Microclimate (Abiotic)
    - Financial well-being, Human capital, Social capital (Socio-economic)

    Use list_available_classes() first to see all available classes.

    Args:
        class_name: The class name (e.g., "Biodiversity", "Soil carbon", "Financial well-being")
        n_results: Maximum indicators to return (default 30, max 100)

    Returns:
        List of indicators in the specified class with their details
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_LARGE)

    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        # Get all indicators and filter by class (case-insensitive)
        results = collection.get(include=["documents", "metadatas"])

        docs = results.get("documents") or []
        metas = results.get("metadatas") or []

        # Find matching class (case-insensitive)
        class_normalized = class_name.strip().lower()
        matching: list[tuple[str, dict[str, Any]]] = []

        for doc, meta in zip(docs, metas, strict=False):
            meta = cast("dict[str, Any]", meta)
            if str(meta.get("class", "")).lower() == class_normalized:
                matching.append((doc, meta))

        if not matching:
            # Get available classes for helpful error
            all_classes = sorted(
                {str(cast("dict[str, Any]", m).get("class", "")) for m in metas}
            )
            return (
                f"Class '{class_name}' not found.\n\nAvailable classes:\n"
                + "\n".join(f"  - {c}" for c in all_classes)
            )

        # Sort by total criteria covered (descending)
        matching.sort(key=lambda x: x[1].get("total_criteria", 0), reverse=True)
        matching = matching[:n_results]

        # Get actual class name (proper case)
        actual_class = matching[0][1].get("class", class_name)
        component = matching[0][1].get("component", "Unknown")

        output = [f"=== {actual_class} Indicators ({component}) ==="]
        output.append(f"Found {len(matching)} indicators\n")

        for doc, meta in matching:
            indicator_id = meta.get("id", "?")
            doc_lines = doc.split("\n")
            indicator_name = (
                doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
            )
            unit = meta.get("unit", "")

            output.append(f"[{indicator_id}] {indicator_name}")
            if unit:
                output.append(f"    Unit: {unit}")
            output.append(
                f"    Principles: {meta.get('total_principles', 0)} | Criteria: {meta.get('total_criteria', 0)}"
            )

            # Show measurement approaches
            approaches = []
            if meta.get("field_methods"):
                approaches.append("Field")
            if meta.get("lab_methods"):
                approaches.append("Lab")
            if meta.get("remote_sensing"):
                approaches.append("Remote sensing")
            if meta.get("social_participatory"):
                approaches.append("Participatory")
            if meta.get("production_audits"):
                approaches.append("Audits")
            if approaches:
                output.append(f"    Methods: {', '.join(approaches)}")

            output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"Error finding indicators by class: {e!s}"


# =============================================================================
# Tool: Find Indicators by Measurement Approach
# =============================================================================


@tool
def find_indicators_by_measurement_approach(approach: str, n_results: int = 30) -> str:
    """
    Find indicators that can be measured using a specific approach.

    Available measurement approaches:
    - "field" or "field methods" - Direct field observation and sampling
    - "lab" or "lab methods" - Laboratory analysis
    - "remote" or "remote sensing" - Satellite imagery and remote sensing
    - "participatory" or "social" - Social surveys and participatory methods
    - "audit" or "production" - Production assessments and audits

    Use this to find indicators compatible with your available resources.

    Args:
        approach: Measurement approach (field, lab, remote, participatory, audit)
        n_results: Maximum indicators to return (default 30, max 100)

    Returns:
        List of indicators measurable with the specified approach
    """
    n_results = min(max(1, n_results), _MAX_SEARCH_RESULTS_LARGE)

    # Map input to metadata field
    approach_map = {
        "field": "field_methods",
        "field methods": "field_methods",
        "lab": "lab_methods",
        "lab methods": "lab_methods",
        "laboratory": "lab_methods",
        "remote": "remote_sensing",
        "remote sensing": "remote_sensing",
        "satellite": "remote_sensing",
        "participatory": "social_participatory",
        "social": "social_participatory",
        "survey": "social_participatory",
        "audit": "production_audits",
        "audits": "production_audits",
        "production": "production_audits",
    }

    approach_normalized = approach.strip().lower()
    field_name = approach_map.get(approach_normalized)

    if not field_name:
        return f"Unknown approach: '{approach}'\n\nAvailable approaches:\n  - field (field methods)\n  - lab (laboratory analysis)\n  - remote (remote sensing & modelling)\n  - participatory (social and participatory methods)\n  - audit (production assessments)"

    # Human-readable names
    approach_names = {
        "field_methods": "Field Methods",
        "lab_methods": "Lab Methods",
        "remote_sensing": "Remote Sensing & Modelling",
        "social_participatory": "Social & Participatory Methods",
        "production_audits": "Production Assessments & Audits",
    }

    try:
        collection = _get_collection("indicators")

        if collection.count() == 0:
            return "Knowledge base is empty. Run: python scripts/ingest_excel.py"

        # Query by approach flag
        results = collection.get(
            where={field_name: True},
            include=["documents", "metadatas"],
        )

        docs = results.get("documents")
        metas = results.get("metadatas")

        if not docs:
            return f"No indicators found with {approach_names[field_name]}."

        # Sort by total criteria covered
        items: list[tuple[str, dict[str, Any]]] = [
            (doc, cast("dict[str, Any]", meta))
            for doc, meta in zip(docs, metas or [], strict=False)
        ]
        items.sort(key=lambda x: x[1].get("total_criteria", 0), reverse=True)
        items = items[:n_results]

        output = [f"=== Indicators Measurable via {approach_names[field_name]} ==="]
        output.append(f"Found {len(docs)} indicators (showing {len(items)})\n")

        # Group by component for organization
        by_component: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for doc, meta in items:
            comp = str(meta.get("component", "Unknown"))
            if comp not in by_component:
                by_component[comp] = []
            by_component[comp].append((doc, meta))

        for component in ["Biotic", "Abiotic", "Socio-economic"]:
            if component not in by_component:
                continue

            output.append(f"📦 {component}")
            for doc, meta in by_component[component]:
                indicator_id = meta.get("id", "?")
                doc_lines = doc.split("\n")
                indicator_name = (
                    doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
                )
                ind_class = meta.get("class", "")

                output.append(f"  [{indicator_id}] {indicator_name}")
                output.append(
                    f"      Class: {ind_class} | Principles: {meta.get('total_principles', 0)}"
                )

            output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"Error finding indicators by approach: {e!s}"


# =============================================================================
# Tool: Compare Indicators
# =============================================================================


@tool
def compare_indicators(indicator_ids: list[int]) -> str:
    """
    Compare multiple indicators side-by-side.

    Use this to evaluate trade-offs between similar indicators based on:
    - Component and class
    - Measurement approaches available
    - Principle and criteria coverage
    - Method characteristics (if available)

    Args:
        indicator_ids: List of 2-5 indicator IDs to compare (e.g., [107, 100, 106])

    Returns:
        Side-by-side comparison table of the indicators
    """

    if not indicator_ids:
        return "No indicator IDs provided. Please specify 2-5 indicator IDs to compare."

    if len(indicator_ids) < 2:
        return "Please provide at least 2 indicators to compare."

    if len(indicator_ids) > 5:
        return "Too many indicators. Please limit to 5 or fewer for comparison."

    try:
        indicators_coll = _get_collection("indicators")
        methods_coll = _get_collection("methods")

        # Fetch all indicators
        indicator_data: list[IndicatorDataDict] = []
        for ind_id in indicator_ids:
            results = indicators_coll.get(
                ids=[f"indicator:{ind_id}"],
                include=["documents", "metadatas"],
            )
            docs = results.get("documents")
            metas = results.get("metadatas")

            if docs and docs[0]:
                doc = cast("str", docs[0])
                meta = cast("dict[str, Any]", metas[0] if metas else {})

                # Extract name
                doc_lines = doc.split("\n")
                name = (
                    doc_lines[0].replace("Indicator: ", "") if doc_lines else "Unknown"
                )

                # Get method info
                method_results = methods_coll.get(
                    ids=[f"methods_for_indicator:{ind_id}"],
                    include=["metadatas"],
                )
                method_metas = method_results.get("metadatas")
                method_meta = cast(
                    "dict[str, Any]",
                    method_metas[0] if method_metas and method_metas[0] else {},
                )

                indicator_data.append(
                    {
                        "id": ind_id,
                        "name": name,
                        "meta": meta,
                        "method_meta": method_meta,
                    }
                )
            else:
                indicator_data.append(
                    {
                        "id": ind_id,
                        "name": f"NOT FOUND (ID: {ind_id})",
                        "meta": {},
                        "method_meta": {},
                    }
                )

        # Build comparison output
        output = ["# Indicator Comparison\n"]

        # Basic info table
        output.append("## Overview")
        output.append("")
        output.append(
            "| Property | "
            + " | ".join(f"**{d['id']}**" for d in indicator_data)
            + " |"
        )
        output.append("|----------|" + "|".join("-" * 10 for _ in indicator_data) + "|")

        # Truncate indicator names for table display
        names = [
            d["name"][:30] + "..." if len(d["name"]) > 30 else d["name"]
            for d in indicator_data
        ]
        output.append("| Name | " + " | ".join(names) + " |")

        # Component
        components = [d["meta"].get("component", "-") for d in indicator_data]
        output.append("| Component | " + " | ".join(components) + " |")

        # Class
        classes = [d["meta"].get("class", "-") for d in indicator_data]
        output.append("| Class | " + " | ".join(classes) + " |")

        # Unit
        units = [d["meta"].get("unit", "-") for d in indicator_data]
        output.append("| Unit | " + " | ".join(units) + " |")

        output.append("")

        # Measurement approaches
        output.append("## Measurement Approaches")
        output.append("")
        output.append(
            "| Approach | "
            + " | ".join(f"**{d['id']}**" for d in indicator_data)
            + " |"
        )
        output.append("|----------|" + "|".join("-" * 10 for _ in indicator_data) + "|")

        approaches = [
            ("Field methods", "field_methods"),
            ("Lab methods", "lab_methods"),
            ("Remote sensing", "remote_sensing"),
            ("Participatory", "social_participatory"),
            ("Production audits", "production_audits"),
        ]

        for approach_name, field in approaches:
            values = ["✅" if d["meta"].get(field) else "❌" for d in indicator_data]
            output.append(f"| {approach_name} | " + " | ".join(values) + " |")

        output.append("")

        # Principle coverage
        output.append("## Principle Coverage")
        output.append("")
        output.append(
            "| Principle | "
            + " | ".join(f"**{d['id']}**" for d in indicator_data)
            + " |"
        )
        output.append("|----------|" + "|".join("-" * 10 for _ in indicator_data) + "|")

        for pid, pname in PRINCIPLES.items():
            values = [
                "✅" if d["meta"].get(f"principle_{pid}") else "❌"
                for d in indicator_data
            ]
            output.append(f"| {pid}. {pname} | " + " | ".join(values) + " |")

        # Totals
        p_totals = [str(d["meta"].get("total_principles", 0)) for d in indicator_data]
        c_totals = [str(d["meta"].get("total_criteria", 0)) for d in indicator_data]
        output.append("| **Total Principles** | " + " | ".join(p_totals) + " |")
        output.append("| **Total Criteria** | " + " | ".join(c_totals) + " |")

        output.append("")

        # Method quality (if available)
        output.append("## Method Quality")
        output.append("")
        output.append(
            "| Quality | " + " | ".join(f"**{d['id']}**" for d in indicator_data) + " |"
        )
        output.append("|---------|" + "|".join("-" * 10 for _ in indicator_data) + "|")

        method_counts = [
            str(d["method_meta"].get("method_count", 0)) for d in indicator_data
        ]
        output.append("| Methods available | " + " | ".join(method_counts) + " |")

        high_accuracy = [
            "✅" if d["method_meta"].get("has_high_accuracy") else "❌"
            for d in indicator_data
        ]
        output.append("| High accuracy option | " + " | ".join(high_accuracy) + " |")

        low_cost = [
            "✅" if d["method_meta"].get("has_low_cost") else "❌"
            for d in indicator_data
        ]
        output.append("| Low cost option | " + " | ".join(low_cost) + " |")

        high_ease = [
            "✅" if d["method_meta"].get("has_high_ease") else "❌"
            for d in indicator_data
        ]
        output.append("| Easy-to-use option | " + " | ".join(high_ease) + " |")

        return "\n".join(output)

    except Exception as e:
        return f"Error comparing indicators: {e!s}"
