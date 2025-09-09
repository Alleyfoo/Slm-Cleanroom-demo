import argparse
import os
import time
from pathlib import Path
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

    clean_texts = []
    flags_col = []
    changes_col = []
    mixed_col = []
    flag_stats = {"embedded_en": 0, "term_change": 0}

    for i, row in enumerate(df.itertuples()):
        text = str(row.text)
        terms = parse_terms(row.protected_terms) if has_terms else []
        translate = bool(row.translate_embedded) if has_translate else False

        res = run_pipeline(text, translate_embedded=translate, protected_terms=terms)
        clean_texts.append(res["clean_text"])
        flags_col.append(serialize(res["flags"]))
        changes_col.append(serialize(res["changes"]))
        mixed_col.append(res["mixed_languages"])

        for f in res["flags"]:
            t = f.get("type")
            if t:
                flag_stats[t] = flag_stats.get(t, 0) + 1

        if (i + 1) % 500 == 0:
            print(f"Processed {i + 1}/{len(df)} rows")

    df["clean_text"] = clean_texts
    df["flags"] = flags_col
    df["changes"] = changes_col
    df["mixed_languages"] = mixed_col

    write_table(df, str(out))
    total = len(df)
    flag_count = sum(flag_stats.values())
    elapsed = int((time.time() - t0) * 1000)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(flag_stats.items()))
    print(f"Processed {total} rows, flags={flag_count}, time={elapsed} ms → {out}")
    print(f"Summary: {summary}")


if __name__ == "__main__":
    main()
