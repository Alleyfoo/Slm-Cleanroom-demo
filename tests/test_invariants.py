import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import run_pipeline


def test_numeric_patterns_unchanged():
    text = "Values: -10%, range 12–15, decimal 3,5, big 1.000,50."
    result = run_pipeline(text)
    assert result["clean_text"] == text
    assert not any(f.get("type") == "numeric_change" for f in result["flags"])


def test_term_survives():
    text = "<TERM>ABC-123 v2</TERM> stays."
    result = run_pipeline(text)
    assert "<TERM>ABC-123 v2</TERM>" in result["clean_text"]


def test_numeric_change_flag(monkeypatch):
    def fake_cleanup(masked_text: str, translate_embedded: bool, **kwargs):
        return {"clean_text": masked_text.replace("-10%", "-11%"), "flags": [], "changes": []}

    monkeypatch.setattr("app.pipeline.slm_cleanup", fake_cleanup)
    result = run_pipeline("Discount -10% now")
    assert {"type": "numeric_change"} in result["flags"]


def test_term_change_survives(monkeypatch):
    """Ensure that pipeline recovers if model changes a protected term."""
    def fake_cleanup(masked_text: str, translate_embedded: bool, **kwargs):
        # Simulate model maliciously changing the term
        return {"clean_text": masked_text.replace("ABC-123 v2", "XYZ-999"), "flags": [], "changes": []}

    monkeypatch.setattr("app.pipeline.slm_cleanup", fake_cleanup)

    # We NO longer expect a ValueError.
    # We expect the pipeline to catch the error and revert the text.
    result = run_pipeline("<TERM>ABC-123 v2</TERM>")

    # Assert that the bad change was reverted and the original term survives
    assert "<TERM>ABC-123 v2</TERM>" in result['clean_text']
    assert "XYZ-999" not in result['clean_text']
