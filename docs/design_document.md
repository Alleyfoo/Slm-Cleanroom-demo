# SLM Cleanroom — Design Document

## 1. Purpose & Scope
**Goal:** Local pipeline that cleans mixed-language texts (FI focus, EN embedded), fixes spelling/grammar, protects `<TERM>…</TERM>` and numbers, and returns an auditable diff (`flags`, `changes`) at batch scale (CSV/Excel).
**In scope**
- Batch processing for CSV/Excel
- Single string API (`/clean`) + healthcheck
- Local model (GGUF via llama.cpp) w/ “download if missing”
- Basic EN spellcheck (pyspellchecker), optional FI via Voikko
- Guardrails for terms & numerics; valid JSON output, auto-retry on JSON fail
**Out of scope (for now)**
- Rich translation / summarization / reasoning
- Heavy UI (only light Streamlit reviewer)
- Non-FI/EN languages beyond basic detection
- Multi-agent autonomy

## 2. Functional Requirements
- `run_pipeline(text, translate_embedded, protected_terms)` → returns:
  ```json
  {
    "clean_text": "string",
    "flags": [{"type": "...", "start": 0, "end": 0, "text": "opt"}],
    "changes": [{"span": [0,0], "type":"spelling|grammar|punctuation|translation", "source":"spell|slm|voikko", "before":"", "after":""}],
    "lang_spans": [{"start":0,"end":0,"lang":"fi|en","text":"..."}],
    "mixed_languages": true
  }


CLI: python cli/clean_table.py <in.csv/xlsx> -o <out> [--model-path PATH] [--workers N]

API: FastAPI GET /healthz, POST /clean

Colab demo: end-to-end single + batch

Model download: HF repo/file, only-if-missing

3. Non-Functional Requirements

Reproducibility: Dockerfile + devcontainer (Phase 3)

Performance targets (baseline, CPU/Colab):

JSON validity ≥ 99.9%

Batch 500+ rows / 10 min with TinyLlama

Quality targets:

TERM & numeric invariance = 100%

Embedded-EN detection precision ≥ 95% on mock/golden

Extensibility: swap model via MODEL_PATH; knobs in app/config.py

4. Architecture & Directories
app/
  pipeline.py        # detection → spell/voikko → SLM cleanup → guardrails
  guardrails.py      # JSON extraction, schema checks
  model_download.py  # HF download-if-missing
  io_utils.py        # CSV/Excel I/O
  config.py          # runtime knobs (CTX, TEMP, etc.)
  server.py          # FastAPI
cli/
  clean_table.py
  clean_file.py      # (optional later)
data/
  mock_inputs.csv
  golden_inputs.csv
  golden_expected.jsonl
notebooks/
  colab_demo.ipynb
tests/
  test_pipeline_smoke.py
  test_batch_smoke.py
  test_golden.py
tools/
  bench.py
ui/
  app.py             # (optional Streamlit)
Dockerfile
requirements.txt
README.md

5. Models

Default: TinyLlama-1.1B-Instruct (fast)

Better: Mistral-7B-Instruct-v0.3 Q4_K_M

Alt: Llama-3.1-8B-Instruct Q4_K_M
Switch by setting MODEL_PATH. Download helpers live in app/model_download.py.

6. Guardrails & Validation

<TERM>…</TERM> content must remain byte-identical.

Numbers (including signed, %, ranges “12–15”, decimals “3,5”) must not change.

JSON strict: clean_text (str), flags (list), changes (list).

Auto-retry on JSON parse failure: smaller chunk (sentence level), then stitch, offset-correct flags/changes.

7. Spellchecking Strategy

EN: pyspellchecker fallback (token-level suggestions).

FI: optional Voikko (python3-libvoikko, voikko-fi) when available.

Merge into changes with source: "spell" | "voikko".

8. Batch Processing

CSV/Excel via pandas/openpyxl.

Optional parallelism (--workers, default 4). Preserve input order.

Output columns added: clean_text, flags, changes, mixed_languages.

9. QA & Regression

Mock set: 10 varied rows (FI/EN mix, typos, TERM, numbers).

Golden set: inputs + expected flags_hash + invariants.

Pytest must pass without model download (mock SLM in CI).

Bench script tools/bench.py for latency/throughput & retry rate.

10. Roadmap

Phase 1 (MVP): pipeline, CLI, API, Colab, mock
Phase 2: JSON retry + guardrails, parallel batch, config/logging, golden tests
Phase 3: Docker/devcontainer, Streamlit reviewer
Phase 4: FI Voikko enabled by default where available, benchmarking & tuning

11. Change Control

Every PR must reference this document: list section(s) changed and rationale.

If a change affects scope/requirements/architecture, update this doc in the same PR.


**Acceptance**
- File `docs/design_document.md` created exactly as above.
- No other files changed in this PR.
