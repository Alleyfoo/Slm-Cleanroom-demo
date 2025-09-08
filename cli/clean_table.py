import argparse
from pathlib import Path
import pandas as pd
from app.io_utils import read_table, write_table, parse_terms, serialize
from app.pipeline import run_pipeline

def main():
    ap = argparse.ArgumentParser(description="Batch-clean CSV/Excel table")
    ap.add_argument("input", help="Input CSV/Excel with columns: id,text,(optional)protected_terms,(optional)translate_embedded")
    ap.add_argument("-o", "--output", help="Output path (.csv or .xlsx). Default: <input>.clean.csv", default=None)
    args = ap.parse_args()

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

    for _, row in df.iterrows():
        text = str(row["text"])
        terms = parse_terms(row["protected_terms"]) if has_terms else []
        translate = bool(row["translate_embedded"]) if has_translate else False

        res = run_pipeline(text, translate_embedded=translate, protected_terms=terms)
        clean_texts.append(res["clean_text"])
        flags_col.append(serialize(res["flags"]))
        changes_col.append(serialize(res["changes"]))
        mixed_col.append(res["mixed_languages"])

    df["clean_text"] = clean_texts
    df["flags"] = flags_col
    df["changes"] = changes_col
    df["mixed_languages"] = mixed_col

    write_table(df, str(out))
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
