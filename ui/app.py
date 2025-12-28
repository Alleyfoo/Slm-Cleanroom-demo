import json
from pathlib import Path
import requests
import pandas as pd
import streamlit as st

from app.pipeline import run_pipeline
from app.io_utils import parse_terms

API_URL = "http://localhost:8000"
REVIEW_PATH = Path("data/review_queue.jsonl")


def load_review_queue():
    if not REVIEW_PATH.exists():
        return []
    rows = []
    with REVIEW_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def review_tab():
    st.header("Review Queue")
    items = [r for r in load_review_queue() if r.get("status") == "pending"]
    if not items:
        st.info("No pending items.")
        return
    for item in items:
        iid = item.get("id", "")
        st.subheader(f"ID: {iid}")
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Original", item.get("text", ""), height=180, key=f"orig_{iid}")
        with col2:
            st.text_area("Clean", item.get("clean_text", ""), height=180, key=f"clean_{iid}")

        flags = item.get("flags") or []
        changes = item.get("changes") or []
        st.write("Flags")
        st.table(pd.DataFrame(flags)) if flags else st.write("None")
        st.write("Changes")
        st.table(pd.DataFrame(changes)) if changes else st.write("None")

        col_ok, col_rej, col_edit = st.columns(3)
        with col_ok:
            if st.button(f"Approve {iid}", key=f"approve_{iid}"):
                requests.post(f"{API_URL}/review/{iid}", json={"approved": True})
                st.experimental_rerun()
        with col_rej:
            if st.button(f"Reject {iid}", key=f"reject_{iid}"):
                requests.post(f"{API_URL}/review/{iid}", json={"approved": False})
                st.experimental_rerun()
        with col_edit:
            correction = st.text_area("Edit & Approve", value=item.get("clean_text", ""), key=f"edit_{iid}")
            if st.button(f"Save {iid}", key=f"save_{iid}"):
                requests.post(f"{API_URL}/review/{iid}", json={"approved": True, "correction": correction})
                st.experimental_rerun()


def upload_tab():
    st.header("Ad-hoc Processing")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    if uploaded is not None:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        for idx, row in df.iterrows():
            text = str(row.get("text", ""))
            terms = parse_terms(row.get("protected_terms"))
            translate = bool(row.get("translate_embedded", False))
            res = run_pipeline(text, translate_embedded=translate, protected_terms=terms)

            st.subheader(f"Row {row.get('id', idx)}")
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("Original", text, height=150, key=f"orig_{idx}")
            with col2:
                st.text_area("Clean", res['clean_text'], height=150, key=f"clean_{idx}")

            st.write("Flags:")
            st.table(pd.DataFrame(res["flags"])) if res["flags"] else st.write("None")

            st.write("Changes:")
            st.table(pd.DataFrame(res["changes"])) if res["changes"] else st.write("None")

            st.markdown("---")


st.title("SLM Cleanroom Review")
tab1, tab2 = st.tabs(["Ad-hoc", "Review Queue"])
with tab1:
    upload_tab()
with tab2:
    review_tab()
