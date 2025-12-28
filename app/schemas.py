from typing import Any, List, Optional
from pydantic import BaseModel


class CleanRequest(BaseModel):
    id: Optional[str] = None
    text: str
    terms: Optional[List[str]] = None
    translate_embedded: bool = False


class Change(BaseModel):
    source: str
    type: str
    original: str
    corrected: str


class CleanResponse(BaseModel):
    clean_text: str
    flags: List[Any]
    changes: List[Any]
    risk_score: float
    review_status: str


class ReviewRequest(BaseModel):
    approved: bool
    correction: Optional[str] = None
