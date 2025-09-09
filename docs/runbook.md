# SLM Cleanroom — Run Book

> This run book shows how to set up and run the project locally, in GitHub Codespaces, in Docker, and in Google Colab.  
> **Design Document:** see [docs/design_document.md](design_document.md). All changes must reference it.

---

## 0) Model choices (GGUF)
Free, small to large (pick one):
- **TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf** (fast baseline)
- **Mistral-7B-Instruct-v0.3.Q4_K_M.gguf** (better quality)
- **Llama-3.1-8B-Instruct.Q4_K_M.gguf** (higher quality)

---

## 1) Local / Codespace

### 1.1. Environment
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

1.2. Download model (only if missing)
# pick a model
export HF_REPO_ID="bartowski/TinyLlama-1.1B-1T-GGUF"
export HF_FILENAME="TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf"

python -m app.model_download     # downloads models/$HF_FILENAME if missing
export MODEL_PATH="$PWD/models/$HF_FILENAME"

1.3. Smoke tests
PYTHONPATH=. pytest -q
python -m cli.clean_table data/mock_inputs.csv -o data/mock_outputs.csv --model-path "$MODEL_PATH"

1.4. API
uvicorn app.server:app --reload --port 8000
# in another shell:
curl -s -X POST http://localhost:8000/clean -H "content-type: application/json" \
 -d '{"text":"Takki – super warm for winter commutes!","translate_embedded":true}' | jq .

```

2) Docker (reproducible)
2.1. Build image
docker build -t slm-cleanroom:latest .

2.2. Run batch (bind-mount model + repo)
# Make sure a model file exists in ./models first
docker run --rm \
  -v "$(pwd)":/app \
  -v "$(pwd)/models":/models \
  -e MODEL_PATH=/models/TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf \
  -w /app slm-cleanroom:latest \
  bash -lc 'python cli/clean_table.py data/mock_inputs.csv -o /app/data/mock_outputs.csv'

3) Google Colab (with Drive model auto-download)
3.1. Install dependencies
!pip -q install llama-cpp-python langid rapidfuzz python-levenshtein \
               pyspellchecker huggingface_hub pandas openpyxl

3.2. Mount Drive
from google.colab import drive
drive.mount('/content/drive')

3.3. Download model to Drive only if missing
from pathlib import Path
import os, shutil
from huggingface_hub import hf_hub_download

# Choose model
REPO_ID = "bartowski/TinyLlama-1.1B-1T-GGUF"
FILENAME = "TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf"

DRIVE_ROOT = Path("/content/drive/MyDrive")
MODELS_DIR = DRIVE_ROOT / "slm_cleanroom" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS_DIR / FILENAME

if MODEL_PATH.exists():
    print("✅ Model already in Drive:", MODEL_PATH)
else:
    print("⬇️ Downloading model to Colab tmp…")
    tmp = hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir="/content")
    shutil.copy2(tmp, MODEL_PATH)
    print("✅ Saved to Drive:", MODEL_PATH)

os.environ["MODEL_PATH"] = str(MODEL_PATH)
MODEL_PATH

3.4. Import project code

Upload/clone the repository into /content/slm-cleanroom (or use Colab’s file browser). Then:

import sys, os
sys.path.append("/content/slm-cleanroom")  # adjust if different
from app.pipeline import run_pipeline

3.5. Single-string smoke test
res = run_pipeline(
    "Tämä takki on NorthFace 1996 retro down jacket – super warm for winter commutes!",
    translate_embedded=True,
    protected_terms=["NorthFace 1996"]
)
res["clean_text"], res["flags"][:3]

3.6. Batch on CSV and save to Drive
from cli.clean_table import main as batch_main
import sys, pandas as pd, os

# Ensure MODEL_PATH is inherited
print("MODEL_PATH =", os.environ.get("MODEL_PATH"))

# Run batch on mock CSV inside repo
sys.argv = ["clean_table.py", "/content/slm-cleanroom/data/mock_inputs.csv",
            "-o", "/content/mock_outputs.csv", "--model-path", os.environ["MODEL_PATH"]]
batch_main()

# Save outputs to Drive
import shutil
OUT_DRIVE = "/content/drive/MyDrive/slm_cleanroom/outputs/mock_outputs.csv"
shutil.copy("/content/mock_outputs.csv", OUT_DRIVE)
print("✅ Saved:", OUT_DRIVE)

pd.read_csv("/content/mock_outputs.csv").head()

4) Configuration & Tuning

You can control runtime via env vars (see app/config.py):

MODEL_PATH — path to .gguf

N_THREADS (default 8), CTX (default 8192)

TEMP (default 0.0), MAX_TOKENS (default 512)

Example:

export N_THREADS=12 CTX=4096 TEMP=0.0 MAX_TOKENS=512

5) Quality & Guardrails

TERM invariance: <TERM>…</TERM> content must be identical pre/post.

Numerics: signed numbers, percentages, ranges (e.g., 12–15), and decimals (3,5) must not change.

JSON validity: pipeline retries with smaller chunks if JSON parsing fails.

Flags: at least embedded_en, term_change, numeric_change are tracked.

Run tests:

PYTHONPATH=. pytest -q

6) Troubleshooting

MODEL_PATH is not set or file not found
→ Export MODEL_PATH or pass --model-path to CLI.

ValueError: HF_FILENAME must be a model artifact
→ Use a .gguf/.ggml/.bin file, not README.md.

Colab OOM / very slow
→ Use TinyLlama instead of 7B/8B models; reduce CTX.

JSON parse errors
→ The pipeline’s retry logic should handle it. If persistent, reduce chunk size or try a different model.

7) Operational Tips

For large files, use --workers (e.g., 4–8) to increase throughput:

python cli/clean_table.py big.csv -o big.clean.csv \
  --model-path "$MODEL_PATH" --workers 6


Use tools/bench.py for quick perf sampling (if present):

python tools/bench.py --file data/mock_inputs.csv --samples 200 --workers 4


Streamlit review (if present):

streamlit run ui/app.py


**(Optional) Create** `notebooks/colab_bootstrap.py` **to mirror the Drive model “download-if-missing” logic (importable in notebooks):**
```python
# notebooks/colab_bootstrap.py
from pathlib import Path
import os, shutil
from typing import Optional
from huggingface_hub import hf_hub_download

def ensure_drive_model(repo_id: str, filename: str, drive_subdir: str = "slm_cleanroom/models") -> str:
    drive_root = Path("/content/drive/MyDrive")
    models_dir = drive_root / drive_subdir
    models_dir.mkdir(parents=True, exist_ok=True)
    dest = models_dir / filename
    if dest.exists():
        return str(dest)
    tmp = hf_hub_download(repo_id=repo_id, filename=filename, local_dir="/content")
    shutil.copy2(tmp, dest)
    return str(dest)

def set_model_env(path: str):
    os.environ["MODEL_PATH"] = path
    return path
```
