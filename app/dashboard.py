from typing import Dict, List

from fastapi import APIRouter

from .db import get_queue_stats, get_length_stats
from .learner import Learner

router = APIRouter(prefix="/stats")


@router.get("/summary")
def get_summary() -> Dict:
    """Return high-level statistics of the system."""
    queue_stats = get_queue_stats()
    total_reviewed = sum(queue_stats.values())
    length_stats = get_length_stats()
    return {
        "queue_stats": queue_stats,
        "total_reviewed": total_reviewed,
        "length_stats": length_stats,
    }


@router.get("/rules")
def get_rules() -> List[Dict]:
    """Return the currently active harmonization rules."""
    learner = Learner()
    return learner.get_rules()
