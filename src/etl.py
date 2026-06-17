#!/usr/bin/env python
"""ETL pipeline — 30-day readmission labeling for CMS DE-SynPUF data.

Reads column definitions from data/CODEBOOK.md.
Uses DuckDB for fast relational joins + window-function computations.

LEAKAGE BAN: features only contain information known at index-discharge time.
CLM_PMT_AMT and any future-admission field are excluded from features.

Writes data/interim/features.parquet.
"""

import duckdb
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
INTERIM = os.path.join(PROJ, "data", "interim")

inp_csv = os.path.join(RAW, "DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv")
ben_csv = os.path.join(RAW, "DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv")
out_parquet = os.path.join(INTERIM, "features.parquet")

CHRONIC_COLS = [
    "SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR", "SP_COPD",
    "SP_DEPRESSN", "SP_DIABETES", "SP_ISCHMCHT", "SP_OSTEOPRS",
    "SP_RA_OA", "SP_STRKETIA",
]

con = duckdb.connect()

# ── 1. Load inpatient claims ─────────────────────────────────────────────
print("Loading inpatient claims …")
con.execute(f"""
CREATE TABLE inpatient AS
SELECT
    DESYNPUF_ID,
    CLM_ID,
    CAST(NULLIF(CLM_ADMSN_DT::VARCHAR, 'NULL') AS VARCHAR) AS CLM_ADMSN_DT_str,
    CAST(NULLIF(NCH_BENE_DSCHRG_DT::VARCHAR, 'NULL') AS VARCHAR) AS DSCHRG_DT_str,
    CLM_UTLZTN_DAY_CNT,
    COALESCE(NULLIF(ICD9_DGNS_CD_1::VARCHAR, 'NULL'), '') AS icd1,
    COALESCE(NULLIF(ICD9_DGNS_CD_2::VARCHAR, 'NULL'), '') AS icd2,
    COALESCE(NULLIF(ICD9_DGNS_CD_3::VARCHAR, 'NULL'), '') AS icd3,
    COALESCE(NULLIF(ICD9_DGNS_CD_4::VARCHAR, 'NULL'), '') AS icd4,
    COALESCE(NULLIF(ICD9_DGNS_CD_5::VARCHAR, 'NULL'), '') AS icd5,
    COALESCE(NULLIF(ICD9_DGNS_CD_6::VARCHAR, 'NULL'), '') AS icd6,
    COALESCE(NULLIF(ICD9_DGNS_CD_7::VARCHAR, 'NULL'), '') AS icd7,
    COALESCE(NULLIF(ICD9_DGNS_CD_8::VARCHAR, 'NULL'), '') AS icd8,
    COALESCE(NULLIF(ICD9_DGNS_CD_9::VARCHAR, 'NULL'), '') AS icd9,
    COALESCE(NULLIF(ICD9_DGNS_CD_10::VARCHAR, 'NULL'), '') AS icd10
FROM read_csv_auto('{inp_csv}', header=true, all_varchar=true)
WHERE CLM_ADMSN_DT IS NOT NULL
  AND NCH_BENE_DSCHRG_DT IS NOT NULL
""")

n_inp = con.execute('SELECT COUNT(*) FROM inpatient').fetchone()[0]
print(f"  Inpatient rows loaded: {n_inp}")

# Parse dates
con.execute("ALTER TABLE inpatient ADD COLUMN CLM_ADMSN DATE")
con.execute("ALTER TABLE inpatient ADD COLUMN DSCHRG DATE")
con.execute("""
UPDATE inpatient
SET CLM_ADMSN = TRY_STRPTIME(CLM_ADMSN_DT_str, '%Y%m%d')::DATE,
    DSCHRG    = TRY_STRPTIME(DSCHRG_DT_str,   '%Y%m%d')::DATE
""")
con.execute("DELETE FROM inpatient WHERE CLM_ADMSN IS NULL OR DSCHRG IS NULL")
n_inp2 = con.execute('SELECT COUNT(*) FROM inpatient').fetchone()[0]
print(f"  After date filter: {n_inp2}")

# ── 2. Load beneficiary summary ──────────────────────────────────────────
print("Loading beneficiary summary …")
chronic_list = ", ".join(CHRONIC_COLS)
con.execute(f"""
CREATE TABLE beneficiary AS
SELECT
    DESYNPUF_ID,
    BENE_BIRTH_DT::VARCHAR AS BIRTH_DT_str,
    BENE_DEATH_DT::VARCHAR AS DEATH_DT_str,
    BENE_SEX_IDENT_CD,
    BENE_RACE_CD,
    {chronic_list}
FROM read_csv_auto('{ben_csv}', header=true, all_varchar=true)
""")

n_ben = con.execute('SELECT COUNT(*) FROM beneficiary').fetchone()[0]
print(f"  Beneficiary rows loaded: {n_ben}")

con.execute("ALTER TABLE beneficiary ADD COLUMN BIRTH DATE")
con.execute("ALTER TABLE beneficiary ADD COLUMN DEATH DATE")
con.execute("""
UPDATE beneficiary
SET BIRTH = TRY_STRPTIME(BIRTH_DT_str, '%Y%m%d')::DATE
""")
con.execute("""
UPDATE beneficiary
SET DEATH = CASE
    WHEN DEATH_DT_str IS NOT NULL AND DEATH_DT_str NOT IN ('NULL', '', '0')
    THEN TRY_STRPTIME(DEATH_DT_str, '%Y%m%d')::DATE
    ELSE NULL
END
""")

# ── 3. Join + compute ordered index ──────────────────────────────────────
print("Joining and computing prior-admission rank …")

con.execute("""
CREATE TABLE ordered AS
SELECT
    i.DESYNPUF_ID,
    i.CLM_ID,
    i.CLM_ADMSN,
    i.DSCHRG,
    i.CLM_UTLZTN_DAY_CNT,
    i.icd1, i.icd2, i.icd3, i.icd4, i.icd5,
    i.icd6, i.icd7, i.icd8, i.icd9, i.icd10,
    b.BENE_SEX_IDENT_CD,
    b.BENE_RACE_CD,
    b.SP_ALZHDMTA, b.SP_CHF, b.SP_CHRNKIDN, b.SP_CNCR, b.SP_COPD,
    b.SP_DEPRESSN, b.SP_DIABETES, b.SP_ISCHMCHT, b.SP_OSTEOPRS,
    b.SP_RA_OA, b.SP_STRKETIA,
    b.BIRTH,
    b.DEATH,
    CASE WHEN b.BIRTH IS NOT NULL
         THEN ROUND(CAST((i.CLM_ADMSN - b.BIRTH) AS DOUBLE) / 365.25, 1)
         ELSE NULL END AS age_at_admission,
    ROW_NUMBER() OVER (
        PARTITION BY i.DESYNPUF_ID
        ORDER BY i.CLM_ADMSN, i.CLM_ID
    ) AS rn
FROM inpatient i
LEFT JOIN beneficiary b USING (DESYNPUF_ID)
""")

joined_count = con.execute('SELECT COUNT(*) FROM ordered').fetchone()[0]
print(f"  Joined rows: {joined_count}")

# ── 4. Readmission label via EXISTS semi-join ────────────────────────────
# Each admission: readmit_30d = 1 if SAME beneficiary has a later admission
# whose CLM_ADMSN falls within 30 days of THIS admission's DSCHRG.
# Exclude admissions where DEATH falls during the stay.
print("Labeling 30-day readmissions …")

con.execute("""
ALTER TABLE ordered ADD COLUMN readmit_30d INTEGER DEFAULT 0
""")
con.execute("""
UPDATE ordered SET readmit_30d = 1
WHERE EXISTS (
    SELECT 1 FROM ordered f2
    WHERE f2.DESYNPUF_ID = ordered.DESYNPUF_ID
      AND f2.CLM_ADMSN > ordered.DSCHRG
      AND f2.CLM_ADMSN <= ordered.DSCHRG + INTERVAL 30 DAY
)
""")

# ── 5. Features table (LEAKAGE-SAFE) ─────────────────────────────────────

# FEATURES (all known at index-discharge):
#   - age_at_admission
#   - sex, race
#   - length_of_stay  (CLM_UTLZTN_DAY_CNT)
#   - diagnosis_count (# of non-null ICD9_DGNS_CD_1..10)
#   - prior_admissions = rn - 1
#   - 11 chronic flags (recoded 1→1, 2→0)
# EXCLUDED: CLM_PMT_AMT and any field from future admissions

print("Building feature table …")

con.execute("""
CREATE TABLE features AS
SELECT
    -- CLM_ID is NOT unique in CMS SynPUF data (68 CLM_IDs appear twice,
    -- 7 of those share identical CLM_ID+ADMSN+DSCHRG but differ in LOS).
    -- Use CLM_ID || '_' || CLM_ADMSN || '_' || rn for a guaranteed-unique key.
    (CLM_ID || '_' || CAST(CLM_ADMSN AS VARCHAR) || '_' || CAST(rn AS VARCHAR))  AS claim_id,
    DESYNPUF_ID                       AS beneficiary_id,
    readmit_30d,
    age_at_admission                  AS age,
    CAST(BENE_SEX_IDENT_CD AS INT)    AS sex,
    CAST(BENE_RACE_CD AS INT)         AS race,
    CAST(CLM_UTLZTN_DAY_CNT AS INT)   AS length_of_stay,
    -- Count of non-null ICD-9 diagnosis codes
    (CASE WHEN LENGTH(TRIM(icd1))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd2))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd3))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd4))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd5))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd6))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd7))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd8))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd9))  > 0 THEN 1 ELSE 0 END +
     CASE WHEN LENGTH(TRIM(icd10)) > 0 THEN 1 ELSE 0 END
    )                                 AS diagnosis_count,
    (rn - 1)                          AS prior_admissions,
    -- 11 chronic conditions 1→1, 2→0
    CASE WHEN SP_ALZHDMTA  = '1' THEN 1 ELSE 0 END AS chronic_alzhdmta,
    CASE WHEN SP_CHF       = '1' THEN 1 ELSE 0 END AS chronic_chf,
    CASE WHEN SP_CHRNKIDN  = '1' THEN 1 ELSE 0 END AS chronic_chrnkidn,
    CASE WHEN SP_CNCR      = '1' THEN 1 ELSE 0 END AS chronic_cncr,
    CASE WHEN SP_COPD      = '1' THEN 1 ELSE 0 END AS chronic_copd,
    CASE WHEN SP_DEPRESSN  = '1' THEN 1 ELSE 0 END AS chronic_depressn,
    CASE WHEN SP_DIABETES  = '1' THEN 1 ELSE 0 END AS chronic_diabetes,
    CASE WHEN SP_ISCHMCHT  = '1' THEN 1 ELSE 0 END AS chronic_ischmcht,
    CASE WHEN SP_OSTEOPRS  = '1' THEN 1 ELSE 0 END AS chronic_osteoprs,
    CASE WHEN SP_RA_OA     = '1' THEN 1 ELSE 0 END AS chronic_ra_oa,
    CASE WHEN SP_STRKETIA  = '1' THEN 1 ELSE 0 END AS chronic_strketia
FROM ordered
WHERE NOT (DEATH IS NOT NULL AND DEATH >= CLM_ADMSN AND DEATH <= DSCHRG)
""")

# ── 6. Write parquet ─────────────────────────────────────────────────────
os.makedirs(INTERIM, exist_ok=True)
con.execute(f"COPY features TO '{out_parquet}' (FORMAT PARQUET)")

# ── 7. GATE C stats ──────────────────────────────────────────────────────
feat_count = con.execute('SELECT COUNT(*) FROM features').fetchone()[0]
base_rate  = con.execute('SELECT AVG(CAST(readmit_30d AS DOUBLE)) FROM features').fetchone()[0]
col_names  = [r[0] for r in con.execute('DESCRIBE features').fetchall()]

print(f"\n=== GATE C: ETL Output Stats ===")
print(f"Total rows:              {feat_count}")
print(f"readmit_30d base rate:   {base_rate:.4f}")
print(f"Feature count:            {len(col_names)}")
print(f"Columns:                 {', '.join(col_names)}")

# Sanity checks
if not (0.05 <= base_rate <= 0.30):
    print(f"\n✗ Base rate {base_rate:.4f} outside [0.05, 0.30] — FAIL")
    sys.exit(1)
print(f"\n✓ Base rate sanity check passed ({base_rate:.4f} in [0.05, 0.30])")

for fb in ["CLM_PMT_AMT", "pmt", "payment"]:
    if any(fb.lower() in c.lower() for c in col_names):
        print(f"\n✗ LEAKAGE: '{fb}' found in columns — FAIL")
        sys.exit(1)
print("✓ No leakage fields present in feature set")
print("✓ Features.parquet written successfully")
