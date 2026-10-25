"""Shared project paths and decision-support constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_ROOT = DATA_ROOT / "raw"
PROCESSED_DATA_ROOT = DATA_ROOT / "processed"
MODEL_ROOT = PROJECT_ROOT / "models"
VECTOR_STORE_ROOT = PROJECT_ROOT / "vector_store" / "financial_rag_faiss"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_TOP_K = 5
CREDIT_MODEL_FILES = {
        "taiwan": "taiwan_credit_default_model.pkl",
        "lending_club": "lending_club_default_model.pkl",
}
FRAUD_MODEL_FILES = {
        "paysim": "Fraud_models/paysim_fraud_model.pkl",
        "ieee_cis": "Fraud_models/ieee_fraud_model.pkl",
}
