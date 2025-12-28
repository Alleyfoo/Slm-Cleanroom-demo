import argparse
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.io_utils import read_table, write_table, parse_terms, serialize
from app.checkpointing import Checkpointer
from app.review_queue import enqueue as enqueue_review
from app.logging_utils import get_logger


def main() -> None:
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

    has_terms = "protected_terms" in df.columns
    has_translate = "translate_embedded" in df.columns
    has_id = "id" in df.columns

    base_columns = list(df.columns)
    extra_columns = ["clean_text", "flags", "changes", "mixed_languages", "risk_score", "review_status"]
    all_columns = base_columns + [c for c in extra_columns if c not in base_columns]

    use_checkpoint = out.suffix.lower() == ".csv" and has_id
    checkpointer = None
    if use_checkpoint:
        checkpointer = Checkpointer(out, out.with_suffix(".errors.csv"), id_field="id", fieldnames=all_columns)

    clean_texts: list[str] = []
    flags_col: list[str] = []
    changes_col: list[str] = []
    mixed_col: list[bool] = []
    risk_scores: list[float] = []
    review_statuses: list[str] = []
    flag_stats: dict[str, int] = {"embedded_en": 0, "term_change": 0}

    def process_row(row: dict) -> dict:
        text = str(row["text"])
        terms = parse_terms(row.get("protected_terms")) if has_terms else []
        translate = bool(row.get("translate_embedded")) if has_translate else False
        row_id = row.get("id")
        res = run_pipeline(
            text,
            translate_embedded=translate,
            protected_terms=terms,
            record_id=str(row_id) if row_id is not None else None,
        )
        if res.get("review_status") == "pending":
            enqueue_review(str(row_id or ""), {"text": text, "clean_text": res.get("clean_text"), "flags": res.get("flags"), "changes": res.get("changes")})
        return res

    rows = df.to_dict("records")
    chunk_size = max(1, args.workers * 4)
    processed_count = 0
    skipped = 0
    log, _ = get_logger()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            to_process = []
            for row in chunk:
                if use_checkpoint and checkpointer and checkpointer.is_processed(row.get("id")):
                    skipped += 1
                    continue
                to_process.append(row)
            results = ex.map(process_row, to_process)
            for row, res in zip(to_process, results):
                out_row = {**row}
                out_row["clean_text"] = res["clean_text"]
                out_row["flags"] = serialize(res["flags"])
                out_row["changes"] = serialize(res["changes"])
                out_row["mixed_languages"] = res["mixed_languages"]
                out_row["risk_score"] = res.get("risk_score", 1.0)
                out_row["review_status"] = res.get("review_status", "auto_approved")

                if use_checkpoint and checkpointer:
                    try:
                        checkpointer.append_row({k: out_row.get(k) for k in all_columns})
                    except Exception as exc:
                        checkpointer.append_error(row.get("id"), str(exc), row.get("text", ""))
                else:
                    clean_texts.append(out_row["clean_text"])
                    flags_col.append(serialize(out_row["flags"]))
                    changes_col.append(serialize(out_row["changes"]))
                    mixed_col.append(out_row["mixed_languages"])
                    risk_scores.append(out_row["risk_score"])
                    review_statuses.append(out_row["review_status"])

                for f in res["flags"]:
                    t = f.get("type") if isinstance(f, dict) else f
                    if t:
                        flag_stats[t] = flag_stats.get(t, 0) + 1
                processed_count += 1
            if (i + len(chunk)) % 500 == 0:
                log.info("batch_progress", event="batch_progress", processed=processed_count, skipped=skipped)

    if not use_checkpoint:
        df["clean_text"] = clean_texts
        df["flags"] = flags_col
        df["changes"] = changes_col
        df["mixed_languages"] = mixed_col
        df["risk_score"] = risk_scores
        df["review_status"] = review_statuses
        write_table(df, str(out))

    total = processed_count
    flag_count = sum(flag_stats.values())
    elapsed = time.time() - t0
    elapsed_ms = int(elapsed * 1000)
    throughput = total / elapsed if elapsed > 0 else 0
    summary = ", ".join(f"{k}={v}" for k, v in sorted(flag_stats.items()))
    log.info(
        "batch_complete",
        event="batch_complete",
        processed=total,
        skipped=skipped,
        flags=flag_count,
        elapsed_ms=elapsed_ms,
        throughput_rps=throughput,
        output=str(out),
        summary=summary,
    )


if __name__ == "__main__":
    main()
