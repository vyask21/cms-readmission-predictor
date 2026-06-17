"""Test suite for CMS Readmission Pipeline."""

from pathlib import Path
import joblib
import pandas as pd
import pytest

PROJ = Path(__file__).resolve().parent.parent
PARQUET = PROJ / "data" / "interim" / "features.parquet"
MODEL = PROJ / "models" / "model.joblib"

DATA_AVAILABLE = PARQUET.exists()
MODEL_AVAILABLE = MODEL.exists()


# ── Test: features parquet exists ─────────────────────────────────────────
def test_features_parquet_exists():
    assert PARQUET.exists(), f"{PARQUET} not found — run src/etl.py first"


# ── Test: no leakage columns ──────────────────────────────────────────────
@pytest.mark.skipif(not DATA_AVAILABLE, reason="data not available")
def test_features_no_leakage():
    df = pd.read_parquet(PARQUET)
    assert "CLM_PMT_AMT" not in df.columns, "CLM_PMT_AMT found in features — leakage!"
    for col in df.columns:
        assert "pmt" not in col.lower(), f"Payment column '{col}' found — leakage!"


# ── Test: identifiers not in model features ───────────────────────────────
@pytest.mark.skipif(not MODEL_AVAILABLE, reason="model not available")
def test_features_no_identifiers_in_model_input():
    model = joblib.load(MODEL)
    feature_names = model.feature_name_
    assert "claim_id" not in feature_names, "claim_id in model features!"
    assert "beneficiary_id" not in feature_names, "beneficiary_id in model features!"


# ── Test: readmit base rate sanity ────────────────────────────────────────
@pytest.mark.skipif(not DATA_AVAILABLE, reason="data not available")
def test_readmit_base_rate_sanity():
    df = pd.read_parquet(PARQUET)
    rate = df["readmit_30d"].mean()
    assert 0.05 < rate < 0.30, f"Base rate {rate:.4f} outside [0.05, 0.30]"


# ── Test: model exists ────────────────────────────────────────────────────
def test_model_exists():
    assert MODEL.exists(), f"{MODEL} not found — run src/train.py first"


# ── Test: model loads and predicts ────────────────────────────────────────
@pytest.mark.skipif(not MODEL_AVAILABLE, reason="model not available")
def test_model_loads_and_predicts():
    model = joblib.load(MODEL)
    feature_names = model.feature_name_
    # Build one dummy row matching the feature schema
    dummy = {col: 0 for col in feature_names}
    dummy["age"] = 75
    dummy["sex"] = 1
    dummy["race"] = 1
    dummy["length_of_stay"] = 5
    dummy["diagnosis_count"] = 3
    dummy["prior_admissions"] = 0
    X = pd.DataFrame([dummy])
    pred = model.predict(X)
    assert len(pred) == 1, f"Expected prediction array of length 1, got {len(pred)}"


# ── Test: no duplicate admissions ─────────────────────────────────────────
@pytest.mark.skipif(not DATA_AVAILABLE, reason="data not available")
def test_no_duplicate_admissions():
    df = pd.read_parquet(PARQUET)
    dupes = df.duplicated(subset=["beneficiary_id", "claim_id"]).sum()
    assert dupes == 0, f"{dupes} duplicate (beneficiary_id, claim_id) pairs found"
