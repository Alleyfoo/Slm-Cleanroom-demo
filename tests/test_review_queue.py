import os
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db


def test_db_upsert_and_retrieve(tmp_path):
    test_db = tmp_path / "cleanroom.db"
    os.environ["DB_PATH"] = str(test_db)

    db.init_db()

    payload = {
        "text": "Original text",
        "clean_text": "Clean text",
        "flags": [{"type": "test"}],
        "changes": [],
    }

    db.upsert_review("id-123", payload)

    result = db.get_review("id-123")
    assert result is not None
    assert result["id"] == "id-123"
    assert result["status"] == "pending"

    pending = db.get_pending_reviews()
    assert any(r["id"] == "id-123" for r in pending)
