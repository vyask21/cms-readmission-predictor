# CMS DE-SynPUF Codebook Reference

## Download URLs (Verified with HTTP 200)

### Beneficiary Summary File
- **URL:** https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip
- **HTTP Status:** 200 OK
- **File:** DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip

### Inpatient Claims File
- **URL:** https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.zip
- **HTTP Status:** 200 OK
- **File:** DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.zip

---

## Inpatient Claims Columns (2008-2010)

| Column Name | Description | Format |
|-------------|-------------|--------|
| DESYNPUF_ID | Beneficiary ID | Char(15) |
| CLM_ID | Claim ID | Char(15) |
| CLM_ADMSN_DT | Claim Admission Date | YYYYMMDD |
| NCH_BENE_DSCHRG_DT | Claim Discharge Date | YYYYMMDD |
| CLM_UTLZTN_DAY_CNT | Claim Utilization Day Count | Num |
| ICD9_DGNS_CD_1 | Diagnosis Code 1 (Primary) | Char(5) |
| ICD9_DGNS_CD_2 | Diagnosis Code 2 | Char(5) |
| ICD9_DGNS_CD_3 | Diagnosis Code 3 | Char(5) |
| ICD9_DGNS_CD_4 | Diagnosis Code 4 | Char(5) |
| ICD9_DGNS_CD_5 | Diagnosis Code 5 | Char(5) |
| ICD9_DGNS_CD_6 | Diagnosis Code 6 | Char(5) |
| ICD9_DGNS_CD_7 | Diagnosis Code 7 | Char(5) |
| ICD9_DGNS_CD_8 | Diagnosis Code 8 | Char(5) |
| ICD9_DGNS_CD_9 | Diagnosis Code 9 | Char(5) |
| ICD9_DGNS_CD_10 | Diagnosis Code 10 | Char(5) |
| CLM_PMT_AMT | Claim Payment Amount | Num |

---

## Beneficiary Summary Columns (2008)

| Column Name | Description | Format |
|-------------|-------------|--------|
| DESYNPUF_ID | Beneficiary ID | Char(15) |
| BENE_BIRTH_DT | Beneficiary Birth Date | YYYYMMDD |
| BENE_DEATH_DT | Beneficiary Death Date | YYYYMMDD (empty if alive) |
| BENE_SEX_IDENT_CD | Beneficiary Sex | 1=Male, 2=Female |
| BENE_RACE_CD | Beneficiary Race | 1=White, 2=Black, 3=Other, 5=Hispanic |

### Chronic Condition Flags (SP_*) — 11 Flags

These flags indicate whether the beneficiary had each condition at any point during the year.

| Column Name | Description | Coding |
|-------------|-------------|--------|
| SP_ALZHDMTA | Alzheimer's or Related Disorders or Senile Dementia | 1=Yes, 2=No |
| SP_CHF | Heart Failure | 1=Yes, 2=No |
| SP_CHRNKIDN | Chronic Kidney Disease | 1=Yes, 2=No |
| SP_CNCR | Cancer (Any) | 1=Yes, 2=No |
| SP_COPD | Chronic Obstructive Pulmonary Disease | 1=Yes, 2=No |
| SP_DEPRESSN | Depression | 1=Yes, 2=No |
| SP_DIABETES | Diabetes | 1=Yes, 2=No |
| SP_ISCHMCHT | Ischemic Heart Disease | 1=Yes, 2=No |
| SP_OSTEOPRS | Osteoporosis | 1=Yes, 2=No |
| SP_RA_OA | Rheumatoid Arthritis / Osteoarthritis | 1=Yes, 2=No |
| SP_STRKETIA | Stroke / Transient Ischemic Attack | 1=Yes, 2=No |

---

## Notes

- All dates in CMS DE-SynPUF files use format **YYYYMMDD** (e.g., 20100312 = March 12, 2010)
- Chronic condition flags are time-varying — the same beneficiary may have different values across years (2008, 2009, 2010)
- DESYNPUF_ID links beneficiaries across all files
- CLM_ID uniquely identifies each claim

## Codebook Source

- Codebook PDF: https://www.cms.gov/files/document/de-10-codebook.pdf-0
- (Note: PDF text extraction proved challenging; column definitions verified against actual data files)