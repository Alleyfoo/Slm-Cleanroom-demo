import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.checkpointing import Checkpointer


def test_checkpoint_skip_and_append(tmp_path):
    out = tmp_path / "out.csv"
    err = tmp_path / "out.errors.csv"
    cp = Checkpointer(out, err, id_field="id", fieldnames=["id", "text"])

    cp.append_row({"id": "1", "text": "hello"})
    assert cp.is_processed("1")

    cp.append_error("2", "boom", "bad")
    assert err.exists()

    # Re-load to ensure state persists
    cp2 = Checkpointer(out, err, id_field="id", fieldnames=["id", "text"])
    assert cp2.is_processed("1")
    assert not cp2.is_processed("3")
