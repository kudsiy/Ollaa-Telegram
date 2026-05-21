# -*- coding: utf-8 -*-
"""
semantic_dedup.py
-----------------
Removes duplicate listings from processed_listings using semantic similarity.
Uses Ollama's nomic-embed-text model to generate embeddings, then finds
pairs with cosine similarity above 0.92 and removes the duplicate.

Requirements:
    pip install ollama numpy sqlalchemy psycopg2-binary --break-system-packages

Usage:
    python src/semantic_dedup.py --dry-run     # see what would be removed
    python src/semantic_dedup.py               # run for real
    python src/semantic_dedup.py --batch 100   # process 100 rows at a time
"""

import argparse
import io
import sys
import time
import numpy as np
from sqlalchemy import create_engine, text

def _force_utf8_stdio() -> None:
    """
    Ensure stdout/stderr use UTF-8 on Windows terminals to avoid UnicodeEncodeError.
    Safe no-op on environments that already support UTF-8.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")  # type: ignore[assignment]
    except Exception:
        pass

    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")  # type: ignore[assignment]
    except Exception:
        pass


_force_utf8_stdio()

try:
    import ollama
except ImportError:
    print("ERROR: ollama package not installed.")
    print("Run: pip install ollama")
    raise

DB_URL = "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"
engine = create_engine(DB_URL)

SIMILARITY_THRESHOLD = 0.92   # pairs above this are considered duplicates
OLLAMA_MODEL        = "nomic-embed-text"
PREVIEW_CHARS       = 80      # characters to show in preview


def get_embedding(text_input: str) -> np.ndarray:
    """Generate embedding for a single text using local Ollama."""
    # Truncate to avoid token limits — first 500 chars is enough for dedup
    truncated = text_input[:500].strip()
    response = ollama.embeddings(model=OLLAMA_MODEL, prompt=truncated)
    return np.array(response["embedding"], dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def run(dry_run: bool = False, batch_size: int = 200):
    print(f"\n{'DRY RUN — ' if dry_run else ''}Semantic Deduplication")
    print(f"Model: {OLLAMA_MODEL} | Threshold: {SIMILARITY_THRESHOLD}")
    print("=" * 60)

    # Verify Ollama is running and model is available
    print("\nChecking Ollama connection...")
    try:
        test_emb = get_embedding("test connection")
        print(f"Ollama OK — embedding size: {len(test_emb)}")
    except Exception as e:
        print(f"ERROR: Cannot connect to Ollama. Is it running?")
        print(f"Start it with: ollama serve")
        print(f"Detail: {e}")
        return

    # Fetch all rows with raw_text
    print("\nFetching listings from database...")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, raw_text
            FROM processed_listings
            WHERE raw_text IS NOT NULL
            AND LENGTH(TRIM(raw_text)) > 20
            ORDER BY id
        """)).fetchall()

    total = len(rows)
    print(f"Loaded {total} rows to process")

    # Generate embeddings in batches
    print(f"\nGenerating embeddings (batch size: {batch_size})...")
    print("This will take a few minutes...\n")

    embeddings = {}
    errors = 0

    for i, row in enumerate(rows):
        try:
            emb = get_embedding(row.raw_text)
            embeddings[row.id] = emb
        except Exception as e:
            errors += 1
            continue

        # Progress update every 50 rows
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total} embeddings generated | errors: {errors}")

        # Small delay to avoid overwhelming Ollama
        if (i + 1) % batch_size == 0:
            time.sleep(0.5)

    print(f"\nEmbeddings generated: {len(embeddings)} | Errors: {errors}")

    # Find duplicate pairs
    print("\nFinding duplicate pairs...")
    ids = list(embeddings.keys())
    duplicates_to_delete = set()
    duplicate_pairs = []

    for i in range(len(ids)):
        if ids[i] in duplicates_to_delete:
            continue
        for j in range(i + 1, len(ids)):
            if ids[j] in duplicates_to_delete:
                continue
            sim = cosine_similarity(embeddings[ids[i]], embeddings[ids[j]])
            if sim >= SIMILARITY_THRESHOLD:
                # Keep lower id (ids[i]), mark ids[j] for deletion
                duplicates_to_delete.add(ids[j])
                duplicate_pairs.append((ids[i], ids[j], round(sim, 4)))

    print(f"Duplicate pairs found: {len(duplicate_pairs)}")
    print(f"Rows to delete:        {len(duplicates_to_delete)}")
    print(f"Rows to keep:          {total - len(duplicates_to_delete)}")

    # Show sample of what will be deleted
    if duplicate_pairs:
        print(f"\nSample duplicate pairs (showing first 5):")
        print("-" * 60)

        row_lookup = {row.id: row.raw_text for row in rows}

        for keep_id, del_id, sim in duplicate_pairs[:5]:
            keep_text = row_lookup.get(keep_id, "")[:PREVIEW_CHARS]
            del_text  = row_lookup.get(del_id,  "")[:PREVIEW_CHARS]
            print(f"  KEEP  id={keep_id}: {keep_text!r}")
            print(f"  DELETE id={del_id} (sim={sim}): {del_text!r}")
            print()

    if dry_run:
        print("DRY RUN — no changes written.")
        return

    if not duplicates_to_delete:
        print("No duplicates found. Nothing to delete.")
        return

    # Delete duplicates in batches of 100
    print(f"\nDeleting {len(duplicates_to_delete)} duplicate rows...")
    delete_list = list(duplicates_to_delete)
    deleted = 0

    for i in range(0, len(delete_list), 100):
        batch = delete_list[i:i+100]
        placeholders = ", ".join(f"'{id_}'" for id_ in batch)
        with engine.begin() as conn:
            result = conn.execute(text(
                f"DELETE FROM processed_listings WHERE id IN ({placeholders})"
            ))
            deleted += result.rowcount

    print(f"Deleted: {deleted} rows")

    # Final count
    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT COUNT(*) FROM processed_listings"
        )).scalar()
    print(f"Rows remaining: {remaining}")

    # Refresh materialized view since data changed
    print("\nRefreshing market price model...")
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW market_price_model"))
    print("Market price model refreshed.")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without making changes")
    parser.add_argument("--batch", type=int, default=200,
                        help="Embedding batch size (default: 200)")
    args = parser.parse_args()

    run(dry_run=args.dry_run, batch_size=args.batch)
