# slm-Cleanroom

Local product description cleaner pipeline.

> **Design Document:** see [docs/design_document.md](docs/design_document.md).  
> All new changes must reference the sections they touch in the Design Document.

### CS Chatbot LLM Demo (EN)
[Alleyfoo/Cs-chatbot-llm-demo](https://github.com/Alleyfoo/Cs-chatbot-llm-demo) — Chat-first queue backed by SQLite (safe for multi-workers), FastAPI ingest with API key auth, and Docker Compose (app + worker + Ollama). Quickstart: clone, set `INGEST_API_KEY`, `docker compose up --build` (or `uvicorn app.server:app --reload`), enqueue via `/chat/enqueue`, and watch workers drain the queue.

### CS Chatbot LLM Demo (FI)
[Alleyfoo/Cs-chatbot-llm-demo](https://github.com/Alleyfoo/Cs-chatbot-llm-demo) — Chat-painotteinen jono SQLite-taustalla (turvallinen monelle työntekijälle), FastAPI-ingest API-avaimella ja Docker Compose (sovellus + työntekijä + Ollama). Pika-aloitus: kloonaa repo, aseta `INGEST_API_KEY`, `docker compose up --build` (tai `uvicorn app.server:app --reload`), jonota viestejä `/chat/enqueue`-päähän ja seuraa, kun työntekijät käsittelevät jonon.

## Getting started

### Quickstart (Codespace/local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# choose a model (free, small):
export HF_REPO_ID="bartowski/TinyLlama-1.1B-1T-GGUF"
export HF_FILENAME="TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf"

# download only if missing → models/<file>.gguf
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

### Batch run (CSV → CSV)

```bash
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv \
  --model-path "$PWD/models/$HF_FILENAME" --workers 4
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
python tools/bench.py --file data/mock_inputs.csv --workers 2 --samples 200
```

The script reports median and 95p latency per row, throughput, JSON retry rate and flag distribution.

