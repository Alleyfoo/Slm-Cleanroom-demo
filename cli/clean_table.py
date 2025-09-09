import argparse
import os
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from app.io_utils import read_table, write_table, parse_terms, serialize


def main():
    ap = argparse.ArgumentParser(description="Batch-clean CSV/Excel table")
    ap.add_argument(
        "input",
        help="Input CSV/Excel with columns: id,text,(optional)protected_terms,(optional)translate_embedded",
    )
    ap.add_argument(
        "-o",
        "--output",
        help="Output path (.csv or .xlsx). Default: <input>.clean.csv",
        default=None,
    )
    ap.add_argument(
        "--model-path",
        default=None,
        help="Path to .gguf model (overrides $MODEL_PATH)",
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads (default 4)",
    )
    args = ap.parse_args()

    mp = args.model_path or os.environ.get("MODEL_PATH")
    if not mp or not Path(mp).exists():
        raise SystemExit(
            "MODEL_PATH is not set or file not found. Use --model-path or export MODEL_PATH=<path/to/model.gguf>"
        )
    os.environ["MODEL_PATH"] = str(mp)
    t0 = time.time()

    from app.pipeline import run_pipeline

    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.with_suffix(".clean.csv")

    df = read_table(str(inp))
    if "text" not in df.columns:
        raise SystemExit("Input must contain column 'text'")

    # optional columns
    has_terms = "protected_terms" in df.columns
    has_translate = "translate_embedded" in df.columns

    clean_texts: list[str] = []
    flags_col: list[str] = []
    changes_col: list[str] = []
    mixed_col: list[bool] = []

    def process_row(row: dict):
        text = str(row["text"])
        terms = parse_terms(row["protected_terms"]) if has_terms else []
        translate = bool(row["translate_embedded"]) if has_translate else False

        res = run_pipeline(text, translate_embedded=translate, protected_terms=terms)
        return (
            res["clean_text"],
            serialize(res["flags"]),
            serialize(res["changes"]),
            res["mixed_languages"],
        )

    rows = df.to_dict("records")
    chunk_size = max(1, args.workers * 4)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            for clean, flags, changes, mixed in ex.map(process_row, chunk):
                clean_texts.append(clean)
                flags_col.append(flags)
                changes_col.append(changes)
                mixed_col.append(mixed)

    df["clean_text"] = clean_texts
    df["flags"] = flags_col
    df["changes"] = changes_col
    df["mixed_languages"] = mixed_col

    write_table(df, str(out))
    total = len(df)
    flag_count = sum(len(json.loads(x)) if isinstance(x, str) else 0 for x in df["flags"])
    elapsed = time.time() - t0
    elapsed_ms = int(elapsed * 1000)
    throughput = total / elapsed if elapsed > 0 else 0
    print(
        f"Processed {total} rows, flags={flag_count}, time={elapsed_ms} ms "
        f"({throughput:.1f} rows/sec) → {out}"
    )


if __name__ == "__main__":
    main()
