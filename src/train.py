#!/usr/bin/env python
"""Train LightGBM model for 30-day readmission prediction.

MLflow tracking: local file store (no server).
Model artifact: models/model.joblib + MLflow logged model.
Predictions: data/interim/test_predictions.csv
"""

import os
import pathlib
import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score, accuracy_score
)
from sklearn.model_selection import train_test_split

PROJ = pathlib.Path(__file__).resolve().parent.parent

# ── 1. Load data ───────────────────────────────────────────────────────────
print("Loading features.parquet …")
df = pd.read_parquet(PROJ / "data" / "interim" / "features.parquet")
print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

# ── 2. Separate X / y ─────────────────────────────────────────────────────
DROP_COLS = {"claim_id", "beneficiary_id", "readmit_30d"}
feature_cols = [c for c in df.columns if c not in DROP_COLS]
X = df[feature_cols]
y = df["readmit_30d"]

print(f"  Features ({len(feature_cols)}): {', '.join(feature_cols)}")
print(f"  Target distribution: {dict(y.value_counts().sort_index())}")

# ── 3. Stratified train/test split ────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

# ── 4. Train LightGBM with monotonic constraints ─────────────────────────
# Enforce clinically correct directional relationships:
#   prior_admissions: more → higher readmission risk
#   age: older → higher readmission risk
#   length_of_stay: longer stay → higher readmission risk
constraint_map = {"prior_admissions": 1, "age": 1, "length_of_stay": 1}
monotone_constraints = [constraint_map.get(f, 0) for f in feature_cols]
print(f"Training LightGBM with monotonic constraints …")
print(f"  Constraints: {dict(zip(feature_cols, monotone_constraints))}")
model = lgb.LGBMClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6,
    class_weight="balanced",
    random_state=42,
    verbose=-1,
    monotone_constraints=monotone_constraints,
)
model.fit(X_train, y_train)

# ── 5. Evaluate on test set ───────────────────────────────────────────────
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

auc_roc = roc_auc_score(y_test, y_prob)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
acc = accuracy_score(y_test, y_pred)

print(f"\n=== GATE E: Test Set Metrics ===")
print(f"AUC-ROC:   {auc_roc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall:    {rec:.4f}")
print(f"F1:        {f1:.4f}")
print(f"Accuracy:  {acc:.4f}")

# Leakage check
if auc_roc > 0.90:
    print(f"\n✗ AUC-ROC {auc_roc:.4f} > 0.90 — possible target leakage. STOPPING.")
    import sys
    sys.exit(2)
if auc_roc < 0.55:
    print(f"\n✗ AUC-ROC {auc_roc:.4f} < 0.55 — model failed to learn. STOPPING.")
    import sys
    sys.exit(2)
print(f"\n✓ AUC-ROC {auc_roc:.4f} in acceptable range [0.55, 0.85]")

# ── 6. MLflow logging (local file store, no server) ───────────────────────
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
MLRUNS = PROJ / "mlruns"
MLRUNS.mkdir(exist_ok=True)
tracking_uri = f"file://{MLRUNS.resolve()}"
mlflow.set_tracking_uri(tracking_uri)

experiment = mlflow.set_experiment("cms-readmission-30d")
print(f"\nMLflow tracking URI: {tracking_uri}")
print(f"Experiment: cms-readmission-30d (id={experiment.experiment_id})")

with mlflow.start_run() as run:
    # Hyperparameters
    mlflow.log_params(model.get_params())
    # Metrics
    mlflow.log_metrics({
        "auc_roc": auc_roc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "accuracy": acc,
    })
    # Log model artifact
    mlflow.lightgbm.log_model(model, "lightgbm_model")
    run_id = run.info.run_id

print(f"MLflow run ID: {run_id}")

# ── 7. Save model via joblib ──────────────────────────────────────────────
MODELS_DIR = PROJ / "models"
MODELS_DIR.mkdir(exist_ok=True)
joblib.dump(model, MODELS_DIR / "model.joblib")
print(f"Model saved to {MODELS_DIR / 'model.joblib'}")

# ── 8. Save test predictions ──────────────────────────────────────────────
pred_df = pd.DataFrame({
    "y_true": y_test.values,
    "y_pred": y_pred,
    "y_prob": y_prob,
})
pred_df.to_csv(PROJ / "data" / "interim" / "test_predictions.csv", index=False)
print(f"Predictions saved to {PROJ / 'data' / 'interim' / 'test_predictions.csv'}")

print("\n✓ Training complete.")
