import json
from pathlib import Path
from typing import Any, Dict, Optional

REVIEW_FILE = Path("data/review_queue.jsonl")


def _ensure_file() -> None:
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_FILE.touch(exist_ok=True)


def enqueue(item_id: str, payload: Dict[str, Any]) -> None:
    _ensure_file()
    with REVIEW_FILE.open("a", encoding="utf-8") as f:
        record = {"id": item_id, "status": "pending", **payload}
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def update(item_id: str, approved: bool, correction: Optional[str] = None) -> Dict[str, Any]:
    _ensure_file()
    updated = []
    found = None
    with REVIEW_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("id") == item_id and found is None:
                obj["status"] = "approved" if approved else "rejected"
                if correction:
                    obj["correction"] = correction
                found = obj
            updated.append(obj)

    if found is None:
        # Create a new entry if it wasn't in the queue yet
        found = {"id": item_id, "status": "approved" if approved else "rejected"}
        if correction:
            found["correction"] = correction
        updated.append(found)

    with REVIEW_FILE.open("w", encoding="utf-8") as f:
        for obj in updated:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return found
