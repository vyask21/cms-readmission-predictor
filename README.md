# CMS Readmission Predictor

Predicts 30-day unplanned hospital readmission from Medicare inpatient claims, and shows
which patient factors drove each prediction.

Interactive demo: [huggingface.co/spaces/vyask21/cms-readmission-predictor](https://huggingface.co/spaces/vyask21/cms-readmission-predictor)

## Background

The CMS Hospital Readmissions Reduction Program penalizes hospitals for excess 30-day
readmissions, so knowing which discharges carry risk has direct operational value. The
modeling problem has two properties that shape everything here: the positive class is rare,
about one discharge in ten, and the features available at discharge are administrative
rather than clinical.

Both make a single accuracy number misleading. A model that predicts "no readmission" for
every patient is right 90 percent of the time and useless, so the results below are
reported against the base rate rather than against chance.

## Data

CMS Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF), Sample 1. Synthetic claims
derived from real Medicare data, released publicly with no data use agreement.

- **Beneficiary summary:** [DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip](https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip)
- **Inpatient claims:** [DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.zip](https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.zip)
- **Codebook:** [de-10-codebook.pdf](https://www.cms.gov/files/document/de-10-codebook.pdf-0), summarized for this project in [data/CODEBOOK.md](data/CODEBOOK.md)
- **Cohort:** 66,772 inpatient admissions, 2008-2010
- **Outcome:** 6,767 admissions (10.13%) followed by another admission within 30 days of discharge

Because the data is synthetic, the associations in it are weaker and cleaner than in real
claims. The pipeline is the deliverable here, not the clinical finding.

## Methods

**ETL.** DuckDB performs the joins and window functions out of core, reading the two raw
CSVs directly. An admission is labeled `readmit_30d = 1` when the same beneficiary has a
later admission whose admit date falls within 30 days of this admission's discharge date.
Admissions are keyed on a composite of claim id, date and row number, which resolves 68
duplicate claim ids in the source file.

**Leakage ban.** Features contain only information known at the moment of discharge.
`CLM_PMT_AMT` and every other payment column are excluded, as is any field describing a
future admission. Two of the seven tests exist to enforce this.

**Model.** LightGBM on 17 features: age, sex, race, length of stay, diagnosis count, prior
admission count, and 11 chronic condition flags. Three features carry monotonic constraints
so the fitted function cannot invert a relationship that is not clinically arguable: more
prior admissions, greater age and longer stay may only push risk up.

Stratified 80/20 split with a fixed seed. Parameters, metrics and the model artifact are
logged to MLflow using a local file store, so a run is reproducible without a server.

**Interpretability.** SHAP TreeExplainer over a 500-admission sample produces both the
global ranking and the per-patient waterfall shown in the demo.

## Results

Held-out test set: 13,355 admissions, 1,353 of them readmissions.

| Metric | Value | Reference |
|---|---|---|
| AUC-ROC | 0.665 | 0.5 is chance |
| Average precision | 0.173 | 0.101 is the base rate |
| Recall, positive class | 0.65 | |
| Precision, positive class | 0.16 | |

At the default 0.5 threshold the model finds 879 of 1,353 readmissions and misses 474, at
the cost of 4,776 false positives. That trade is the honest shape of the problem: catching
two thirds of readmissions on administrative features alone means flagging a large number
of patients who will not return.

Average precision of 0.173 against a 0.101 base rate is a 1.7x lift, so the ranking carries
real signal. An AUC of 0.665 is modest in absolute terms, and expected: discharge-time
administrative data does not contain the clinical detail that drives readmission, and the
synthetic source weakens what association exists. A model reporting 0.85 on this data would
be evidence of leakage, not of skill.

Chronic kidney disease, COPD and congestive heart failure rank among the strongest
contributors in the SHAP ranking ([notebooks/shap_bar.png](notebooks/shap_bar.png)), which
matches the conditions the CMS readmissions program targets.

## Repository Structure

```
cms-readmission-predictor/
├── data/
│   ├── CODEBOOK.md        # column definitions, read by the ETL
│   ├── raw/               # downloaded CSVs (not committed)
│   └── interim/           # features.parquet, test_predictions.csv
├── src/
│   ├── etl.py             # DuckDB ETL and 30-day readmission labeling
│   └── train.py           # LightGBM training, monotonic constraints, MLflow logging
├── notebooks/
│   ├── 01_eda.py          # cohort, base rate, chronic prevalence, missingness
│   ├── 02_evaluation.py   # ROC, PR, confusion matrix, SHAP
│   ├── *.html             # executed notebook output
│   └── *.png              # figures used above and in the demo
├── app/
│   └── streamlit_app.py   # risk score plus per-patient SHAP waterfall
├── tests/
│   └── test_pipeline.py   # 7 tests: leakage, identifiers, base rate, duplicates, model
├── models/
│   └── model.joblib       # fitted LightGBM classifier
└── requirements.txt       # pinned dependencies
```

## How to Reproduce

```bash
# 1. Clone and enter the project
git clone https://github.com/vyask21/cms-readmission-predictor.git
cd cms-readmission-predictor

# 2. Set up the virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Download the two DE-SynPUF archives listed under Data, unzip into data/raw/

# 4. Build features (writes data/interim/features.parquet)
python src/etl.py

# 5. Train (writes models/model.joblib and data/interim/test_predictions.csv)
python src/train.py

# 6. Check the pipeline
pytest tests/

# 7. Run the notebooks
jupytext --to notebook notebooks/01_eda.py -o notebooks/01_eda.ipynb
jupyter nbconvert --to html --execute notebooks/01_eda.ipynb
jupytext --to notebook notebooks/02_evaluation.py -o notebooks/02_evaluation.ipynb
jupyter nbconvert --to html --execute notebooks/02_evaluation.ipynb

# 8. Run the demo locally
streamlit run app/streamlit_app.py
```

The split and the model both use a fixed seed (42), so the reported metrics reproduce
exactly.

## References

- Centers for Medicare & Medicaid Services. CMS 2008-2010 Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF). https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files
- Centers for Medicare & Medicaid Services. Hospital Readmissions Reduction Program (HRRP). https://www.cms.gov/medicare/payment/prospective-payment-systems/acute-inpatient-pps/hospital-readmissions-reduction-program-hrrp
- Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems*, 30.
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30.

## License

MIT. See [LICENSE](LICENSE).
