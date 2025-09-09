import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import run_pipeline


def test_embedded_en_flag():
    text = "Tämä takki on todella hyvä ja super warm for winter commutes kaupungilla."
    result = run_pipeline(text)
    assert any(f.get('type') == 'embedded_en' for f in result['flags'])


def test_term_unchanged():
    text = "Suosittu malli <TERM>NorthFace 1996</TERM> on klassikko."
    result = run_pipeline(text)
    assert '<TERM>NorthFace 1996</TERM>' in result['clean_text']
