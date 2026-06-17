# DE-SynPUF Codebook — Inpatient Claims & Beneficiary Summary (2008-2010)

Source: CMS 2008-2010 Data Entrepreneurs Synthetic Public Use File (DE-SynPUF) — DE 1.0 Sample 1
Codebook: <https://www.cms.gov/files/document/de-10-codebook.pdf-0>
Sample page: <https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf/de10-sample-1>

## Verified Download URLs (curl -I -L confirmed HTTP 200)

### DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip
**URL:** `https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/de1_0_2008_beneficiary_summary_file_sample_1.zip`
**Status: HTTP 200 ✓**

### DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.zip
**URL:** `https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/de1_0_2008_to_2010_inpatient_claims_sample_1.zip`
**Status: HTTP 200 ✓**

## File Format

All sample files are comma-delimited CSVs. Field delimiters are commas; text fields are not quoted.

---

## Inpatient Claims — Key Columns

| Column Name | Data Type | Format / Notes |
|---|---|---|
| `DESYNPUF_ID` | String | De-identified beneficiary ID (unique within sample) |
| `CLM_ID` | String | Unique claim ID for this inpatient claim |
| `CLM_ADMSN_DT` | Date | Claim admission date, format: **YYYYMMDD** |
| `NCH_BENE_DSCHRG_DT` | Date | Beneficiary discharge date, format: **YYYYMMDD** |
| `CLM_UTLZTN_DAY_CNT` | Integer | Length of inpatient stay in days (utilization day count) |
| `ICD9_DGNS_CD_1` | String | ICD-9-CM Principal diagnosis code (e.g. "41071") |
| `ICD9_DGNS_CD_2` | String | ICD-9-CM Secondary diagnosis code 1 |
| `ICD9_DGNS_CD_3` | String | ICD-9-CM Secondary diagnosis code 2 |
| `ICD9_DGNS_CD_4` | String | ICD-9-CM Secondary diagnosis code 3 |
| `ICD9_DGNS_CD_5` | String | ICD-9-CM Secondary diagnosis code 4 |
| `ICD9_DGNS_CD_6` | String | ICD-9-CM Secondary diagnosis code 5 |
| `ICD9_DGNS_CD_7` | String | ICD-9-CM Secondary diagnosis code 6 |
| `ICD9_DGNS_CD_8` | String | ICD-9-CM Secondary diagnosis code 7 |
| `ICD9_DGNS_CD_9` | String | ICD-9-CM Secondary diagnosis code 8 |
| `ICD9_DGNS_CD_10` | String | ICD-9-CM Secondary diagnosis code 9 |
| `CLM_PMT_AMT` | Float | Total claim payment amount (in dollars; not used as feature) |

**Notes on ICD-9 codes:** Columns `ICD9_DGNS_CD_1` through `ICD9_DGNS_CD_10` contain ICD-9-CM diagnosis codes. Not all 10 may be populated for every claim. Codes are string/character type, varying length.

**Notes on dates:** All date fields (`CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT`, etc.) are stored as 8-character strings in YYYYMMDD format.

---

## Beneficiary Summary — Key Columns

### Identifier & Demographics

| Column Name | Data Type | Format / Notes |
|---|---|---|
| `DESYNPUF_ID` | String | De-identified beneficiary ID (unique within sample) |
| `BENE_BIRTH_DT` | Date | Beneficiary date of birth, format: **YYYYMMDD** |
| `BENE_DEATH_DT` | Date | Beneficiary date of death, format: **YYYYMMDD** (blank if alive) |
| `BENE_SEX_IDENT_CD` | Integer | 1 = Male, 2 = Female |
| `BENE_RACE_CD` | Integer | 1 = White, 2 = Black, 3 = Asian, 4 = Other, 5 = Hispanic, 6 = Unknown |

### Chronic-Condition Flags (11 fields)

**Encoding: `1` = Has the condition (Yes), `2` = Does not have the condition (No)**

| Column Name | Condition |
|---|---|
| `SP_ALZHDMTA` | Alzheimer's Disease or Related Dementia |
| `SP_CHF` | Congestive Heart Failure |
| `SP_CHRNKIDN` | Chronic Kidney Disease |
| `SP_CNCR` | Cancer |
| `SP_COPD` | Chronic Obstructive Pulmonary Disease |
| `SP_DEPRESSN` | Depression |
| `SP_DIABETES` | Diabetes |
| `SP_ISCHMCHT` | Ischemic Heart Disease |
| `SP_OSTEOPRS` | Osteoporosis |
| `SP_RA_OA` | Rheumatoid Arthritis / Osteoarthritis |
| `SP_STRKETIA` | Stroke / Transient Ischemic Attack (TIA) |

**Notes on chronic conditions:** These are 25-month flags derived from claims data. Recoding `1→1, 2→0` converts them into binary 0/1 flag variables. Values should exist for each beneficiary in each year they appear in the beneficiary summary file.
