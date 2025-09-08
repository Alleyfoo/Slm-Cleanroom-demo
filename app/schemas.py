from typing import List, Optional, Any
from pydantic import BaseModel


class CleanRequest(BaseModel):
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
    flags: List[str]
    changes: List[Any]
