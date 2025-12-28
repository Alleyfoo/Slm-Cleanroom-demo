import re
from typing import Dict, List, Tuple


ENTITY_PATTERNS: List[Tuple[str, re.Pattern]] = [
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


def merge_protected_terms(terms: List[str], locks: List[Dict]) -> List[str]:
    """Combine user-provided protected terms with extracted entity values."""
    merged = list(terms)
    for lock in locks:
        if lock["value"] not in merged:
            merged.append(lock["value"])
    return merged


def enforce_entity_lock(original: str, clean_text: str, locks: List[Dict]) -> Tuple[str, List[Dict]]:
    """Ensure locked entities survive; patch surgically or revert and flag."""
    flags: List[Dict] = []
    final_text = clean_text
    for lock in locks:
        if lock["value"] in final_text:
            continue
        # Attempt surgical patch at the original span position.
        try:
            start, end = lock.get("span", [0, 0])
            patched = final_text
            if start <= len(patched):
                patched = patched[:start] + lock["value"] + patched[start:]
                final_text = patched
                flags.append(
                    {
                        "type": "locked_entity_changed",
                        "entity_type": lock["type"],
                        "value": lock["value"],
                        "patched": True,
                    }
                )
                continue
        except Exception:
            pass
        # Fallback: revert to original to avoid data corruption.
        final_text = original
        flags.append(
            {
                "type": "locked_entity_changed",
                "entity_type": lock["type"],
                "value": lock["value"],
                "patched": False,
            }
        )
        break
    return final_text, flags
