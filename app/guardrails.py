import json
import re
from typing import Dict, List

SCHEMA_KEYS = {"clean_text", "flags", "changes"}


def validate_json_schema(obj: Dict) -> None:
    """Validate that *obj* contains the expected top-level keys.

    The cleanup pipeline expects the language model to return a JSON object
    with ``clean_text``, ``flags`` and ``changes`` fields.  Some tests stub
    out the model and feed arbitrary strings through the adapter, so this
    lightweight check ensures we fail fast if the structure is unexpected.
    """
    if not isinstance(obj, dict):
        raise ValueError("Result must be a dict")
    missing = SCHEMA_KEYS.difference(obj.keys())
    if missing:
        raise ValueError("JSON schema mismatch")


def extract_json(text: str) -> Dict:
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1 or i > j:
        raise ValueError("No JSON object found")
    obj = json.loads(text[i : j + 1])
    if not isinstance(obj, dict) or not SCHEMA_KEYS.issubset(obj.keys()):
        raise ValueError("JSON schema mismatch")
    for k in ("flags", "changes"):
        if not isinstance(obj.get(k, []), list):
            raise ValueError(f"{k} must be a list")
    return obj


def forbid_changes_in_terms(original: str, clean_text: str) -> None:
    pattern = re.compile(r"<TERM>(.*?)</TERM>")
    if pattern.findall(original) != pattern.findall(clean_text):
        raise ValueError("TERM content changed")


def post_validate(original: str, result: Dict) -> List[str]:
    flags: List[str] = []
    orig_nums = re.findall(r"\d+", original)
    new_nums = re.findall(r"\d+", result.get("clean_text", ""))
    if orig_nums != new_nums:
        flags.append("numeric_change")
    return flags
