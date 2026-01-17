"""
Use Case ingestion script for CBA ME Indicators knowledge base.

Ingests example project data (outcome-indicator mappings + PDF summaries):
1. Load Excel workbook - Parse outcome-indicator mappings
2. Load PDF - Extract project overview text
3. Resolve indicator names to IDs - Fuzzy match against master library
4. Build RAG documents - Outcome docs + overview doc
5. Upsert to ChromaDB - Single `usecases` collection

Usage:
    python scripts/ingest_usecases.py
    python scripts/ingest_usecases.py --clear       # Clear usecases collection first
    python scripts/ingest_usecases.py --dry-run     # Show what would be indexed
    python scripts/ingest_usecases.py --verbose     # Detailed output

Document IDs:
    - usecase:{slug}:overview        - Project summary from PDF
    - usecase:{slug}:outcome:{id}    - One per outcome row
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import chromadb
import pandas as pd

if TYPE_CHECKING:
    from chromadb.api import ClientAPI


class IngestionResult(TypedDict):
    """Type definition for ingestion result dictionary."""

    usecases_processed: int
    total_docs: int
    errors: list[str]


# Add src to path for agentic_cba_indicators imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_cba_indicators.paths import get_kb_path
from agentic_cba_indicators.tools._embedding import get_embeddings_batch

# =============================================================================
# Configuration
# =============================================================================


USECASES_DIR = Path(__file__).parent.parent / "cba_inputs" / "example"
MASTER_EXCEL = (
    Path(__file__).parent.parent / "cba_inputs" / "CBA ME Indicators List.xlsx"
)
KB_PATH = get_kb_path()

FUZZY_MATCH_THRESHOLD = 0.85  # 85% similarity required for name-to-ID matching


# Use case definitions - add new projects here
USE_CASES = [
    {
        "slug": "regen_cotton_chad",
        "name": "Regenerative Cotton in Chad",
        "country": "Chad",
        "region": "Africa",
        "commodity": "Cotton",
        "excel_file": "Indicators_for_Use_Case_Regenerative_Cotton_in_Chad.xlsx",
        "pdf_file": "Use Case Regenerative Cotton in Chad.pdf",
        "excel_sheet": "Suggested indicators",
    },
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class UseCaseOverviewDoc:
    """Project overview document from PDF."""

    use_case_slug: str
    use_case_name: str
    country: str
    region: str
    commodity: str
    summary_text: str
    outcome_count: int = 0

    @property
    def doc_id(self) -> str:
        return f"usecase:{self.use_case_slug}:overview"

    def to_document_text(self) -> str:
        """Generate searchable document text."""
        return f"""Use Case Project: {self.use_case_name}
Country: {self.country}
Region: {self.region}
Commodity: {self.commodity}
Outcomes: {self.outcome_count}

Project Summary:
{self.summary_text}"""

    def to_metadata(self) -> dict:
        return {
            "doc_type": "overview",
            "use_case_slug": self.use_case_slug,
            "use_case_name": self.use_case_name,
            "country": self.country,
            "region": self.region,
            "commodity": self.commodity,
            "outcome_count": self.outcome_count,
        }


@dataclass
class UseCaseOutcomeDoc:
    """Single outcome document with its indicators."""

    use_case_slug: str
    use_case_name: str
    country: str
    region: str
    commodity: str
    outcome_id: str
    outcome_text: str
    selected_indicator_names: list[str] = field(default_factory=list)
    selected_indicator_ids: list[int] = field(default_factory=list)
    extra_indicator_names: list[str] = field(default_factory=list)
    unresolved_names: list[str] = field(default_factory=list)

    @property
    def doc_id(self) -> str:
        return f"usecase:{self.use_case_slug}:outcome:{self.outcome_id}"

    def to_document_text(self) -> str:
        """Generate searchable document text."""
        parts = [
            f"Use Case: {self.use_case_name}",
            f"Country: {self.country} ({self.region})",
            f"Commodity: {self.commodity}",
            "",
            f"Outcome {self.outcome_id}: {self.outcome_text}",
            "",
            f"Selected Indicators ({len(self.selected_indicator_names)}):",
        ]

        parts.extend(f"  - {name}" for name in self.selected_indicator_names)

        if self.extra_indicator_names:
            parts.append("")
            parts.append(f"Extra Indicators ({len(self.extra_indicator_names)}):")
            parts.extend(f"  - {name}" for name in self.extra_indicator_names)

        return "\n".join(parts)

    def to_metadata(self) -> dict:
        return {
            "doc_type": "outcome",
            "use_case_slug": self.use_case_slug,
            "use_case_name": self.use_case_name,
            "country": self.country,
            "region": self.region,
            "commodity": self.commodity,
            "outcome_id": self.outcome_id,
            "indicator_count": len(self.selected_indicator_ids),
            "indicator_ids_json": json.dumps(self.selected_indicator_ids),
            "has_extra_indicators": len(self.extra_indicator_names) > 0,
            "has_unresolved": len(self.unresolved_names) > 0,
        }


# =============================================================================
# PDF Extraction
# =============================================================================


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using pymupdf."""
    try:
        import fitz  # type: ignore[import-not-found]  # pymupdf optional
    except ImportError:
        print("  ⚠ pymupdf not installed. Run: uv add pymupdf")
        return ""

    with fitz.open(pdf_path) as doc:
        text_parts = [page.get_text() for page in doc]

    full_text = "\n".join(text_parts)

    # Clean up text
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)  # Collapse multiple newlines
    full_text = full_text.strip()

    return full_text


def extract_pdf_summary(pdf_path: Path, max_chars: int = 4000) -> str:
    """Extract a summary from the PDF (first N chars, cleaned up)."""
    full_text = extract_pdf_text(pdf_path)

    if not full_text:
        return ""

    # Take first max_chars, try to end at sentence boundary
    if len(full_text) <= max_chars:
        return full_text

    truncated = full_text[:max_chars]
    # Find last sentence ending
    last_period = truncated.rfind(". ")
    if last_period > max_chars // 2:
        truncated = truncated[: last_period + 1]

    return truncated + "\n\n[... document continues ...]"


# =============================================================================
# Indicator Name Resolution
# =============================================================================


def load_master_indicators(excel_path: Path) -> dict[str, int]:
    """Load master indicator list and create name-to-ID mapping."""
    df = pd.read_excel(excel_path, sheet_name="Indicators")

    name_to_id = {}
    for _, row in df.iterrows():
        indicator_id = int(row.get("id", 0))
        indicator_name = str(row.get("Indicator", "")).strip()
        if indicator_id > 0 and indicator_name:
            # Store both original and normalized versions
            name_to_id[indicator_name] = indicator_id
            name_to_id[normalize_text(indicator_name)] = indicator_id

    return name_to_id


def normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, collapse spaces, strip."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def fuzzy_match(
    query: str, candidates: dict[str, int], threshold: float = 0.85
) -> tuple[int | None, float]:
    """Find best fuzzy match for a query string against candidates."""
    query_norm = normalize_text(query)
    best_match = None
    best_score = 0.0

    for name, indicator_id in candidates.items():
        name_norm = normalize_text(name)
        score = SequenceMatcher(None, query_norm, name_norm).ratio()
        if score > best_score:
            best_score = score
            best_match = indicator_id

    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def resolve_indicator_names(
    names: list[str],
    master_lookup: dict[str, int],
    threshold: float = FUZZY_MATCH_THRESHOLD,
    verbose: bool = False,
) -> tuple[list[int], list[str]]:
    """
    Resolve indicator names to IDs using exact + fuzzy matching.

    Returns:
        (resolved_ids, unresolved_names)
    """
    resolved_ids = []
    unresolved = []

    for name in names:
        # Try exact match first
        if name in master_lookup:
            resolved_ids.append(master_lookup[name])
            if verbose:
                print(f"      ✓ Exact: '{name}' → {master_lookup[name]}")
            continue

        # Try normalized exact match
        name_norm = normalize_text(name)
        if name_norm in master_lookup:
            resolved_ids.append(master_lookup[name_norm])
            if verbose:
                print(f"      ✓ Normalized: '{name}' → {master_lookup[name_norm]}")
            continue

        # Try fuzzy match
        indicator_id, score = fuzzy_match(name, master_lookup, threshold)
        if indicator_id is not None:
            resolved_ids.append(indicator_id)
            if verbose:
                print(f"      ✓ Fuzzy ({score:.0%}): '{name}' → {indicator_id}")
        else:
            unresolved.append(name)
            if verbose:
                print(f"      ✗ Unresolved ({score:.0%}): '{name}'")

    return resolved_ids, unresolved


# =============================================================================
# Excel Parsing
# =============================================================================


def parse_semicolon_list(value) -> list[str]:
    """Parse semicolon-delimited list from cell value."""
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    items = [item.strip() for item in text.split(";")]
    return [item for item in items if item]


def load_usecase_excel(
    excel_path: Path,
    sheet_name: str,
    use_case_config: dict,
    master_lookup: dict[str, int],
    verbose: bool = False,
) -> list[UseCaseOutcomeDoc]:
    """Load outcome-indicator mappings from use case Excel file."""
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    outcomes = []
    total_unresolved = []

    for _, row in df.iterrows():
        outcome_id = str(row.get("Outcome id", "")).strip()
        if not outcome_id:
            continue

        outcome_text = str(row.get("Outcome", "")).strip()
        selected_names = parse_semicolon_list(
            row.get("Indicators (selected from CBA ME Indicators List)", "")
        )
        extra_names = parse_semicolon_list(row.get("Extra indicators", ""))

        # Resolve indicator names to IDs
        resolved_ids, unresolved = resolve_indicator_names(
            selected_names, master_lookup, verbose=verbose
        )
        total_unresolved.extend(unresolved)

        outcome = UseCaseOutcomeDoc(
            use_case_slug=use_case_config["slug"],
            use_case_name=use_case_config["name"],
            country=use_case_config["country"],
            region=use_case_config["region"],
            commodity=use_case_config["commodity"],
            outcome_id=outcome_id,
            outcome_text=outcome_text,
            selected_indicator_names=selected_names,
            selected_indicator_ids=resolved_ids,
            extra_indicator_names=extra_names,
            unresolved_names=unresolved,
        )
        outcomes.append(outcome)

    if total_unresolved and verbose:
        print(f"  ⚠ Total unresolved indicator names: {len(total_unresolved)}")

    return outcomes


# =============================================================================
# ChromaDB Operations
# =============================================================================


def get_chroma_client() -> ClientAPI:
    """Get or create persistent ChromaDB client."""
    KB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(KB_PATH))


def upsert_usecase_docs(
    client: ClientAPI,
    overview: UseCaseOverviewDoc | None,
    outcomes: list[UseCaseOutcomeDoc],
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
) -> tuple[int, list[str]]:
    """Upsert use case documents to ChromaDB."""
    collection = client.get_or_create_collection(name="usecases")

    # Build document lists
    all_docs: list[UseCaseOverviewDoc | UseCaseOutcomeDoc] = []
    if overview:
        all_docs.append(overview)
    all_docs.extend(outcomes)

    ids = [doc.doc_id for doc in all_docs]
    documents = [doc.to_document_text() for doc in all_docs]
    metadatas = [doc.to_metadata() for doc in all_docs]

    if dry_run:
        print(f"  [DRY RUN] Would upsert {len(all_docs)} documents")
        if verbose:
            for doc in all_docs[:3]:
                print(f"    - {doc.doc_id}")
            if len(all_docs) > 3:
                print(f"    ... and {len(all_docs) - 3} more")
        return len(all_docs), []

    print(f"  Embedding {len(documents)} documents...")
    embeddings = get_embeddings_batch(documents, strict=strict)

    filtered_ids: list[str] = []
    filtered_docs: list[str] = []
    filtered_metas: list[dict] = []
    filtered_embeddings: list[list[float]] = []
    failed_ids: list[str] = []

    for doc_id, doc, meta, embedding in zip(
        ids, documents, metadatas, embeddings, strict=False
    ):
        if embedding is None:
            failed_ids.append(doc_id)
            continue
        filtered_ids.append(doc_id)
        filtered_docs.append(doc)
        filtered_metas.append(meta)
        filtered_embeddings.append(embedding)

    if failed_ids:
        print(f"  ⚠ Skipping {len(failed_ids)} docs due to embedding failures")

    print("  Upserting to 'usecases' collection...")
    collection.upsert(
        ids=filtered_ids,
        embeddings=filtered_embeddings,  # type: ignore[arg-type]
        documents=filtered_docs,
        metadatas=filtered_metas,  # type: ignore[arg-type]
    )

    return len(filtered_ids), failed_ids


# =============================================================================
# Main Ingestion Logic
# =============================================================================


def ingest_usecase(
    use_case_config: dict,
    master_lookup: dict[str, int],
    client: ClientAPI,
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
) -> dict:
    """Ingest a single use case project."""
    slug = use_case_config["slug"]
    summary = {
        "slug": slug,
        "overview": False,
        "outcomes": 0,
        "resolved_indicators": 0,
        "unresolved_indicators": 0,
        "failed_docs": 0,
    }

    excel_path = USECASES_DIR / use_case_config["excel_file"]
    pdf_path = USECASES_DIR / use_case_config["pdf_file"]

    # Check files exist
    if not excel_path.exists():
        print(f"  ✗ Excel not found: {excel_path}")
        return summary
    if not pdf_path.exists():
        print(f"  ⚠ PDF not found: {pdf_path}")

    # Load outcomes from Excel
    print("  Loading outcomes from Excel...")
    outcomes = load_usecase_excel(
        excel_path,
        use_case_config["excel_sheet"],
        use_case_config,
        master_lookup,
        verbose=verbose,
    )
    print(f"    Found {len(outcomes)} outcomes")

    # Extract PDF summary
    overview = None
    if pdf_path.exists():
        print("  Extracting PDF summary...")
        pdf_summary = extract_pdf_summary(pdf_path)
        if pdf_summary:
            overview = UseCaseOverviewDoc(
                use_case_slug=use_case_config["slug"],
                use_case_name=use_case_config["name"],
                country=use_case_config["country"],
                region=use_case_config["region"],
                commodity=use_case_config["commodity"],
                summary_text=pdf_summary,
                outcome_count=len(outcomes),
            )
            summary["overview"] = True
            if verbose:
                print(f"    Extracted {len(pdf_summary)} chars")

    # Count resolution stats
    for outcome in outcomes:
        summary["resolved_indicators"] += len(outcome.selected_indicator_ids)
        summary["unresolved_indicators"] += len(outcome.unresolved_names)

    # Upsert to ChromaDB
    doc_count, failed_ids = upsert_usecase_docs(
        client,
        overview,
        outcomes,
        verbose=verbose,
        dry_run=dry_run,
        strict=strict,
    )
    _ = doc_count
    summary["failed_docs"] = len(failed_ids)
    summary["outcomes"] = len(outcomes)

    return summary


def ingest(
    clear: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
) -> IngestionResult:
    """Main ingestion function for all use cases."""
    results: IngestionResult = {
        "usecases_processed": 0,
        "total_docs": 0,
        "errors": [],
    }

    # Test Ollama connection
    if not dry_run:
        print("Testing Ollama connection...")
        try:
            test_emb = get_embeddings_batch(["test"], strict=True)
            emb_dim = len(test_emb[0]) if test_emb[0] is not None else 0
            print(f"  ✓ Ollama ready (embedding dim: {emb_dim})")
        except Exception as e:
            results["errors"].append(f"Ollama connection failed: {e}")
            print(f"  ✗ Ollama error: {e}")
            return results

    # Initialize ChromaDB
    print(f"\nInitializing ChromaDB at {KB_PATH}...")
    client = get_chroma_client()

    if clear:
        print("  Clearing usecases collection...")
        try:
            client.delete_collection("usecases")
            print("  ✓ Collection cleared")
        except Exception:
            print("  Collection didn't exist")

    # Load master indicator lookup
    print("\nLoading master indicator library...")
    if not MASTER_EXCEL.exists():
        results["errors"].append(f"Master Excel not found: {MASTER_EXCEL}")
        return results

    master_lookup = load_master_indicators(MASTER_EXCEL)
    print(f"  Loaded {len(master_lookup) // 2} indicators for name resolution")

    # Process each use case
    for use_case_config in USE_CASES:
        print(f"\n{'=' * 50}")
        print(f"Processing: {use_case_config['name']}")
        print(f"{'=' * 50}")

        case_summary = ingest_usecase(
            use_case_config,
            master_lookup,
            client,
            verbose=verbose,
            dry_run=dry_run,
            strict=strict,
        )

        results["usecases_processed"] += 1  # type: ignore[operator]
        if case_summary["overview"]:
            results["total_docs"] += 1  # type: ignore[operator]
        results["total_docs"] += case_summary["outcomes"]  # type: ignore[operator]

        print(f"\n  Summary for {case_summary['slug']}:")
        print(f"    Overview doc: {'Yes' if case_summary['overview'] else 'No'}")
        print(f"    Outcome docs: {case_summary['outcomes']}")
        print(f"    Resolved indicators: {case_summary['resolved_indicators']}")
        print(f"    Unresolved indicators: {case_summary['unresolved_indicators']}")

        if case_summary.get("failed_docs", 0):
            results["errors"].append(
                f"Embedding failed for {case_summary['failed_docs']} documents in {case_summary['slug']}"
            )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ingest use case projects into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/ingest_usecases.py                 # Standard ingestion
    python scripts/ingest_usecases.py --clear         # Clear and rebuild
    python scripts/ingest_usecases.py --dry-run       # Preview without changes
    python scripts/ingest_usecases.py --verbose       # Detailed output
        """,
    )
    parser.add_argument(
        "--clear",
        "-c",
        action="store_true",
        help="Clear usecases collection before ingesting",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail ingestion on any embedding error",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Use Case Projects - Ingestion")
    print("=" * 60)
    print(f"Source: {USECASES_DIR}")
    print(f"Target: {KB_PATH}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    results = ingest(
        clear=args.clear,
        verbose=args.verbose,
        dry_run=args.dry_run,
        strict=args.strict,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Use cases processed: {results['usecases_processed']}")
    print(f"Total documents indexed: {results['total_docs']}")

    if results["errors"]:
        print("\nErrors encountered:")
        for err in results["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    print(f"\n✓ Use cases ready in 'usecases' collection at: {KB_PATH}")


if __name__ == "__main__":
    main()
