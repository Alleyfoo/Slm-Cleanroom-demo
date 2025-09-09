# slm-Cleanroom

Local product description cleaner pipeline.

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


No code changes required; the pipeline auto-enables Voikko if available.
=======
### Batch run (CSV → CSV)

```bash
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv \
  --model-path "$PWD/models/$HF_FILENAME" --workers 4
```
