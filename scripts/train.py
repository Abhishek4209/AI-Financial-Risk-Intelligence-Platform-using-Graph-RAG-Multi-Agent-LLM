"""Train a domain-specific binary risk model and save a reproducible artifact."""
import argparse
import json
import logging
import re
import tempfile
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
DATASET_DEFAULTS = {
    "taiwan": {"target": "default payment next month", "task": "credit risk"},
    "paysim": {"target": "isFraud", "task": "mobile-money fraud"},
    "ieee_cis": {"target": "isFraud", "task": "transaction fraud"},
    "european": {"target": "Class", "task": "credit-card fraud"},
    "bank_marketing": {"target": "y", "task": "customer propensity"},
    "lending_club": {"target": "loan_status", "task": "credit risk"},
    "custom": {"target": None, "task": "custom binary classification"},
}
POST_OUTCOME_COLUMNS = {
    "last_pymnt_d", "last_pymnt_amnt", "next_pymnt_d", "recoveries",
    "collection_recovery_fee", "total_rec_prncp", "total_rec_int",
    "total_rec_late_fee", "settlement_status", "settlement_date",
    "settlement_amount", "settlement_percentage", "debt_settlement_flag_date",
}
ID_COLUMNS = {"id", "index", "unnamed: 0", "customer_id", "transaction_id"}
POSITIVE_VALUES = {"1", "true", "yes", "y", "default", "bad", "fraud", "charged off"}
def _normalized(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())
def _find_column(columns, requested):
    normalized = {_normalized(column): column for column in columns}
    return normalized.get(_normalized(requested))
def _prepare_target(frame, dataset, target_column, positive_label):
    if dataset == "lending_club":
        status = frame[target_column].astype("string").str.strip().str.lower()
        good = status.eq("fully paid")
        bad = status.str.contains(r"charged off|default", na=False)
        selected = good | bad
        frame = frame.loc[selected].copy()
        labels = bad.loc[selected].astype("int8")
        if labels.nunique() != 2:
            raise ValueError("loan_status must contain both Fully Paid and charged-off/default loans")
        return frame, labels, "charged off/default"
    raw = frame[target_column]
    unique_values = list(pd.unique(raw.dropna()))
    if len(unique_values) != 2:
        raise ValueError("Target must contain exactly two non-null classes for binary risk training")
    positive = positive_label
    if positive is None and dataset == "taiwan":
        positive = "1"
    if positive is None:
        matches = [value for value in unique_values if _normalized(value) in POSITIVE_VALUES]
        positive = matches[0] if matches else max(unique_values, key=lambda value: _normalized(value))
    positive_match = next((value for value in unique_values if _normalized(value) == _normalized(positi
ve)), None)
    if positive_match is None:
        raise ValueError("Positive label %r was not found in target values %r" % (positive, unique_values
))
    not_null = raw.notna()
    labels = raw.loc[not_null].map(lambda value: int(_normalized(value) == _normalized(positive_match)
))
    return frame.loc[not_null].copy(), labels.astype("int8"), positive_match
def train(args):
    data_path = Path(args.data_path).expanduser().resolve()
    if not data_path.is_file():
        raise FileNotFoundError("Dataset not found: %s" % data_path)
    frame = pd.read_csv(data_path, low_memory=False)
    requested_target = args.target or DATASET_DEFAULTS[args.dataset]["target"]
    if not requested_target:
        raise ValueError("Pass --target for a custom dataset")
    target_column = _find_column(frame.columns, requested_target)
    if target_column is None:
        raise ValueError("Target column %r not found. Available columns: %s" % (requested_target, list(fr
ame.columns)))
    frame, labels, source_positive_label = _prepare_target(
        frame, args.dataset, target_column, args.positive_label
    )
    excluded = {_normalized(value) for value in args.drop_columns}
    excluded.update(ID_COLUMNS)
    if args.dataset == "lending_club":
        excluded.update(POST_OUTCOME_COLUMNS)
    feature_columns = [
        column for column in frame.columns
        if column != target_column and _normalized(column) not in excluded
    ]
    if not feature_columns:
        raise ValueError("No feature columns remain after excluding the target and identifiers")
    features = frame[feature_columns].copy()
    numeric_columns = list(features.select_dtypes(include=["number", "bool"]).columns)
    categorical_columns = [column for column in feature_columns if column not in numeric_columns]
    transformers = []
    if numeric_columns:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ], memory=None)
        transformers.append(("numeric", numeric_pipeline, numeric_columns))
    if categorical_columns:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ], memory=None)
        transformers.append(("categorical", categorical_pipeline, categorical_columns))
    if args.model == "logistic_regression":
        estimator = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=args.seed)
    else:
        estimator = RandomForestClassifier(
            n_estimators=args.n_estimators,
            class_weight="balanced_subsample",
            random_state=args.seed,
            n_jobs=args.jobs,
            min_samples_leaf=1,
            max_features="sqrt",
        )
    pipeline = Pipeline([
        ("preprocessor", ColumnTransformer(transformers=transformers, remainder="drop")),
        ("classifier", estimator),
    ], memory=None)
    class_counts = labels.value_counts()
    stratify = labels if len(class_counts) == 2 and class_counts.min() >= 2 else None
    if stratify is None:
        raise ValueError("Each target class needs at least two rows for a stratified train/test split")
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=args.test_size, random_state=args.seed, stratify=stratify
    )
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
    }
    artifact_path = Path(args.output or (Path("models") / (args.dataset + "_" + args.model + ".joblib"
)))
    artifact_path = artifact_path.expanduser().resolve()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": pipeline,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "source_positive_label": source_positive_label,
        "dataset": args.dataset,
        "task": DATASET_DEFAULTS[args.dataset]["task"],
        "model_name": args.model,
        "positive_label": 1,
        "threshold": args.threshold,
        "random_state": args.seed,
        "test_size": args.test_size,
        "data_path": str(data_path),
        "metrics": metrics,
        "excluded_columns": sorted(excluded),
        "class_distribution": {str(key): int(value) for key, value in labels.value_counts().items()}
,
    }
    with tempfile.NamedTemporaryFile(dir=artifact_path.parent, suffix=".joblib", delete=False) as temporar
y:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(artifact, temporary_path)
        temporary_path.replace(artifact_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return artifact_path, metrics, len(x_train), len(x_test)
def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(DATASET_DEFAULTS), required=True)
    parser.add_argument("--data-path", required=True, help="Path to one domain-specific CSV; datasets must 
not be merged")
    parser.add_argument("--target", help="Target column; defaults are supplied for supported datasets")
    parser.add_argument("--positive-label", help="Value that represents the positive/default/fraud class")
    parser.add_argument("--drop-columns", nargs="*", default=[], help="Additional columns to exclude from t
raining")
    parser.add_argument("--model", choices=["logistic_regression", "random_forest"], default="logistic_regr
ession")
    parser.add_argument("--output", help="Output joblib path; defaults under models/")
    parser.add_argument("--threshold", type=float, default=0.5, help="Stored operating threshold; not a reg
ulatory cutoff")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--jobs", type=int, default=-1)
    return parser.parse_args()
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    arguments = parse_args()
    if not 0.0 < arguments.test_size < 1.0:
        raise SystemExit("--test-size must be between 0 and 1")
    if not 0.0 <= arguments.threshold <= 1.0:
        raise SystemExit("--threshold must be between 0 and 1")
    saved_path, test_metrics, training_rows, testing_rows = train(arguments)
    print(json.dumps({
        "artifact": str(saved_path),
        "training_rows": training_rows,
        "test_rows": testing_rows,
        "metrics": test_metrics,
        "note": "Prediction scores support analyst review; they are not autonomous financial decisions.",
    }, indent=2))
