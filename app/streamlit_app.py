#!/usr/bin/env python
"""Streamlit app — 30-Day Readmission Risk Predictor.

A portfolio demo using the CMS DE-SynPUF synthetic dataset.
NOT for clinical decision-making.
"""

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Readmission Risk Predictor",
    page_icon="🏥",
    layout="centered",
)

# ── Load model at startup ──────────────────────────────────────────────────
@st.cache_resource
def load_model():
    return joblib.load("models/model.joblib")

model = load_model()
FEATURE_NAMES = model.feature_name_

# ── Sidebar inputs ─────────────────────────────────────────────────────────
st.sidebar.header("Patient Features")

age = st.sidebar.number_input("Age", min_value=18, max_value=110, value=75, step=1)

sex = st.sidebar.selectbox("Sex", options=[1, 2], index=0, format_func=lambda x: "Male" if x == 1 else "Female")

race = st.sidebar.selectbox(
    "Race",
    options=[1, 2, 3, 5],
    index=0,
    format_func=lambda x: {1: "White", 2: "Black", 3: "Other", 5: "Hispanic"}.get(x, "Unknown"),
)

length_of_stay = st.sidebar.number_input("Length of Stay (days)", min_value=1, max_value=60, value=5, step=1)

diagnosis_count = st.sidebar.slider("Number of Diagnosis Codes", min_value=1, max_value=10, value=3, step=1)

prior_admissions = st.sidebar.number_input("Prior Admissions", min_value=0, max_value=20, value=0, step=1)

CHRONIC_LABELS = {
    "chronic_alzhdmta":   "Alzheimer's / Dementia",
    "chronic_chf":        "Congestive Heart Failure",
    "chronic_chrnkidn":   "Chronic Kidney Disease",
    "chronic_cncr":       "Cancer",
    "chronic_copd":       "COPD",
    "chronic_depressn":   "Depression",
    "chronic_diabetes":    "Diabetes",
    "chronic_ischmcht":   "Ischemic Heart Disease",
    "chronic_osteoprs":   "Osteoporosis",
    "chronic_ra_oa":      "Rheumatoid Arthritis / OA",
    "chronic_strketia":   "Stroke / TIA",
}

st.sidebar.subheader("Chronic Conditions")
chronic_vals = {}
for col, label in CHRONIC_LABELS.items():
    chronic_vals[col] = 1 if st.sidebar.checkbox(label, value=False) else 0

# ── Build input vector ────────────────────────────────────────────────────
input_data = pd.DataFrame([{
    "age": age,
    "sex": sex,
    "race": race,
    "length_of_stay": length_of_stay,
    "diagnosis_count": diagnosis_count,
    "prior_admissions": prior_admissions,
    **chronic_vals,
}])

# Ensure column order matches model
input_data = input_data[FEATURE_NAMES]

# ── Predict ────────────────────────────────────────────────────────────────
prob = model.predict_proba(input_data)[0][1]
pred = model.predict(input_data)[0]

# ═══ Main panel ═════════════════════════════════════════════════════════
st.title("🏥 30-Day Readmission Risk Predictor")
st.markdown("*Using a LightGBM model trained on CMS DE-SynPUF synthetic data*")

# Risk color + label
if prob < 0.15:
    color = "green"
    level = "Low"
    emoji = "🟢"
elif prob < 0.30:
    color = "orange"
    level = "Medium"
    emoji = "🟡"
else:
    color = "red"
    level = "High"
    emoji = "🔴"

st.metric(
    label="Readmission Probability",
    value=f"{prob:.1%}",
    delta=None,
)
st.markdown(f"<h3 style='color:{color}'>{emoji} Risk Level: {level}</h3>", unsafe_allow_html=True)

# ── Waterfall plot ────────────────────────────────────────────────────────
st.subheader("SHAP Explanation")
explainer = shap.TreeExplainer(model)
shap_vals = explainer.shap_values(input_data)

# Handle LightGBM binary classifier SHAP output (list of 2 arrays or single array)
if isinstance(shap_vals, list):
    sv_class1 = shap_vals[1][0]      # class-1 SHAP values for first row
    base_val = explainer.expected_value[1] if hasattr(explainer.expected_value, '__len__') else explainer.expected_value
else:
    sv_class1 = shap_vals[0]
    base_val = explainer.expected_value

fig_waterfall = shap.plots.waterfall(
    shap.Explanation(values=sv_class1, base_values=base_val, data=input_data.iloc[0], feature_names=FEATURE_NAMES),
    show=False
)
fig_waterfall.tight_layout()
st.pyplot(fig_waterfall)

# ── About expander ────────────────────────────────────────────────────────
with st.expander("ℹ️ About this project"):
    st.markdown("""
### What does this predict?
This app estimates the probability that a Medicare patient will be readmitted to the hospital
within 30 days of being discharged from an inpatient stay.

### What data was it trained on?
The model was trained on the **CMS DE-SynPUF** (Data Entrepreneurs' Synthetic Public Use File) —
a 5% sample of 2008-2010 Medicare claims data that has been de-identified and synthetically
perturbed to protect beneficiary privacy. It contains ~116,000 beneficiaries and ~67,000
inpatient admissions.

### Disclaimer
⚠️ **This is a portfolio project built on synthetic data. It is NOT intended for clinical
decision-making, patient care, or any medical purpose.** All data is synthetically generated
by CMS and does not represent real patients.

### Model details
- **Algorithm:** LightGBM (gradient boosted trees)
- **Features:** 16 (age, sex, race, length of stay, diagnosis count, prior admissions, 11 chronic conditions)
- **AUC-ROC on test set:** ~0.67
- **Training data:** 53,417 admissions, **Test data:** 13,355 admissions
""")
