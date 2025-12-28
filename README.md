# slm-Cleanroom

Local product description cleaner pipeline.

> **Design Document:** see [docs/design_document.md](docs/design_document.md).  
> All new changes must reference the sections they touch in the Design Document.

## Overview
- Local FI/EN cleaner with guardrails: TERM and numeric invariance, JSON via GBNF, spellcheck, and entity locks.
- Review queue backed by SQLite; UI is API-only (approve/reject/edit).
- Batch CLI, FastAPI service, and Docker Compose for API + UI.

## Workflow (ASCII)
```
Input text/CSV
    |
    v
Mask protected terms -> SLM cleanup (GBNF JSON) -> Guardrails (terms/numerics)
    |
    +--> Flags/changes -> SQLite review queue -> UI/API review endpoints
    |
    +--> Clean text + audit trail to API response / CSV output
```

## Getting started

### Quickstart (Codespace/local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# choose a model (free, small):
export HF_REPO_ID="bartowski/TinyLlama-1.1B-1T-GGUF"
export HF_FILENAME="TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf"

# download only if missing models/<file>.gguf
python -m app.model_download

# set path for runtime
export MODEL_PATH="$PWD/models/$HF_FILENAME"
# optionally raise context window (only if the model supports it)
export CTX=4096
```

Install dependencies and run the API server:
```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

CLI example:
```bash
python -m cli.clean_file input.txt -o output.json
```

### Optional Finnish spellcheck (Voikko)
On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y python3-libvoikko voikko-fi
```
No code changes required; the pipeline auto-enables Voikko if available.

### Batch run (CSV)
```bash
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv \
  --model-path "$PWD/models/$HF_FILENAME" --workers 1
```

### Streamlit review UI
```bash
streamlit run ui/app.py
```

### Docker
Build an image from the provided Dockerfile:
```bash
docker build -t slm-cleanroom .
```

### Contributing
Before proposing changes, update or reference the relevant sections in [docs/design_document.md](docs/design_document.md). PRs without a Design Document reference may be rejected.

Run the batch cleaner with a bind-mounted model:
```bash
docker run --rm -v $(pwd)/models:/models -v $(pwd):/app -e MODEL_PATH=/models/<file>.gguf \
  -w /app python:3.12-slim bash -lc "pip install -r requirements.txt && python cli/clean_table.py data/mock_inputs.csv -o /app/out.csv"
```

### Benchmarking
Run a quick performance benchmark on a sample of rows to guide model selection:
```bash
python tools/bench.py --file data/mock_inputs.csv --workers 1 --samples 200
```
The script reports median and 95p latency per row, throughput, JSON retry rate and flag distribution.
