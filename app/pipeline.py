from typing import List, Dict, Optional
import difflib

from .lang_utils import mask_terms, lang_spans
from .slm_llamacpp import slm_cleanup
from .guardrails import validate_json_schema, forbid_changes_in_terms, post_validate

try:
    from spellchecker import SpellChecker
    SP_EN = SpellChecker(language="en")
except Exception:
    SP_EN = None

def en_misspellings(text: str):
    if SP_EN is None:
        return []
    out = []
    import re
    for m in re.finditer(r"[A-Za-z][A-Za-z\-']+", text):
        w = m.group(0)
        if w.lower() in SP_EN.unknown([w]):
            cand = list(SP_EN.candidates(w))
            out.append({"start": m.start(), "end": m.end(), "word": w, "suggest": cand[:3]})
    return out

def run_pipeline(text: str, translate_embedded: bool = False, protected_terms: Optional[List[str]] = None) -> Dict:
    masked = mask_terms(text, protected_terms or [])

    spans = lang_spans(masked)
    langs = {s['lang'] for s in spans}
    flags: List[Dict] = []
    mixed_languages = len(langs) > 1
    if 'en' in langs and 'fi' in langs:
        flags.append({'type': 'embedded_en'})

    spell_changes: List[Dict] = []
    for s in spans:
        if s["lang"].startswith("en"):
            for m in en_misspellings(s["text"]):
                spell_changes.append({
                    "span": [s["start"] + m["start"], s["start"] + m["end"]],
                    "type": "spelling",
                    "source": "spell",
                    "before": m["word"],
                    "after": (m["suggest"][0] if m["suggest"] else m["word"])
                })

    result = slm_cleanup(masked, translate_embedded)
    validate_json_schema(result)
    forbid_changes_in_terms(masked, result['clean_text'])
    flags.extend(result.get('flags', []))
    flags.extend(post_validate(masked, result))

    changes = result.get('changes', [])
    changes.extend(spell_changes)
    if result['clean_text'] != masked:
        diff = list(difflib.unified_diff(masked.splitlines(), result['clean_text'].splitlines(), lineterm=''))
        changes.append({'source': 'diff', 'type': 'rewrite', 'diff': '\n'.join(diff)})

    return {'clean_text': result['clean_text'], 'flags': flags, 'changes': changes, 'mixed_languages': mixed_languages}

def run_pipeline_like_this():
    example = "Tämä takki on super warm for winter commutes kaupungilla."
    return run_pipeline(example)
