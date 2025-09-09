import streamlit as st
import pandas as pd

from app.pipeline import run_pipeline
from app.io_utils import parse_terms

st.title("SLM Cleanroom Review")

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
        if res["flags"]:
            st.table(pd.DataFrame(res["flags"]))
        else:
            st.write("None")

        st.write("Changes:")
        if res["changes"]:
            st.table(pd.DataFrame(res["changes"]))
        else:
            st.write("None")

        st.markdown("---")
