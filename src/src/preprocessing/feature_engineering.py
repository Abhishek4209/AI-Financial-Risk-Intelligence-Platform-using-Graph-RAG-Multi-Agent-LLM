"""Notebook-aligned feature transformations for PaySim and credit risk."""
from collections.abc import Mapping, Sequence
from typing import Any
import numpy as np
import pandas as pd
from src.utils.validators import validate_paysim_transaction
PAYSIM_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")
TAIWAN_FEATURES = [
    "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    *["BILL_AMT%d" % month for month in range(1, 7)],
    *["PAY_AMT%d" % month for month in range(1, 7)],
]
LENDING_FEATURE_ALIASES = {
    "loan_amount": "loan_amnt", "annual_income": "annual_inc", "debt_to_income": "dti",
    "credit_score_low": "fico_range_low", "credit_score_high": "fico_range_high",
    "delinquencies_2yr": "delinq_2yrs", "inquiries_6m": "inq_last_6mths",
    "open_accounts": "open_acc", "public_records": "pub_rec",
    "revolving_balance": "revol_bal", "revolving_utilization": "revol_util",
    "total_accounts": "total_acc",
}
def build_paysim_features(transaction: Mapping[str, Any], feature_columns: Sequence[str]) -> pd.DataFrame:
    row = validate_paysim_transaction(transaction)
    step = int(row["step"])
    values = {
        "step": step, "hour": step % 24, "day": step // 24,
        "amount": row["amount"], "oldbalanceOrg": row["oldbalanceOrg"],
        "newbalanceOrig": row["newbalanceOrig"], "oldbalanceDest": row["oldbalanceDest"],
        "newbalanceDest": row["newbalanceDest"],
        "origin_balance_error": abs(row["oldbalanceOrg"] - row["amount"] - row["newbalanceOrig"]),
        "destination_balance_error": abs(row["oldbalanceDest"] + row["amount"] - row["newbalanceDest"]),
        "origin_zero_after": int(row["newbalanceOrig"] == 0),
        "destination_zero_before": int(row["oldbalanceDest"] == 0),
        "amount_to_origin_balance": row["amount"] / row["oldbalanceOrg"] if row["oldbalanceOrg"] else 0.0,
    }
    values.update({"type_%s" % kind: int(row["type"] == kind) for kind in PAYSIM_TYPES})
    unsupported = [name for name in feature_columns if name not in values]
    if unsupported:
        raise ValueError("Unsupported model features: %s" % unsupported)
    return pd.DataFrame([[values[name] for name in feature_columns]], columns=list(feature_columns), dtyp
e="float32")
def build_lending_features(record: Mapping[str, Any], feature_columns: Sequence[str]) -> pd.DataFrame:
    values = {}
    for name in feature_columns:
        source = LENDING_FEATURE_ALIASES.get(name, name)
        value = record.get(source, record.get(name))
        values[name] = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return pd.DataFrame([values], columns=list(feature_columns))
def derive_taiwan_features(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in TAIWAN_FEATURES if column not in frame]
    if missing:
        raise ValueError("Taiwan credit input is missing columns: %s" % missing)
    return frame[TAIWAN_FEATURES].apply(pd.to_numeric, errors="coerce")
def harmonize_credit_record(record: Mapping[str, Any], dataset: str) -> dict[str, Any]:
    """Map comparison features; Taiwan and Lending Club models remain independent."""
    if dataset == "taiwan":
        limit = float(record.get("LIMIT_BAL", np.nan))
        bill = float(record.get("BILL_AMT1", np.nan))
        return {
            "dataset_source": "taiwan_credit_card", "loan_amount": np.nan,
            "annual_income": np.nan, "debt_to_income": np.nan, "credit_limit": limit,
            "age": float(record.get("AGE", np.nan)), "credit_score": np.nan,
            "delinquencies": max(float(record.get("PAY_0", np.nan)), 0),
            "revolving_balance": bill, "utilization": bill / limit if limit > 0 else np.nan,
            "monthly_payment": float(record.get("PAY_AMT1", np.nan)),
        }
    if dataset == "lending_club":
        utilization = pd.to_numeric(pd.Series([record.get("revol_util")]), errors="coerce").iloc[0]
        return {
            "dataset_source": "lending_club", "loan_amount": record.get("loan_amnt"),
            "annual_income": record.get("annual_inc"), "debt_to_income": record.get("dti"),
            "credit_limit": record.get("total_rev_hi_lim"), "age": np.nan,
            "credit_score": record.get("fico_range_low"), "delinquencies": record.get("delinq_2yrs"),
            "revolving_balance": record.get("revol_bal"),
            "utilization": utilization / 100 if pd.notna(utilization) else np.nan,
            "monthly_payment": record.get("installment"),
        }
    raise ValueError("dataset must be ’taiwan’ or ’lending_club’")
