from typing import List, Dict, Optional
import difflib

from .lang_utils import mask_terms, lang_spans
from .slm_llamacpp import slm_cleanup
from .guardrails import validate_json_schema, forbid_changes_in_terms, post_validate


def run_pipeline(text: str, terms: Optional[List[str]] = None, translate_embedded: bool = False) -> Dict:
    original = text
    masked = mask_terms(text, terms or [])

    spans = lang_spans(masked)
    langs = {s['lang'] for s in spans}
    flags: List[str] = []
    if 'en' in langs and 'fi' in langs:
        flags.append('embedded_en')

    result = slm_cleanup(masked, translate_embedded)
    validate_json_schema(result)
    forbid_changes_in_terms(masked, result['clean_text'])
    flags.extend(result.get('flags', []))
    flags.extend(post_validate(masked, result))

    changes = result.get('changes', [])
    if result['clean_text'] != masked:
        diff = list(difflib.unified_diff(masked.splitlines(), result['clean_text'].splitlines(), lineterm=''))
        changes.append({'source': 'diff', 'type': 'rewrite', 'diff': '\n'.join(diff)})

    return {'clean_text': result['clean_text'], 'flags': flags, 'changes': changes}

def run_pipeline_like_this():
    example = "Tämä takki on super warm for winter commutes kaupungilla."
    return run_pipeline(example)
