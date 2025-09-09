import os
import sys
import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import run_pipeline


def test_numeric_patterns_unchanged():
    text = "Values: -10%, range 12\u201315, decimal 3,5, big 1.000,50."
    result = run_pipeline(text)
    assert result["clean_text"] == text
    assert "numeric_change" not in result["flags"]


def test_term_survives():
    text = "<TERM>ABC-123 v2</TERM> stays."
    result = run_pipeline(text)
    assert "<TERM>ABC-123 v2</TERM>" in result["clean_text"]


def test_numeric_change_flag(monkeypatch):
    def fake_cleanup(masked_text: str, translate_embedded: bool, **_: object):
        return {"clean_text": masked_text.replace("-10%", "-11%"), "flags": [], "changes": []}

    monkeypatch.setattr("app.pipeline.slm_cleanup", fake_cleanup)
    result = run_pipeline("Discount -10% now")
    assert {"type": "numeric_change"} in result["flags"]


def test_term_change_raises(monkeypatch):
    def fake_cleanup(masked_text: str, translate_embedded: bool, **_: object):
        return {"clean_text": masked_text.replace("ABC-123 v2", "XYZ-999"), "flags": [], "changes": []}

    monkeypatch.setattr("app.pipeline.slm_cleanup", fake_cleanup)
    with pytest.raises(ValueError):
        run_pipeline("<TERM>ABC-123 v2</TERM>")
