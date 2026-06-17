# ---
# jupytext:
#   text_representation:
#     extension: .py
#     format_name: percent
# ---
"""01_eda.ipynb — Exploratory Data Analysis for CMS Readmission Predictor.

Covers:
- Dataset shape & readmit_30d distribution
- Age distribution
- Chronic-condition prevalence
- Length-of-stay distribution
- Missingness summary
"""

# %%
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# %%
# Resolve project root (works both in .py script and .ipynb)
NOTEBOOK_DIR = pathlib.Path("/home/node/.openclaw/projects/cms-readmission-predictor/notebooks")
PROJ = NOTEBOOK_DIR.parent
PARQUET = PROJ / "data" / "interim" / "features.parquet"
OUTDIR  = NOTEBOOK_DIR

df = pd.read_parquet(PARQUET)
print(f"Dataset shape: {df.shape}")

# %% [markdown]
# ## Dataset Shape

# %%
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
df.info()

# %% [markdown]
# ## Readmission Distribution

# %%
rate = df["readmit_30d"].mean()
counts = df["readmit_30d"].value_counts().sort_index()
print(f"\nreadmit_30d distribution:")
for k, v in counts.items():
    print(f"  {k}: {v:>8,}  ({v/len(df):.2%})")
print(f"\nBase rate: {rate:.4f} ({rate:.2%})")

fig, ax = plt.subplots(figsize=(5, 3))
counts.plot(kind="bar", ax=ax, color=["#4a90d9", "#e8553a"])
ax.set_xticklabels(["No Readmission", "Readmitted ≤30d"], rotation=0)
ax.set_ylabel("Count")
ax.set_title("30-Day Readmission Distribution")
for bar, v in zip(ax.patches, counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30,
            f"{v:,}\n({v/len(df):.2%})", ha="center", va="bottom", fontsize=9)
plt.tight_layout()
fig.savefig(OUTDIR / "eda_readmit_dist.png", dpi=150)
plt.close(fig)

# %% [markdown]
# ## Age Distribution

# %%
age = df["age"].dropna()
print(f"\nAge stats (n={len(age):,}):")
print(age.describe().to_string())

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
sns.histplot(age, bins=40, kde=True, ax=axes[0], color="#4a90d9")
axes[0].set_title("Age Distribution")
axes[0].set_xlabel("Age (years)")
sns.boxplot(x=age, ax=axes[1], color="#4a90d9")
axes[1].set_title("Age Box Plot")
axes[1].set_xlabel("Age (years)")
plt.tight_layout()
fig.savefig(OUTDIR / "eda_age_dist.png", dpi=150)
plt.close(fig)

# %% [markdown]
# ## Chronic Condition Prevalence

# %%
chronic_cols = [c for c in df.columns if c.startswith("chronic_")]
chronic_rates = df[chronic_cols].mean().sort_values(ascending=False)
print("\nChronic condition prevalence:")
for col, rate_ in chronic_rates.items():
    label = col.replace("chronic_", "").replace("_", " ").title()
    print(f"  {label}: {rate_:.2%}")

fig, ax = plt.subplots(figsize=(7, 5))
chronic_rates.plot(kind="barh", ax=ax, color="#e8553a")
ax.set_xlabel("Prevalence")
ax.set_title("Chronic Condition Prevalence")
ax.set_xlim(0, chronic_rates.max() + 0.05)
for i, v in enumerate(chronic_rates.values):
    ax.text(v + 0.005, i, f"{v:.1%}", va="center", fontsize=9)
plt.tight_layout()
fig.savefig(OUTDIR / "eda_chronic_prev.png", dpi=150)
plt.close(fig)

# %% [markdown]
# ## Length of Stay Distribution

# %%
los = df["length_of_stay"]
print(f"\nLength of stay stats:")
print(los.describe().to_string())

fig, ax = plt.subplots(figsize=(6, 4))
sns.histplot(los, bins=50, kde=True, ax=ax, color="#2ca02c")
ax.set_title("Length of Stay Distribution")
ax.set_xlabel("Days")
ax.set_ylabel("Count")
plt.tight_layout()
fig.savefig(OUTDIR / "eda_los_dist.png", dpi=150)
plt.close(fig)

# %% [markdown]
# ## Missingness Summary

# %%
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
missing_df = pd.DataFrame({"nulls": missing, "pct": missing_pct})
missing_df = missing_df[missing_df["nulls"] > 0].sort_values("nulls", ascending=False)
print("\nMissingness summary:")
if len(missing_df) == 0:
    print("  No missing values — clean dataset ✓")
else:
    print(missing_df.to_string())

fig, ax = plt.subplots(figsize=(8, 4))
if len(missing_df) > 0:
    missing_df["pct"].plot(kind="barh", ax=ax, color="#888888")
    ax.set_xlabel("Missing %")
    ax.set_title("Missingness by Column")
else:
    ax.barh(["All Complete"], [1], color="#2ca02c")
    ax.set_xlim(0, 1.1)
    ax.set_title("No Missing Values")
plt.tight_layout()
fig.savefig(OUTDIR / "eda_missing.png", dpi=150)
plt.close(fig)

# %% [markdown]
# ## Diagnosis Count & Prior Admissions

# %%
print(f"\nDiagnosis count stats:")
print(df["diagnosis_count"].describe().to_string())
print(f"\nPrior admissions stats:")
print(df["prior_admissions"].describe().to_string())

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
sns.countplot(x="diagnosis_count", data=df, ax=axes[0], color="#4a90d9")
axes[0].set_title("Diagnosis Code Count per Admission")
axes[0].set_xlabel("Number of ICD-9 Diagnosis Codes")
sns.histplot(df["prior_admissions"].clip(0, 10), bins=11, kde=False, ax=axes[1], color="#2ca02c")
axes[1].set_title("Prior Admissions Distribution (clipped to 10)")
axes[1].set_xlabel("Number of Prior Admissions")
plt.tight_layout()
fig.savefig(OUTDIR / "eda_diag_prior.png", dpi=150)
plt.close(fig)

print("\n✓ EDA complete. All figures saved to notebooks/")
