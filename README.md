# slm-Cleanroom

Local product description cleaner pipeline.

## Getting started

Install dependencies and run the API server:

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

CLI example:

```bash
python -m cli.clean_file input.txt -o output.json
```

### Batch run (CSV → CSV)

```bash
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv \
  --model-path "$PWD/models/$HF_FILENAME"
```
