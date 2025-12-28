import json
import os
import requests
import pandas as pd
import streamlit as st

# Default to localhost for local dev; override in Docker/Cloud
API_URL = os.environ.get("API_URL", "http://localhost:8000")


def call_clean(text: str, terms=None, translate=False, rid=None):
    payload = {
        "text": text,
        "terms": terms or [],
        "translate_embedded": translate,
        "id": rid,
    }
    resp = requests.post(f"{API_URL}/clean", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def review_tab():
    st.header("Review Queue (via API)")
    try:
        resp = requests.get(f"{API_URL}/reviews/pending", timeout=10)
        resp.raise_for_status()
        items = resp.json()
    except Exception as exc:
        st.error(f"Failed to load review queue: {exc}")
        return

    pending = [i for i in items if i.get("status") == "pending"]
    if not pending:
        st.info("No pending items.")
        return

    for item in pending:
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
                st.rerun()
        with col_rej:
            if st.button(f"Reject {iid}", key=f"reject_{iid}"):
                requests.post(f"{API_URL}/review/{iid}", json={"approved": False})
                st.rerun()
        with col_edit:
            correction = st.text_area("Edit & Approve", value=item.get("clean_text", ""), key=f"edit_{iid}")
            if st.button(f"Save {iid}", key=f"save_{iid}"):
                requests.post(f"{API_URL}/review/{iid}", json={"approved": True, "correction": correction})
                st.rerun()


def upload_tab():
    st.header("Ad-hoc Processing (via API)")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    if uploaded is None:
        return

    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    for idx, row in df.iterrows():
        text = str(row.get("text", ""))
        terms = []
        if "protected_terms" in row and pd.notna(row["protected_terms"]):
            if isinstance(row["protected_terms"], str):
                terms = [t.strip() for t in row["protected_terms"].split(";") if t.strip()]
        translate = bool(row.get("translate_embedded", False))
        rid = row.get("id", idx)
        try:
            res = call_clean(text, terms=terms, translate=translate, rid=rid)
        except Exception as exc:
            st.error(f"Row {rid}: API call failed: {exc}")
            continue

        st.subheader(f"Row {rid}")
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Original", text, height=150, key=f"orig_{idx}")
        with col2:
            st.text_area("Clean", res.get("clean_text", ""), height=150, key=f"clean_{idx}")

        st.write("Flags:")
        st.table(pd.DataFrame(res.get("flags", []))) if res.get("flags") else st.write("None")

        st.write("Changes:")
        st.table(pd.DataFrame(res.get("changes", []))) if res.get("changes") else st.write("None")

        st.markdown("---")


st.title("SLM Cleanroom Review")
tab1, tab2 = st.tabs(["Ad-hoc", "Review Queue"])
with tab1:
    upload_tab()
with tab2:
    review_tab()
