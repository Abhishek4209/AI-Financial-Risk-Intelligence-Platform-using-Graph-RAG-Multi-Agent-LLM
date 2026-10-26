"""Column-aware cleaning helpers; cleaning never silently drops rows."""
from typing import Any
import pandas as pd
def clean_frame(frame: pd.DataFrame, *, drop_duplicates: bool = False) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    if cleaned.columns.duplicated().any():
        duplicates = cleaned.columns[cleaned.columns.duplicated()].tolist()
        raise ValueError("Duplicate column names after normalization: %s" % duplicates)
    if drop_duplicates:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    return cleaned
def coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    missing = [column for column in columns if column not in result]
    if missing:
        raise ValueError("Numeric columns not found: %s" % missing)
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result
def missing_value_report(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)), "columns": int(frame.shape[1]),
        "missing": {str(column): {"count": int(count), "fraction": float(count / max(len(frame), 1)
)}
                    for column, count in frame.isna().sum().items() if count},
        "duplicate_rows": int(frame.duplicated().sum()),
    }
