import re
from typing import Dict, List, Tuple


ENTITY_PATTERNS = [
    ("price", re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:€|eur|e)\b", flags=re.IGNORECASE)),
    ("sku", re.compile(r"\b[A-Z0-9]{2,}-[A-Z0-9\-]{2,}\b", flags=re.IGNORECASE)),
    ("size", re.compile(r"\b(?:size\s+)?(?:XS|S|M|L|XL|XXL)\b", flags=re.IGNORECASE)),
    ("dimensions", re.compile(r"\b\d+(?:[x×]\d+){1,2}\s?(?:mm|cm)?\b", flags=re.IGNORECASE)),
]


def extract_entities(text: str) -> List[Dict]:
    """Return list of entity locks with spans and values."""
    locks: List[Dict] = []
    for ent_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            locks.append(
                {
                    "type": ent_type,
                    "value": match.group(0),
                    "span": [match.start(), match.end()],
                }
            )
    return locks


def enforce_entity_lock(original: str, clean_text: str, locks: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    Ensure locked entities survive; if any are missing, revert to the original text
    and flag the occurrence. Safer than patching with stale indices.
    """
    flags: List[Dict] = []
    final_text = clean_text
    for lock in locks:
        if lock["value"] in final_text:
            continue
        # Fail-safe: revert entire text to avoid corruption.
        final_text = original
        flags.append(
            {
                "type": "locked_entity_changed",
                "entity_type": lock["type"],
                "value": lock["value"],
                "action": "reverted_entire_text",
            }
        )
        break
    return final_text, flags
