# ---
# jupytext:
#   text_representation:
#     extension: .py
#     format_name: percent
# ---
"""02_evaluation.ipynb — Model evaluation and SHAP interpretability.

Loads test predictions, trained model, and features.
Produces: ROC curve, PR curve, confusion matrix, classification report,
SHAP summary + bar plots.
"""

# %%
import pathlib
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve, average_precision_score,
    confusion_matrix, classification_report
)
import shap

PROJ = next(p for p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents] if (p / "requirements.txt").exists())
OUTDIR = PROJ / "notebooks"

# %% [markdown]
# ## 1. Load test predictions

# %%
preds = pd.read_csv(PROJ / "data" / "interim" / "test_predictions.csv")
print(f"Predictions: {preds.shape}")
print(preds.head())

# %% [markdown]
# ## 2. Load trained model

# %%
model = joblib.load(PROJ / "models" / "model.joblib")
print(f"Model type: {type(model).__name__}")
print(f"Model features ({len(model.feature_name_)}): {model.feature_name_}")

# %% [markdown]
# ## 3. Load features for column names

# %%
features_df = pd.read_parquet(PROJ / "data" / "interim" / "features.parquet")
drop_cols = {"claim_id", "beneficiary_id", "readmit_30d"}
feature_names = [c for c in features_df.columns if c not in drop_cols]
print(f"Feature columns ({len(feature_names)}): {feature_names}")

# %% [markdown]
# ## 4. ROC Curve

# %%
fpr, tpr, thresholds = roc_curve(preds["y_true"], preds["y_prob"])
roc_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=(6, 5))
ax.plot(fpr, tpr, color="#4a90d9", lw=2, label=f"AUC-ROC = {roc_auc:.4f}")
ax.plot([0, 1], [0, 1], color="#999", lw=1, linestyle="--", label="Random")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("Receiver Operating Characteristic (ROC) Curve")
ax.legend(loc="lower right")
plt.tight_layout()
fig.savefig(OUTDIR / "roc_curve.png", dpi=150)
plt.close(fig)
print(f"✓ ROC curve saved. AUC = {roc_auc:.4f}")

# %% [markdown]
# ## 5. Precision-Recall Curve

# %%
precision, recall, pr_thresholds = precision_recall_curve(preds["y_true"], preds["y_prob"])
avg_precision = average_precision_score(preds["y_true"], preds["y_prob"])

fig, ax = plt.subplots(figsize=(6, 5))
ax.plot(recall, precision, color="#e8553a", lw=2, label=f"AP = {avg_precision:.4f}")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Precision-Recall Curve")
ax.legend(loc="lower left")
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])
plt.tight_layout()
fig.savefig(OUTDIR / "pr_curve.png", dpi=150)
plt.close(fig)
print(f"✓ PR curve saved. Average Precision = {avg_precision:.4f}")

# %% [markdown]
# ## 6. Confusion Matrix

# %%
cm = confusion_matrix(preds["y_true"], preds["y_pred"])
fig, ax = plt.subplots(figsize=(5, 4))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
            xticklabels=["No Readmit (0)", "Readmit (1)"],
            yticklabels=["No Readmit (0)", "Readmit (1)"])
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title("Confusion Matrix")
plt.tight_layout()
fig.savefig(OUTDIR / "confusion_matrix.png", dpi=150)
plt.close(fig)
print(f"✓ Confusion matrix saved.\nTN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}")

# %% [markdown]
# ## 7. Classification Report

# %%
report = classification_report(preds["y_true"], preds["y_pred"])
print(report)

# %% [markdown]
# ## 8. SHAP Interpretability

# %%
# Build a sample DataFrame for SHAP using the feature columns
# Reconstruct test features from predictions by loading features.parquet
# and matching the test split (reproducible with same random_state)
from sklearn.model_selection import train_test_split
X = features_df[feature_names]
y = features_df["readmit_30d"]
_, X_test, _, _ = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

# Sample 500 rows for SHAP
X_sample = X_test.sample(n=min(500, len(X_test)), random_state=42)
print(f"SHAP sample size: {len(X_sample)}")

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_sample)

# Summary plot (beeswarm)
shap.summary_plot(shap_values, X_sample, show=False, max_display=12)
plt.tight_layout()
plt.savefig(OUTDIR / "shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ SHAP summary (beeswarm) saved")

# Bar chart of mean |SHAP|
shap.plots.bar(shap.Explanation(values=shap_values, data=X_sample, feature_names=feature_names),
               show=False, max_display=12)
plt.tight_layout()
plt.savefig(OUTDIR / "shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ SHAP bar chart saved")

# %% [markdown]
# ## 9. SHAP Interpretation
#
# The SHAP analysis reveals the top 3 features driving readmission predictions:
#
# 1. **length_of_stay**: Longer hospital stays generally increase readmission risk. Patients with extended stays (especially >7 days) tend to have more complex conditions that warrant follow-up care.
#
# 2. **chronic_chf (Congestive Heart Failure)**: Patients with CHF have a significantly higher risk of 30-day readmission, which aligns with clinical literature showing heart failure readmissions are among the most common.
#
# 3. **prior_admissions**: Patients with a history of multiple prior admissions are at elevated risk, reflecting a pattern of chronic care needs and system utilization.
#
# These findings are clinically plausible and consistent with known readmission risk factors, lending credibility to the model's learned patterns.

print("\n✓ Evaluation notebook complete. All figures saved to notebooks/")
