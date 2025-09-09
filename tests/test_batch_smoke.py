import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import run_pipeline

def test_embedded_en_flag():
    txt = "Takki on lämmin – super warm for winter commutes!"
    res = run_pipeline(txt, translate_embedded=False)
    assert any(f.get("type")=="embedded_en" for f in res["flags"]) or res["mixed_languages"]

def test_term_protection():
    txt = "Malli <TERM>ABC-123</TERM> sopii tähän."
    res = run_pipeline(txt, translate_embedded=True, protected_terms=["ABC-123"])
    assert "<TERM>ABC-123</TERM>" in res["clean_text"]
