import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .db import get_review_history

RULES_PATH = Path("data/rules.json")


class RuleMiner:
    def __init__(self):
        pass

    def extract_patterns(self, original: str, corrected: str) -> Optional[Dict]:
        if not original or not corrected or original == corrected:
            return None

        # Heuristic: casing normalization
        if original.lower() == corrected.lower() and original != corrected:
            return {"type": "casing", "pattern": original, "fix": corrected, "confidence": 1.0}

        # Heuristic: spacing adjustments (remove/add spaces)
        if original.replace(" ", "") == corrected.replace(" ", "") and original != corrected:
            return {"type": "spacing", "pattern": original, "fix": corrected, "confidence": 0.5}

        # Heuristic: hyphen standardization (e.g., SKU 123 -> SKU-123)
        if re.sub(r"[-\s]", "", original) == re.sub(r"[-\s]", "", corrected) and original != corrected:
            return {"type": "hyphenation", "pattern": original, "fix": corrected, "confidence": 0.5}

        return None

    def mine_from_history(self, history: List[Dict]) -> List[Dict]:
        potential_rules = []
        for item in history:
            orig = item.get("text", "")
            corr = item.get("correction", "")
            if not corr or not orig:
                continue
            rule = self.extract_patterns(orig, corr)
            if rule:
                rule["source_id"] = item.get("id")
                potential_rules.append(rule)

        rule_counts = Counter((r["pattern"], r["fix"], r["type"]) for r in potential_rules)
        refined_rules: List[Dict] = []
        for r in potential_rules:
            key = (r["pattern"], r["fix"], r["type"])
            count = rule_counts[key]
            if count >= 3:
                r["confidence"] = min(1.0, count / 10.0)
                refined_rules.append(r)
        return refined_rules


class Learner:
    def __init__(self):
        self.rules: List[Dict] = []
        self.load_rules()

    def load_rules(self):
        if RULES_PATH.exists():
            try:
                with RULES_PATH.open("r", encoding="utf-8") as f:
                    self.rules = json.load(f)
            except Exception:
                self.rules = []
        else:
            self.rules = []

    def save_rules(self):
        RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RULES_PATH.open("w", encoding="utf-8") as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)

    def get_rules(self) -> List[Dict]:
        return self.rules

    def learn(self, limit: int = 1000):
        history = get_review_history(limit=limit)
        miner = RuleMiner()
        new_rules = miner.mine_from_history(history)
        if not new_rules:
            return []

        existing = {(r.get("pattern"), r.get("fix"), r.get("type")) for r in self.rules}
        merged = list(self.rules)
        for r in new_rules:
            key = (r.get("pattern"), r.get("fix"), r.get("type"))
            if key not in existing:
                merged.append(r)
        self.rules = merged
        self.save_rules()
        return new_rules

    def harmonize(self, text: str) -> str:
        if not self.rules:
            return text
        sorted_rules = sorted(self.rules, key=lambda x: x.get("confidence", 0), reverse=True)
        result_text = text
        for rule in sorted_rules:
            pattern = rule.get("pattern")
            fix = rule.get("fix")
            rtype = rule.get("type")
            if not pattern or not fix:
                continue
            flags = re.IGNORECASE if rtype in {"casing", "hyphenation"} else 0
            try:
                result_text = re.sub(re.escape(pattern), fix, result_text, flags=flags)
            except re.error:
                continue
        return result_text
