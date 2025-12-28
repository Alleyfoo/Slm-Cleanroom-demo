from typing import Any, Dict, Optional

from .db import upsert_review, get_review, get_pending_reviews


def enqueue(item_id: str, payload: Dict[str, Any]) -> None:
    payload["id"] = item_id
    payload["status"] = "pending"
    upsert_review(item_id, payload)


def update(item_id: str, approved: bool, correction: Optional[str] = None) -> Dict[str, Any]:
    existing = get_review(item_id) or {"id": item_id}
    existing["status"] = "approved" if approved else "rejected"
    if correction:
        existing["correction"] = correction
    upsert_review(item_id, existing)
    return existing


__all__ = ["enqueue", "update", "get_review", "get_pending_reviews"]
