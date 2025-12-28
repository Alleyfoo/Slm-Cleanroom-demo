import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(os.environ.get("DB_PATH", "data/cleanroom.db"))


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS review_queue (
            id TEXT PRIMARY KEY,
            status TEXT,
            text TEXT,
            clean_text TEXT,
            flags TEXT,
            changes TEXT,
            correction TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_review(item_id: str, payload: Dict[str, Any]) -> None:
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO review_queue
        (id, status, text, clean_text, flags, changes, correction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            payload.get("status", "pending"),
            payload.get("text"),
            payload.get("clean_text"),
            json.dumps(payload.get("flags", [])),
            json.dumps(payload.get("changes", [])),
            payload.get("correction"),
        ),
    )
    conn.commit()
    conn.close()


def get_review(item_id: str) -> Optional[Dict]:
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM review_queue WHERE id = ?", (item_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def get_pending_reviews() -> List[Dict]:
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM review_queue WHERE status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_review_history(limit: int = 1000) -> List[Dict]:
    """Return approved/rejected reviews that include a correction, newest first."""
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM review_queue
        WHERE status IN ('approved','rejected') AND correction IS NOT NULL
        ORDER BY rowid DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_queue_stats() -> Dict[str, int]:
    """Return counts per status in the review queue."""
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) as count FROM review_queue GROUP BY status")
    rows = c.fetchall()
    conn.close()
    return {r["status"]: r["count"] for r in rows if r["status"]}
