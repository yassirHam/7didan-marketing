"""Backfill `url` (and title/category/...) into existing vector-store rows.

The crawler already wrote a sidecar .json next to every .md file with
`source_url`, but rows indexed before the pipeline fix only stored
{source, section_h1..h3}. This script updates `langchain_metadata` in
PostgreSQL in place, keyed by the `source` filename, so the URL can be
returned by the API without re-crawling or re-embedding.

Usage:
    python knowledge_base/scripts/backfill_metadata.py
"""

import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

RAW_DATA_PATH = Path(os.getenv("RAW_DATA_PATH", "knowledge_base/data/raw/markdown"))
if not RAW_DATA_PATH.is_absolute():
    RAW_DATA_PATH = PROJECT_ROOT / RAW_DATA_PATH
TABLE = os.getenv("POSTGRES_TABLE", "7didan_store")

METADATA_FIELDS = ("source_url", "title", "category", "document_type", "language")


def main() -> int:

    if not RAW_DATA_PATH.is_dir():
        print(f"Raw data folder not found: {RAW_DATA_PATH}")
        return 1

    sidecars = sorted(RAW_DATA_PATH.glob("*.json"))
    print(f"Found {len(sidecars)} sidecar metadata files")

    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

    updated = 0
    missing = 0

    with conn.cursor() as cur:

        for sidecar in sidecars:

            data = json.loads(sidecar.read_text(encoding="utf-8"))
            filename = data.get("source") or sidecar.with_suffix(".md").name

            # Map sidecar keys to the metadata keys used by the indexer.
            meta = {"url": data.get("source_url")}
            for field in METADATA_FIELDS[1:]:
                meta[field] = data.get(field)

            # Store every field, including url, as JSON in langchain_metadata.
            cur.execute(
                f'UPDATE "{TABLE}" '
                f"SET langchain_metadata = (langchain_metadata::jsonb || %s::jsonb)::json "
                f"WHERE langchain_metadata->>'source' = %s",
                (json.dumps(meta), filename),
            )

            if cur.rowcount:
                updated += cur.rowcount
            else:
                missing += 1
                print(f"[NO MATCH] {filename}")

    conn.commit()
    conn.close()

    print(f"Rows updated: {updated}")
    print(f"Sidecars with no matching rows: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
