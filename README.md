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
