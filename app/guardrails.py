import re
from typing import Dict, List


def validate_json_schema(obj: Dict) -> None:
    required = {"clean_text": str, "flags": list, "changes": list}
    for key, typ in required.items():
        if key not in obj or not isinstance(obj[key], typ):
            raise ValueError(f"Invalid schema: {key}")


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
