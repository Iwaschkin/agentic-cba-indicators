"""
Deterministic Excel ingestion script for CBA ME Indicators knowledge base.

This script follows a predictable, repeatable workflow:
1. Load workbook - Read Indicators and Methods sheets
2. Normalise - Convert flags to booleans, clean citations
3. Build RAG documents - Create stable document IDs
4. Embed - Generate embeddings via Ollama
5. Upsert - Safe incremental updates to ChromaDB
6. Persist - Local storage that survives restarts

Usage:
    python scripts/ingest_excel.py
    python scripts/ingest_excel.py --file path/to/file.xlsx
    python scripts/ingest_excel.py --clear       # Clear and rebuild
    python scripts/ingest_excel.py --dry-run     # Show what would be indexed
    python scripts/ingest_excel.py --verbose     # Detailed output

Collections created:
    - indicators: One document per indicator (224 docs)
    - methods: One document per indicator with ALL methods grouped (223 docs, id=105 has none)
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import httpx
import pandas as pd

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_EXCEL_FILE = (
    Path(__file__).parent.parent / "cba_inputs" / "CBA ME Indicators List.xlsx"
)
KB_PATH = Path(__file__).parent.parent / "kb_data"
OLLAMA_HOST = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
BATCH_SIZE = 5  # Embedding batch size (smaller for large documents)


# =============================================================================
# Data Classes
# =============================================================================

# Principle and Criteria definitions (from Excel column headers)
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

# Excel column mappings for principles and criteria
PRINCIPLE_COLUMNS = {
    "1": "Principle: 1. Natural Environment",
    "2": "Principle: 2. Social Well-being",
    "3": "Principle: 3. Economic Prosperity",
    "4": "Principle: 4. Diversity",
    "5": "Principle: 5. Connectivity",
    "6": "Principle: 6. Adaptive Capacity",
    "7": "Principle: 7. Harmony",
}

CRITERIA_COLUMNS = {
    "1.1": "1.1 Avoid ecosystem degradation",
    "1.2": "1.2 Minimize GHG emissions and enhance sinks",
    "1.3": "1.3. Shift to environmentally sustainable practices",
    "1.4": "1.4. Shift to renewable and bio-based processes",
    "2.1": "2.1 Enhance human health and wellbeing",
    "2.2": "2.2 Enhance equity and inclusion",
    "2.3": "2.3 Shift to just governance",
    "3.1": "3.1 Enhance economic prosperity",
    "3.2": "3.2 Enhance livelihoods",
    "4.1": "4.1 Conserve and restore ecological diversity",
    "4.2": "4.2. Support and enhance social and cultural diversity",
    "4.3": "4.3 Enhance economic diversity",
    "5.1": "5.1 Restore ecological connectivity",
    "5.2": "5.2 Enhance social connectivity",
    "6.1": "6.1 Reduce socioecological risks",
    "6.2": "6.2 Enhance innovation capacity",
    "7.1": "7.1 Enhance nature-based solutions",
    "7.2": "7.2. Balance trade-offs between and among humans and nature",
    "7.3": "7.3. Harness local context, culture, and knowledge",
    "7.4": "7.4 Enhance multi-level compliance",
}


@dataclass
class IndicatorDoc:
    """Represents a single indicator document for RAG."""

    id: int
    component: str
    indicator_class: str
    indicator_text: str
    unit: str
    field_methods: bool
    lab_methods: bool
    remote_sensing: bool
    social_participatory: bool
    production_audits: bool
    principles: list[str]  # List of principle IDs: ["1", "4", "7"]
    criteria: dict[str, str]  # Criteria ID -> marking: {"1.1": "P", "4.1": "x"}

    @property
    def doc_id(self) -> str:
        return f"indicator:{self.id}"

    @property
    def total_principles(self) -> int:
        return len(self.principles)

    @property
    def total_criteria(self) -> int:
        return len(self.criteria)

    def to_document_text(self) -> str:
        """Generate searchable document text."""
        parts = [
            f"Indicator: {self.indicator_text}",
            f"Component: {self.component}",
            f"Class: {self.indicator_class}",
            f"Unit: {self.unit}",
        ]

        categories = []
        if self.field_methods:
            categories.append("Field methods")
        if self.lab_methods:
            categories.append("Lab methods")
        if self.remote_sensing:
            categories.append("Remote sensing & modelling")
        if self.social_participatory:
            categories.append("Social and participatory methods")
        if self.production_audits:
            categories.append("Production assessments and audits")

        if categories:
            parts.append(f"Measurement approaches: {', '.join(categories)}")

        # Add principle coverage with names
        if self.principles:
            principle_names = [
                f"{pid}. {PRINCIPLES[pid]}" for pid in sorted(self.principles)
            ]
            parts.append(f"Principles covered ({len(self.principles)}): {', '.join(principle_names)}")

        # Add criteria coverage with names and markings
        if self.criteria:
            criteria_parts = []
            for cid in sorted(self.criteria.keys()):
                marking = self.criteria[cid]
                marking_label = "(Primary)" if marking == "P" else ""
                criteria_parts.append(f"{cid} {CRITERIA.get(cid, '')} {marking_label}".strip())
            parts.append(f"Criteria covered ({len(self.criteria)}):")
            for cp in criteria_parts:
                parts.append(f"  - {cp}")

        return "\n".join(parts)

    def to_metadata(self) -> dict:
        """Generate metadata for filtering."""
        import json

        return {
            "id": self.id,
            "component": self.component,
            "class": self.indicator_class,
            "unit": self.unit,
            "field_methods": self.field_methods,
            "lab_methods": self.lab_methods,
            "remote_sensing": self.remote_sensing,
            "social_participatory": self.social_participatory,
            "production_audits": self.production_audits,
            "total_principles": self.total_principles,
            "total_criteria": self.total_criteria,
            # Store as JSON strings for ChromaDB compatibility
            "principles_json": json.dumps(self.principles),
            "criteria_json": json.dumps(self.criteria),
            # Individual principle flags for filtering
            "principle_1": "1" in self.principles,
            "principle_2": "2" in self.principles,
            "principle_3": "3" in self.principles,
            "principle_4": "4" in self.principles,
            "principle_5": "5" in self.principles,
            "principle_6": "6" in self.principles,
            "principle_7": "7" in self.principles,
        }


@dataclass
class MethodDoc:
    """Represents a single method row."""

    indicator_id: int
    indicator_text: str
    unit: str
    method_general: str
    method_specific: str
    notes: str
    accuracy: str
    ease: str
    cost: str
    citations: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        """Generate text for a single method."""
        parts = []

        if self.method_general:
            parts.append(f"Method (General): {self.method_general}")
        if self.method_specific:
            parts.append(f"Method (Specific): {self.method_specific}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")

        eval_parts = []
        if self.accuracy:
            eval_parts.append(f"Accuracy: {self.accuracy}")
        if self.ease:
            eval_parts.append(f"Ease: {self.ease}")
        if self.cost:
            eval_parts.append(f"Cost: {self.cost}")

        if eval_parts:
            parts.append(f"Evaluation: {', '.join(eval_parts)}")

        if self.citations:
            parts.append(f"References: {'; '.join(self.citations)}")

        return "\n".join(parts)


@dataclass
class MethodsGroupDoc:
    """All methods for a single indicator, grouped for RAG retrieval."""

    indicator_id: int
    indicator_text: str
    unit: str
    methods: list[MethodDoc] = field(default_factory=list)

    @property
    def doc_id(self) -> str:
        return f"methods_for_indicator:{self.indicator_id}"

    def to_document_text(self) -> str:
        """Generate searchable document with all methods."""
        if not self.methods:
            return ""

        parts = [
            f"Measurement Methods for Indicator {self.indicator_id}:",
            f"Indicator: {self.indicator_text}",
            f"Unit: {self.unit}",
            f"Number of methods: {len(self.methods)}",
            "",
        ]

        for i, method in enumerate(self.methods, 1):
            parts.append(f"--- Method {i} ---")
            parts.append(method.to_text())
            parts.append("")

        return "\n".join(parts)

    def to_metadata(self) -> dict:
        """Generate metadata for filtering."""
        # Collect unique accuracy/ease/cost levels across all methods
        accuracies = list(set(m.accuracy for m in self.methods if m.accuracy))
        eases = list(set(m.ease for m in self.methods if m.ease))
        costs = list(set(m.cost for m in self.methods if m.cost))

        return {
            "indicator_id": self.indicator_id,
            "indicator": self.indicator_text,
            "unit": self.unit,
            "method_count": len(self.methods),
            "has_high_accuracy": "High" in accuracies,
            "has_low_cost": "Low" in costs,
            "has_high_ease": "High" in eases,
        }


# =============================================================================
# Normalisation Helpers
# =============================================================================


def normalize_flag(value) -> bool:
    """Convert x/(x)/blank to boolean. Treats x and (x) as equivalent."""
    if pd.isna(value):
        return False
    val = str(value).strip().lower()
    return val in ["x", "(x)"]


def safe_str(value) -> str:
    """Convert value to string, handling NaN."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_int(value, default: int = 0) -> int:
    """Convert value to int, handling NaN."""
    if pd.isna(value):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def extract_citations(row: pd.Series) -> list[str]:
    """Extract and clean citations from row, including unnamed spillover columns."""
    citations = []

    # Standard citation columns
    for i in range(1, 6):
        doi_col = "DOI" if i == 1 else f"DOI.{i}"
        cite_col = "Citation" if i == 1 else f"Citation.{i}"

        doi = safe_str(row.get(doi_col, ""))
        cite = safe_str(row.get(cite_col, ""))

        if cite or doi:
            if cite and doi:
                citations.append(f"{cite} [DOI: {doi}]")
            elif cite:
                citations.append(cite)
            elif doi:
                citations.append(f"[DOI: {doi}]")

    # Handle unnamed spillover columns (32, 33)
    for col in ["Unnamed: 32", "Unnamed: 33"]:
        spillover = safe_str(row.get(col, ""))
        if spillover and len(spillover) > 5:  # Avoid noise
            citations.append(spillover)

    return citations


# =============================================================================
# Data Loading and Transformation
# =============================================================================


def extract_principles_and_criteria(row: pd.Series) -> tuple[list[str], dict[str, str]]:
    """Extract principle and criteria coverage from a row.
    
    Returns:
        Tuple of (principles list, criteria dict)
        - principles: List of principle IDs that apply (e.g., ["1", "4", "7"])
        - criteria: Dict of criteria ID -> marking (e.g., {"1.1": "P", "4.1": "x"})
    """
    principles = []
    criteria = {}
    
    # Extract principles (marked with x, S, or ?)
    for pid, col_name in PRINCIPLE_COLUMNS.items():
        val = safe_str(row.get(col_name, "")).lower()
        if val in ["x", "s", "?"]:
            principles.append(pid)
    
    # Extract criteria (marked with P, x, S, or ?)
    for cid, col_name in CRITERIA_COLUMNS.items():
        val = safe_str(row.get(col_name, ""))
        if val.upper() in ["P", "X", "S", "?"]:
            criteria[cid] = val.upper()
    
    return principles, criteria


def load_indicators(df: pd.DataFrame) -> list[IndicatorDoc]:
    """Load and normalise indicators from dataframe."""
    indicators = []

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue

        # Extract principle and criteria coverage
        principles, criteria = extract_principles_and_criteria(row)

        doc = IndicatorDoc(
            id=indicator_id,
            component=safe_str(row.get("Component", "")),
            indicator_class=safe_str(row.get("Class", "")),
            indicator_text=safe_str(row.get("Indicator", "")),
            unit=safe_str(row.get("Unit", "")),
            field_methods=normalize_flag(row.get("Field methods")),
            lab_methods=normalize_flag(row.get("Lab methods")),
            remote_sensing=normalize_flag(row.get("Remote sensing & modelling")),
            social_participatory=normalize_flag(row.get("Social and partcipatory")),
            production_audits=normalize_flag(
                row.get("Production assessments and audits")
            ),
            principles=principles,
            criteria=criteria,
        )
        indicators.append(doc)

    return indicators


def load_methods(df: pd.DataFrame) -> dict[int, list[MethodDoc]]:
    """Load and normalise methods, grouped by indicator ID."""
    methods_by_indicator: dict[int, list[MethodDoc]] = {}

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue

        method = MethodDoc(
            indicator_id=indicator_id,
            indicator_text=safe_str(row.get("Indicator", "")),
            unit=safe_str(row.get("Unit", "")),
            method_general=safe_str(row.get("Method  (General)", "")),
            method_specific=safe_str(row.get("Method  (Specific)", "")),
            notes=safe_str(row.get("Notes", "")),
            accuracy=safe_str(row.get("Accuracy (High/Medium/Low)", "")),
            ease=safe_str(row.get("Ease of Use (High/Medium/Low)", "")),
            cost=safe_str(row.get("Financial Cost (High/Medium/Low)", "")),
            citations=extract_citations(row),
        )

        # Only include if method has meaningful content
        if method.method_general or method.method_specific or method.notes:
            if indicator_id not in methods_by_indicator:
                methods_by_indicator[indicator_id] = []
            methods_by_indicator[indicator_id].append(method)

    return methods_by_indicator


def build_methods_group_docs(
    indicators: list[IndicatorDoc], methods_by_indicator: dict[int, list[MethodDoc]]
) -> tuple[list[MethodsGroupDoc], list[int]]:
    """Build grouped method documents and track indicators with no methods."""
    grouped_docs = []
    missing_methods = []

    for indicator in indicators:
        methods = methods_by_indicator.get(indicator.id, [])

        if not methods:
            missing_methods.append(indicator.id)
            continue

        group = MethodsGroupDoc(
            indicator_id=indicator.id,
            indicator_text=indicator.indicator_text,
            unit=indicator.unit,
            methods=methods,
        )
        grouped_docs.append(group)

    return grouped_docs, missing_methods


# =============================================================================
# Embedding
# =============================================================================


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts using Ollama."""
    # Truncate texts that are too long for the embedding model
    MAX_CHARS = 6000  # nomic-embed-text has ~8k token limit, be conservative
    truncated_texts = [
        text[:MAX_CHARS] + "..." if len(text) > MAX_CHARS else text for text in texts
    ]

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{OLLAMA_HOST}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": truncated_texts},
        )
        if response.status_code != 200:
            # Fall back to individual embedding if batch fails
            print(f"      Batch failed, falling back to individual embedding...")
            embeddings = []
            for i, text in enumerate(truncated_texts):
                try:
                    single_resp = client.post(
                        f"{OLLAMA_HOST}/api/embed",
                        json={"model": EMBEDDING_MODEL, "input": text},
                    )
                    single_resp.raise_for_status()
                    embeddings.append(single_resp.json()["embeddings"][0])
                except Exception as e:
                    print(f"      Error embedding doc {i} (len={len(text)}): {e}")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * 768)
            return embeddings
        return response.json()["embeddings"]


def embed_documents(documents: list[str], verbose: bool = False) -> list[list[float]]:
    """Embed all documents in batches."""
    all_embeddings = []
    total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        if verbose:
            print(f"    Embedding batch {batch_num}/{total_batches}...")

        embeddings = get_embeddings_batch(batch)
        all_embeddings.extend(embeddings)

    return all_embeddings


# =============================================================================
# ChromaDB Operations
# =============================================================================


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create persistent ChromaDB client."""
    KB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(KB_PATH))


def upsert_indicators(
    client: chromadb.PersistentClient,
    indicators: list[IndicatorDoc],
    verbose: bool = False,
    dry_run: bool = False,
) -> int:
    """Upsert indicator documents to ChromaDB."""
    collection = client.get_or_create_collection(name="indicators")

    ids = [ind.doc_id for ind in indicators]
    documents = [ind.to_document_text() for ind in indicators]
    metadatas = [ind.to_metadata() for ind in indicators]

    if dry_run:
        print(f"  [DRY RUN] Would upsert {len(indicators)} indicators")
        if verbose and indicators:
            print(f"    Sample ID: {ids[0]}")
            print(f"    Sample doc (first 200 chars): {documents[0][:200]}...")
        return len(indicators)

    print(f"  Embedding {len(documents)} indicator documents...")
    embeddings = embed_documents(documents, verbose=verbose)

    print(f"  Upserting to 'indicators' collection...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(indicators)


def upsert_methods(
    client: chromadb.PersistentClient,
    methods_groups: list[MethodsGroupDoc],
    verbose: bool = False,
    dry_run: bool = False,
) -> int:
    """Upsert grouped method documents to ChromaDB."""
    collection = client.get_or_create_collection(name="methods")

    ids = [mg.doc_id for mg in methods_groups]
    documents = [mg.to_document_text() for mg in methods_groups]
    metadatas = [mg.to_metadata() for mg in methods_groups]

    if dry_run:
        print(f"  [DRY RUN] Would upsert {len(methods_groups)} method groups")
        if verbose and methods_groups:
            print(f"    Sample ID: {ids[0]}")
            print(f"    Sample methods count: {metadatas[0]['method_count']}")
        return len(methods_groups)

    print(f"  Embedding {len(documents)} method group documents...")
    embeddings = embed_documents(documents, verbose=verbose)

    print(f"  Upserting to 'methods' collection...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(methods_groups)


# =============================================================================
# Main Ingestion Logic
# =============================================================================


def ingest(
    excel_file: Path,
    clear: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Main ingestion function.

    Returns:
        Summary dict with counts and any issues found.
    """
    summary = {
        "indicators_count": 0,
        "methods_groups_count": 0,
        "total_methods": 0,
        "missing_methods_indicator_ids": [],
        "errors": [],
    }

    # Step 1: Test Ollama connection
    if not dry_run:
        print("Testing Ollama connection...")
        try:
            test_emb = get_embeddings_batch(["test"])
            print(f"  ✓ Ollama ready (embedding dim: {len(test_emb[0])})")
        except Exception as e:
            summary["errors"].append(f"Ollama connection failed: {e}")
            print(f"  ✗ Ollama error: {e}")
            print(f"  Make sure Ollama is running: ollama serve")
            print(f"  And the model is pulled: ollama pull {EMBEDDING_MODEL}")
            return summary

    # Step 2: Initialize ChromaDB
    print(f"\nInitializing ChromaDB at {KB_PATH}...")
    client = get_chroma_client()

    if clear:
        print("  Clearing existing collections...")
        for coll in client.list_collections():
            client.delete_collection(coll.name)
        print("  ✓ Collections cleared")

    # Step 3: Load workbook
    print(f"\nLoading workbook: {excel_file}")
    xlsx = pd.ExcelFile(excel_file)
    print(f"  Sheets found: {xlsx.sheet_names}")

    indicators_df = pd.read_excel(xlsx, sheet_name="Indicators")
    methods_df = pd.read_excel(xlsx, sheet_name="Methods")
    print(f"  Indicators: {len(indicators_df)} rows")
    print(f"  Methods: {len(methods_df)} rows")

    # Step 4: Normalise and build documents
    print("\nNormalising data...")
    indicators = load_indicators(indicators_df)
    methods_by_indicator = load_methods(methods_df)

    print(f"  Loaded {len(indicators)} indicators")
    print(f"  Loaded methods for {len(methods_by_indicator)} indicators")

    # Step 5: Build grouped method documents
    print("\nBuilding RAG documents...")
    methods_groups, missing_methods = build_methods_group_docs(
        indicators, methods_by_indicator
    )

    summary["missing_methods_indicator_ids"] = missing_methods
    if missing_methods:
        print(f"  ⚠ Indicators with no methods: {missing_methods}")

    total_methods = sum(len(mg.methods) for mg in methods_groups)
    print(f"  Built {len(indicators)} indicator documents")
    print(
        f"  Built {len(methods_groups)} method group documents ({total_methods} total methods)"
    )

    # Step 6: Upsert to ChromaDB
    print("\n[1/2] Processing indicators...")
    summary["indicators_count"] = upsert_indicators(
        client, indicators, verbose=verbose, dry_run=dry_run
    )

    print("\n[2/2] Processing methods...")
    summary["methods_groups_count"] = upsert_methods(
        client, methods_groups, verbose=verbose, dry_run=dry_run
    )
    summary["total_methods"] = total_methods

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic ingestion of CBA ME Indicators into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/ingest_excel.py                    # Standard ingestion
    python scripts/ingest_excel.py --clear            # Clear and rebuild
    python scripts/ingest_excel.py --dry-run          # Preview without changes
    python scripts/ingest_excel.py --verbose          # Detailed output
        """,
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=DEFAULT_EXCEL_FILE,
        help="Path to Excel file",
    )
    parser.add_argument(
        "--clear",
        "-c",
        action="store_true",
        help="Clear existing collections before ingesting",
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
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    print("=" * 60)
    print("CBA ME Indicators - Deterministic Ingestion")
    print("=" * 60)
    print(f"Source: {args.file}")
    print(f"Target: {KB_PATH}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    summary = ingest(
        excel_file=args.file,
        clear=args.clear,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Indicators indexed: {summary['indicators_count']}")
    print(f"Method groups indexed: {summary['methods_groups_count']}")
    print(f"Total individual methods: {summary['total_methods']}")

    if summary["missing_methods_indicator_ids"]:
        print(f"Indicators without methods: {summary['missing_methods_indicator_ids']}")

    if summary["errors"]:
        print(f"\nErrors encountered:")
        for err in summary["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    print(f"\n✓ Knowledge base ready at: {KB_PATH}")


if __name__ == "__main__":
    main()
