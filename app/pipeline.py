from typing import List, Dict, Optional
import difflib
import json
import re

from .lang_utils import mask_terms, lang_spans
from .slm_llamacpp import slm_cleanup
from .guardrails import validate_json_schema, forbid_changes_in_terms, post_validate
from .config import MODEL_PATH, N_THREADS, CTX, TEMP, MAX_TOKENS

try:  # optional dependency
    from llama_cpp import Llama  # type: ignore
except Exception:  # pragma: no cover - llama_cpp is optional
    Llama = None  # type: ignore

_LLAMA = None


def _load_llama():
    """Lazily load llama-cpp model using environment configuration."""
    global _LLAMA
    if _LLAMA is None and Llama is not None and MODEL_PATH:
        try:  # pragma: no cover - exercised only when llama_cpp is installed
            _LLAMA = Llama(
                model_path=MODEL_PATH,
                n_threads=N_THREADS,
                n_ctx=CTX,
            )
        except Exception:
            _LLAMA = None
    return _LLAMA


try:
    from spellchecker import SpellChecker
    SP_EN = SpellChecker(language="en")
except Exception:
    SP_EN = None

# Optional Voikko (FI)
_VOIKKO = None
try:
    import libvoikko
    _VOIKKO = libvoikko.Voikko("fi")
except Exception:
    _VOIKKO = None

def en_misspellings(text: str):
    if SP_EN is None:
        return []
    out = []
    for m in re.finditer(r"[A-Za-z][A-Za-z\-']+", text):
        w = m.group(0)
        if w.lower() in SP_EN.unknown([w]):
            cand = list(SP_EN.candidates(w))
            out.append({"start": m.start(), "end": m.end(), "word": w, "suggest": cand[:3]})
    return out

def fi_misspellings_voikko(text: str):
    if _VOIKKO is None:
        return []
    out = []
    for m in re.finditer(r"[A-Za-zÅÄÖåäö][A-Za-zÅÄÖåäö\-']+", text):
        w = m.group(0)
        if not _VOIKKO.spell(w):
            sugg = _VOIKKO.suggest(w) or []
            out.append({"start": m.start(), "end": m.end(), "word": w, "suggest": sugg[:3]})
    return out

def slm_cleanup(text: str, translate_embedded: bool) -> Dict:
    def _call(t: str) -> Dict:
        raw = _slm_cleanup(t, translate_embedded)
        if isinstance(raw, dict):
            raw = json.dumps(raw)
        return extract_json(raw)

    try:
        return _call(text)
    except Exception:
        parts = [m.group(0) for m in re.finditer(r"[^.!?]+[.!?]?\s*", text)]
        clean_parts: List[str] = []
        flags: List = []
        changes: List = []
        offset = 0
        for part in parts:
            res = _call(part)
            ct = res.get("clean_text", "")
            clean_parts.append(ct)
            for f in res.get("flags", []):
                item = f
                if isinstance(item, dict) and "span" in item:
                    s, e = item["span"]
                    item = {**item, "span": [s + offset, e + offset]}
                flags.append(item)
            for c in res.get("changes", []):
                item = c
                if isinstance(item, dict) and "span" in item:
                    s, e = item["span"]
                    item = {**item, "span": [s + offset, e + offset]}
                changes.append(item)
            offset += len(ct)
        return {"clean_text": "".join(clean_parts), "flags": flags, "changes": changes}

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
        if s["lang"].startswith("fi"):
            for m in fi_misspellings_voikko(s["text"]):
                spell_changes.append({
                    "span": [s["start"] + m["start"], s["start"] + m["end"]],
                    "type": "spelling",
                    "source": "voikko",
                    "before": m["word"],
                    "after": (m["suggest"][0] if m["suggest"] else m["word"])
                })

    llama = _load_llama()
    # The stubbed slm_cleanup ignores the llama and generation parameters,
    # but the real implementation will use them.
    result = slm_cleanup(
        masked,
        translate_embedded,
        llama=llama,
        temp=TEMP,
        max_tokens=MAX_TOKENS,
    )
    validate_json_schema(result)
    result = slm_cleanup(masked, translate_embedded)
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
