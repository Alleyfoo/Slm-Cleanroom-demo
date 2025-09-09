import importlib

import app.slm_llamacpp as llm
import app.pipeline as pipeline
from app.pipeline import run_pipeline, slm_cleanup


def _patch_model(monkeypatch, func):
    """Helper to patch the low level model cleanup function."""
    monkeypatch.setattr(llm, "slm_cleanup", func)
    monkeypatch.setattr(pipeline, "_slm_cleanup", func)


def test_json_only_prompt_echo(monkeypatch):
    """Model echo without JSON should still yield valid structure."""

    def echo(masked_text: str, translate_embedded: bool, **_: object):
        return masked_text

    _patch_model(monkeypatch, echo)
    res = slm_cleanup("Just some text.", False)
    assert res == {"clean_text": "Just some text.", "flags": [], "changes": []}


def test_flags_shape_and_numeric_roll_back(monkeypatch):
    """String flags from the model are normalised and numeric_change dropped."""

    def mock(masked_text: str, translate_embedded: bool, **_: object):
        return {
            "clean_text": masked_text,
            "flags": ["embedded_en", "numeric_change"],
            "changes": [],
        }

    _patch_model(monkeypatch, mock)
    result = run_pipeline("Hello 10")
    assert result["flags"] == [{"type": "embedded_en"}]


def test_ctx_env(monkeypatch):
    """CTX defaults to 2048 but respects the environment variable."""

    import app.config as config

    monkeypatch.delenv("CTX", raising=False)
    importlib.reload(config)
    assert config.CTX == 2048

    monkeypatch.setenv("CTX", "123")
    importlib.reload(config)
    assert config.CTX == 123

