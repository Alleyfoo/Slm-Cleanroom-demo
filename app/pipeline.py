from typing import List, Dict, Optional
import difflib
import re

from .lang_utils import mask_terms, lang_spans
from .slm_llamacpp import slm_cleanup as _slm_cleanup

from .guardrails import (
    validate_json_schema,
    forbid_changes_in_terms,
    post_validate,
    extract_json,
)

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

NUMERIC_RE = re.compile(
    r"""
    [-+]?
    (?:
        \d{1,3}(?:\.\d{3})+(?:,\d+)? |  # thousand separators with optional decimal comma
        \d+(?:[.,]\d+)?                   # plain number with optional decimal part
    )
    (?:\s*[\u2013-]\s*[-+]?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?))?  # optional range
    %?                                      # optional percentage
    """,
    re.VERBOSE,
)


def _extract_numbers(text: str) -> List[str]:
    """Return all numeric-like substrings from text."""
    return NUMERIC_RE.findall(text)

def slm_cleanup(text: str, translate_embedded: bool, **kwargs) -> Dict:
    """Adapter around the low level ``_slm_cleanup`` function.

    The wrapper forwards any additional keyword arguments to the underlying
    implementation and ensures that a JSON object with the expected schema is
    always returned.  If the model fails to produce valid JSON, the input text
    is split into sentence-like parts and processed piece by piece.
    """

    def _call(t: str) -> Dict:
        raw = _slm_cleanup(t, translate_embedded, **kwargs)


    llama = _load_llama()
    gen = {"llama": llama, "temp": TEMP, "max_tokens": MAX_TOKENS}

    def _call(t: str) -> Dict:
        try:
            raw = _slm_cleanup(t, translate_embedded, **gen)
        except TypeError:
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
            try:
                res = _call(part)
            except Exception:
                # If even individual parts cannot be parsed, fall back to
                # returning the original input verbatim.
                return {"clean_text": text, "flags": [], "changes": []}
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


def normalize_flags_and_changes(result: Dict, masked: str) -> Dict:
    flags_raw = result.get("flags", [])
    if not isinstance(flags_raw, list):
        flags_raw = []
    normalized_flags: List[Dict] = []
    numeric_change = False
    for f in flags_raw:
        if isinstance(f, dict):
            if f.get("type") == "numeric_change":
                numeric_change = True
            normalized_flags.append(f)
        elif isinstance(f, str):
            if f == "numeric_change":
                numeric_change = True
            normalized_flags.append({"type": f})
        # silently drop other types

    if numeric_change:
        result["clean_text"] = masked
        normalized_flags = [f for f in normalized_flags if f.get("type") != "numeric_change"]
        normalized_flags.append({"type": "numeric_change"})
        result["changes"] = []

    result["flags"] = normalized_flags

    changes_raw = result.get("changes", [])
    if not isinstance(changes_raw, list):
        changes_raw = []
    result["changes"] = [c for c in changes_raw if isinstance(c, dict)]

    return result

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


    result = slm_cleanup(masked, translate_embedded)

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
    result = slm_cleanup(masked, translate_embedded)

    try:
        result = slm_cleanup(
            masked,
            translate_embedded,
            llama=llama,
            temp=TEMP,
            max_tokens=MAX_TOKENS,
        )
    except TypeError:
        # Allow monkeypatched or legacy implementations that don't accept kwargs
        result = slm_cleanup(masked, translate_embedded)
    validate_json_schema(result)

    forbid_changes_in_terms(masked, result['clean_text'])
    flags.extend(result.get('flags', []))
    # Normalise flags to dictionaries and ignore any numeric change markers
    # coming from the model itself; numeric diffs are detected separately.
    normalised: List[Dict] = []
    for f in flags:
        if isinstance(f, str):
            if f == 'numeric_change':
                continue
            normalised.append({'type': f})
        elif isinstance(f, dict):
            if f.get('type') == 'numeric_change':
                continue
            normalised.append(f)
    flags = normalised
    if _extract_numbers(masked) != _extract_numbers(result.get('clean_text', '')):
        flags.append({'type': 'numeric_change'})

    changes = result.get('changes', [])
    changes.extend(spell_changes)
    if result['clean_text'] != masked:
        diff = list(difflib.unified_diff(masked.splitlines(), result['clean_text'].splitlines(), lineterm=''))
        changes.append({'source': 'diff', 'type': 'rewrite', 'diff': '\n'.join(diff)})

    final = {'clean_text': result['clean_text'], 'flags': flags, 'changes': changes, 'mixed_languages': mixed_languages}
    return normalize_flags_and_changes(final, masked)

def run_pipeline_like_this():
    example = "Tämä takki on super warm for winter commutes kaupungilla."
    return run_pipeline(example)
