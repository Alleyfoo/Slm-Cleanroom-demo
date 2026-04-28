# slm-Cleanroom

A small, self-contained tool that tidies up product descriptions — automatically — without sending any data to the cloud.

> **Design Document:** see [docs/design_document.md](docs/design_document.md).
> All new changes must reference the sections they touch in the Design Document.

## What this project does

Online shops and catalogues collect product descriptions written by many different people: some are messy, full of typos, inconsistent capitalisation, or stray formatting. Cleaning them up by hand is slow and expensive.

This project takes raw product text (in Finnish or English) and produces a tidied-up version, while making sure nothing important is changed by mistake — brand names stay correct, numbers and units are preserved, and anything the system isn't sure about is sent to a human for review instead of silently "fixed".

It runs entirely on your own computer or server, so confidential product data never leaves the building.

## Why it matters

- **Privacy by default.** Everything runs locally — no third-party API calls, no data leaks.
- **Safe automation.** Built-in safety checks (called "guardrails") catch the kinds of mistakes AI models typically make: dropped numbers, invented words, mangled brand names.
- **Human in the loop.** Anything risky goes to a review queue (a list of items waiting for a person to approve, reject, or edit) rather than being shipped automatically.
- **Cheap to run.** It uses a small language model (a compact AI model that fits on a laptop), not a giant cloud system.

## How it works (at a glance)

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

In words:
1. Protected terms (brand names, product codes) are hidden so the AI can't accidentally rewrite them.
2. A small local AI model rewrites the text in a strict structured format (JSON, a standard data format).
3. Guardrails check that nothing important changed — same numbers, same protected terms.
4. Anything suspicious is logged to a review queue stored in SQLite (a lightweight built-in database).
5. The clean text and a full record of what changed are returned to the caller.

## Getting started

### Quickstart (Codespace or local machine)
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

Start the API server (the program that other software talks to over the network):
```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

Clean a single file from the command line:
```bash
python -m cli.clean_file input.txt -o output.json
```

### Optional Finnish spellcheck (Voikko)

Voikko is an open-source Finnish spellchecker. If installed, the pipeline picks it up automatically — no code changes needed.

On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y python3-libvoikko voikko-fi
```

### Batch run (clean a whole spreadsheet)

Process many rows at once from a CSV (a plain spreadsheet file):
```bash
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv \
  --model-path "$PWD/models/$HF_FILENAME" --workers 1
```

### Review screen (Streamlit UI)

A simple web page for a human reviewer to approve, reject, or edit flagged items:
```bash
streamlit run ui/app.py
```

### Docker

Docker is a tool that packages the app with everything it needs, so it runs the same on any machine. Build the image:
```bash
docker build -t slm-cleanroom .
```

Run the batch cleaner inside Docker, sharing the model file from your computer:
```bash
docker run --rm -v $(pwd)/models:/models -v $(pwd):/app -e MODEL_PATH=/models/<file>.gguf \
  -w /app python:3.12-slim bash -lc "pip install -r requirements.txt && python cli/clean_table.py data/mock_inputs.csv -o /app/out.csv"
```

### Benchmarking

Measure how fast and reliable a given model is on real-looking data, to help pick the right one:
```bash
python tools/bench.py --file data/mock_inputs.csv --workers 1 --samples 200
```
The script reports typical and worst-case time per row, overall throughput, how often the AI had to retry, and how many items were flagged for review.

## Contributing

Before proposing changes, update or reference the relevant sections in [docs/design_document.md](docs/design_document.md). Pull requests (proposed changes) without a Design Document reference may be rejected.
