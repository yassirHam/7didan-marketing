"""Writer for reporting.conversation_events (PostgreSQL).

Mirrors database/reporting.sql from the marketing repo. The schema and
table are created idempotently on first use so the backend works even
before scripts/setup.py has run. Logging failures must never break the
API, so callers should catch exceptions (or use record_safe).
"""

import logging
import os
import threading
from typing import Optional

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE IF NOT EXISTS reporting.conversation_events (
    id              bigserial PRIMARY KEY,
    conversation_id text NOT NULL,
    event           text NOT NULL CHECK (event IN (
                        'started', 'answered', 'abstained', 'qualification_started',
                        'qualification_completed', 'abandoned')),
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    is_synthetic    boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS conversation_events_conv_idx
    ON reporting.conversation_events (conversation_id);
"""

_INSERT_SQL = """
INSERT INTO reporting.conversation_events (conversation_id, event)
VALUES (%s, %s)
"""

_SELECT_SQL = """
SELECT 1 FROM reporting.conversation_events
WHERE conversation_id = %s
LIMIT 1
"""


class EventStore:
    """Lazy, thread-safe writer for conversation funnel events."""

    def __init__(self):
        self._lock = threading.Lock()
        self._conn: Optional[psycopg.Connection] = None
        self._schema_ready = False

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                dbname=os.getenv("POSTGRES_DB"),
                autocommit=True,
            )
            self._schema_ready = False
        return self._conn

    def _ensure_schema(self, cur) -> None:
        if not self._schema_ready:
            cur.execute(_SCHEMA_SQL)
            self._schema_ready = True

    def record(self, conversation_id: str, event: str) -> None:
        """Insert one funnel event."""
        with self._lock:
            cur = self._connection().cursor()
            self._ensure_schema(cur)
            cur.execute(_INSERT_SQL, (conversation_id, event))

    def has_events(self, conversation_id: str) -> bool:
        """True if any event was already recorded for this conversation."""
        with self._lock:
            cur = self._connection().cursor()
            self._ensure_schema(cur)
            cur.execute(_SELECT_SQL, (conversation_id,))
            return cur.fetchone() is not None

    def close(self):
        with self._lock:
            if self._conn and not self._conn.closed:
                self._conn.close()
            self._conn = None


_store: Optional[EventStore] = None
_store_lock = threading.Lock()


def get_event_store() -> EventStore:
    """Get or create the global event store."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = EventStore()
    return _store


def record_safe(conversation_id: str, event: str) -> None:
    """Record an event, logging but never raising on failure."""
    try:
        get_event_store().record(conversation_id, event)
    except Exception:
        logger.exception("Failed to record conversation event %s for %s", event, conversation_id)


def conversation_started(conversation_id: str) -> bool:
    """True if this conversation has no events yet (first message)."""
    try:
        return not get_event_store().has_events(conversation_id)
    except Exception:
        logger.exception("Failed to check conversation events for %s", conversation_id)
        return False
