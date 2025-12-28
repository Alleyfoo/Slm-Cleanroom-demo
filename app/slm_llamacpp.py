"""Wrapper utilities for llama-cpp based small language model."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from .guardrails import JSON_END, JSON_START, extract_json

try:  # optional dependency
    from llama_cpp import Llama  # type: ignore
except Exception:  # pragma: no cover - llama_cpp is optional
    Llama = None  # type: ignore

# Generation system prompt and JSON sentinels
SYSTEM = (
    "Olet kielipuhdistusagentti. Älä muuta merkitystä. "
    "Älä muuta <TERM>...</TERM>-sisältöä. "
    "Käsittele vain <USER_INPUT>...</USER_INPUT> -lohkon sisältö ja vastaa AINOASTAAN JSONILLA.\n"
    "Esimerkki 1:\n"
    "User: \"Tämä on <TERM>ABC-123</TERM>, joka on hyvä.\"\n"
    "Assistant: {\"clean_text\": \"Tämä on <TERM>ABC-123</TERM>, joka on hyvä.\", \"flags\": [], \"changes\": []}\n\n"
    "Esimerkki 2:\n"
    "User: \"Super warm takki\"\n"
    "Assistant: {\"clean_text\": \"Super warm takki\", \"flags\": [{\"type\": \"embedded_en\"}], \"changes\": []}\n"
)

GRAMMAR = r"""
root   ::= object
object ::= "{" space "\"clean_text\"" space ":" space string "," space "\"flags\"" space ":" space array "," space "\"changes\"" space ":" space array "}"
string ::= "\"" ( [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]) )* "\""
array  ::= "[" space ( value ("," space value)* )? "]"
value  ::= object | string | number | "true" | "false" | "null"
space  ::= [ \t\n]*
number ::= ("-"? ([0-9] | [1-9] [0-9]*)) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
"""


def _build_user(masked_text: str, translate_embedded: bool) -> str:
    """Return user prompt for the model."""
    return (
        f"""Kontekstikieli: FI. Sallitut kielet: FI ja EN.
Ohjeet:
- Korjaa kielioppi ja välimerkit.
- Jos FI-tekstissä on upotettu EN-segmentti, lisää flags: {{ "type":"embedded_en","start":i,"end":j }}.
- translate_embedded = {"true" if translate_embedded else "false"} → jos true, käännä EN-osiot suomeksi.
- Älä muuta <TERM>...</TERM> -osuuksia.
- Palauta VAIN JSON seuraavan skeeman mukaan, ilman mitään muuta tekstiä:
{JSON_START}{{"clean_text":"...","flags":[{{"type":"embedded_en","start":0,"end":0}}],"changes":[{{"span":[0,0],"type":"grammar|spelling|punctuation|translation","source":"slm|spell|voikko","before":"","after":""}}]}}{JSON_END}

KÄSITELTÄVÄ TEKSTI (käsittele vain tämä lohko):
<USER_INPUT>
{masked_text}
</USER_INPUT>
"""
    )


def slm_cleanup(masked_text: str, translate_embedded: bool, **kwargs: Any) -> Dict:
    """Clean up text using an optional ``llama`` instance.

    Parameters are accepted as ``**kwargs`` so that unused generation
    parameters (e.g. ``temperature`` or ``max_tokens``) do not raise errors.
    When ``llama`` is ``None`` the function acts as a deterministic stub
    returning the original ``masked_text``.
    """

    llama = kwargs.get("llama")
    temperature = kwargs.get("temperature", kwargs.get("temp", 0.0))
    max_tokens = kwargs.get("max_tokens", 512)

    def _call(t: str) -> Dict:
        """Generate and parse model output for ``t``."""

        if llama is None or not hasattr(llama, "create_chat_completion"):
            # Deterministic stub used in tests
            raw = (
                JSON_START
                + json.dumps({"clean_text": t, "flags": [], "changes": []}, ensure_ascii=False)
                + JSON_END
            )
        else:  # pragma: no cover - requires llama_cpp
            try:
                prompt = _build_user(t, translate_embedded)
                out = llama.create_chat_completion(
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    grammar=GRAMMAR,
                )
                raw = out["choices"][0]["message"]["content"]
            except Exception:
                raw = (
                    JSON_START
                    + json.dumps({"clean_text": t, "flags": [], "changes": []}, ensure_ascii=False)
                    + JSON_END
                )
        return extract_json(raw)

    try:
        return _call(masked_text)
    except Exception:
        # Fallback: process sentence by sentence
        parts = [m.group(0) for m in re.finditer(r"[^.!?]+[.!?]?\s*", masked_text)]
        clean_parts = []
        flags = []
        changes = []
        offset = 0
        for part in parts:
            res = _call(part)
            ct = res.get("clean_text", "")
            clean_parts.append(ct)

            for f in res.get("flags", []):
                if isinstance(f, dict):
                    if {"start", "end"}.issubset(f.keys()):
                        flags.append({**f, "start": f["start"] + offset, "end": f["end"] + offset})
                    elif "span" in f:
                        s, e = f["span"]
                        flags.append({**f, "span": [s + offset, e + offset]})
                    else:
                        flags.append(f)
                else:
                    flags.append(f)

            for c in res.get("changes", []):
                if isinstance(c, dict) and "span" in c:
                    s, e = c["span"]
                    changes.append({**c, "span": [s + offset, e + offset]})
                else:
                    changes.append(c)

            offset += len(ct)

        return {"clean_text": "".join(clean_parts), "flags": flags, "changes": changes}
