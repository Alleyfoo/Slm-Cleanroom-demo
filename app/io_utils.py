from pathlib import Path
import pandas as pd
import json
from typing import List, Dict, Any

def read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p)
    return pd.read_csv(p)

def write_table(df: pd.DataFrame, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df.to_excel(p, index=False)
    else:
        df.to_csv(p, index=False)

def parse_terms(x: Any) -> List[str]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    if isinstance(x, list):
        return [str(t).strip() for t in x]
    # "term1; term2; term3"
    return [t.strip() for t in str(x).split(";") if t.strip()]

def serialize(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
