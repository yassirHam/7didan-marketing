"""Export the vector DB + reporting schema to a plain-SQL dump in the repo.

The database runs in Docker (pgvector), but the data must live in the local
repo so it can be shared/restored later (e.g. by the marketing project):
`docker compose up` mounts postgres/7didan_backup.sql into
/docker-entrypoint-initdb.d/, which restores it into a fresh volume.

Usage (from the repo root, with .env loaded):
    python scripts/export_db.py            # writes postgres/7didan_backup.sql
"""

import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

OUT_FILE = PROJECT_ROOT / "postgres" / "7didan_backup.sql"
TABLE = os.getenv("POSTGRES_TABLE", "7didan_store")


def copy_escape(value) -> str:
    """Escape a value for PostgreSQL COPY text format."""
    if value is None:
        return r"\N"
    s = str(value)
    return (
        s.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def main() -> int:

    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with conn.cursor() as cur, open(OUT_FILE, "w", encoding="utf-8") as out:

        out.write("-- 7didan vector DB + reporting schema dump (plain SQL).\n")
        out.write("-- Restore with: psql -d <db> -f postgres/7didan_backup.sql\n")
        out.write("-- or automatically on first `docker compose up` (docker-entrypoint-initdb.d).\n\n")
        out.write("CREATE EXTENSION IF NOT EXISTS vector;\n\n")

        # ---- vector table DDL (recreated if missing) ----
        out.write(f'DROP TABLE IF EXISTS "{TABLE}";\n')
        out.write(
            f'CREATE TABLE "{TABLE}" (\n'
            f'    langchain_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n'
            f'    content text,\n'
            f'    embedding vector(1024),\n'
            f'    langchain_metadata json\n'
            f');\n\n'
        )

        # ---- reporting schema (funnel events written by the FastAPI backend) ----
        out.write("CREATE SCHEMA IF NOT EXISTS reporting;\n")
        out.write("DROP TABLE IF EXISTS reporting.conversation_events;\n")
        out.write(
            "CREATE TABLE reporting.conversation_events (\n"
            "    id bigserial PRIMARY KEY,\n"
            "    conversation_id text NOT NULL,\n"
            "    event text NOT NULL CHECK (event IN (\n"
            "        'started', 'answered', 'abstained', 'qualification_started',\n"
            "        'qualification_completed', 'abandoned')),\n"
            "    occurred_at timestamptz NOT NULL DEFAULT now(),\n"
            "    is_synthetic boolean NOT NULL DEFAULT true\n"
            ");\n"
            "CREATE INDEX conversation_events_conv_idx ON reporting.conversation_events (conversation_id);\n\n"
        )

        # ---- vector rows as COPY ----
        cur.execute(
            f'SELECT langchain_id, content, embedding, langchain_metadata FROM "{TABLE}"'
        )
        rows = cur.fetchall()
        out.write(f'COPY "{TABLE}" (langchain_id, content, embedding, langchain_metadata) FROM stdin;\n')
        for langchain_id, content, embedding, metadata in rows:
            # psycopg returns json columns as dicts; re-serialize to real JSON.
            if isinstance(metadata, (dict, list)):
                metadata = json.dumps(metadata, ensure_ascii=False)
            out.write(
                "\t".join(
                    copy_escape(v)
                    for v in (str(langchain_id), content, str(embedding), metadata)
                )
                + "\n"
            )
        out.write("\\.\n\n")

        # ---- reporting rows as COPY ----
        try:
            cur.execute(
                "SELECT conversation_id, event, occurred_at, is_synthetic "
                "FROM reporting.conversation_events"
            )
            events = cur.fetchall()
        except psycopg.errors.UndefinedTable:
            conn.rollback()
            events = []
        out.write(
            "COPY reporting.conversation_events (conversation_id, event, occurred_at, is_synthetic) FROM stdin;\n"
        )
        for conv_id, event, occurred_at, is_synthetic in events:
            out.write(
                "\t".join(copy_escape(v) for v in (conv_id, event, str(occurred_at), is_synthetic))
                + "\n"
            )
        out.write("\\.\n")

    conn.close()

    size = OUT_FILE.stat().st_size
    print(f"Wrote {OUT_FILE.relative_to(PROJECT_ROOT)} ({size / 1024:.0f} KB, {len(rows)} vector rows, {len(events)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
