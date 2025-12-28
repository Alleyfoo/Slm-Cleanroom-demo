import json
import re
from typing import Dict, List

SCHEMA_KEYS = {"clean_text", "flags", "changes"}
JSON_START = "<JSON>"
JSON_END = "</JSON>"


def _coerce_payload(raw: str) -> Dict:
    """Load JSON and enforce minimal schema defaults."""
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("JSON schema mismatch")
    obj.setdefault("clean_text", "")
    obj.setdefault("flags", [])
    obj.setdefault("changes", [])
    for key in ("flags", "changes"):
        if not isinstance(obj.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    obj["clean_text"] = str(obj.get("clean_text", ""))
    return obj


def extract_json(text: str, start: str = JSON_START, end: str = JSON_END) -> Dict:
    """Extract a JSON object, preferring sentinel markers when present."""
    if start in text and end in text:
        i = text.find(start)
        j = text.rfind(end)
        if i != -1 and j != -1 and i < j:
            raw = text[i + len(start) : j].strip()
            obj = _coerce_payload(raw)
            validate_json_schema(obj)
            return obj

    def _extract_brace_json(src: str) -> str:
        start_idx = src.find("{")
        if start_idx == -1:
            raise ValueError("No JSON object found")
        depth = 0
        in_str = False
        esc = False
        for idx in range(start_idx, len(src)):
            ch = src[idx]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"' and not esc:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return src[start_idx : idx + 1]
        raise ValueError("Unbalanced braces in JSON payload")

    raw_obj = _extract_brace_json(text)
    obj = _coerce_payload(raw_obj)
    validate_json_schema(obj)
    return obj


def validate_json_schema(obj: Dict) -> None:
    """Validate that *obj* matches the minimal result schema."""
    if not isinstance(obj, dict) or not SCHEMA_KEYS.issubset(obj.keys()):
        raise ValueError("JSON schema mismatch")
    for key in ("flags", "changes"):
        if not isinstance(obj.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    obj.setdefault("clean_text", "")


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
