#!/usr/bin/env python3
"""
CMS Readmission Pipeline Part 1 - QA Script
Verifies correctness by tracing individual cases.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Project paths
PROJECT_DIR = "/home/node/.openclaw/projects/cms-readmission-predictor"
INPATIENT_CSV = f"{PROJECT_DIR}/data/raw/DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv"
BENEFICIARY_CSV = f"{PROJECT_DIR}/data/raw/DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv"
FEATURES_PARQUET = f"{PROJECT_DIR}/data/interim/features.parquet"
EDA_HTML = f"{PROJECT_DIR}/notebooks/01_eda.html"

# Use venv python
VENV_PYTHON = "/home/node/.openclaw/projects/cms-readmission-predictor/.venv/bin/python"

print("=" * 80)
print("CMS READMISSION PIPELINE PART 1 - QA VERIFICATION")
print("=" * 80)

# ============================================================
# TASK 1: Manual trace, 5 beneficiaries (from RAW CSV)
# ============================================================
print("\n" + "=" * 80)
print("TASK 1: Manual trace, 5 beneficiaries")
print("=" * 80)

# Read raw inpatient CSV
print("\n[Task 1] Reading raw inpatient CSV...")
inpatient_df = pd.read_csv(INPATIENT_CSV)
print(f"  Total rows in inpatient CSV: {len(inpatient_df)}")
print(f"  Columns: {list(inpatient_df.columns)}")

# Find 5 distinct DESYNPUF_IDs with >= 3 admissions
beneficiary_counts = inpatient_df.groupby('DESYNPUF_ID').size()
beneficiaries_3plus = beneficiary_counts[beneficiary_counts >= 3].index.tolist()
print(f"  Beneficiaries with >= 3 admissions: {len(beneficiaries_3plus)}")

# Select 5 distinct beneficiaries
sample_beneficiaries = beneficiaries_3plus[:5]
print(f"  Selected 5 beneficiaries for tracing:")
for bid in sample_beneficiaries:
    print(f"    - {bid} ({beneficiary_counts[bid]} admissions)")

# Parse date function
def parse_date(date_val):
    """Parse date string like '20100312' to datetime"""
    if pd.isna(date_val) or date_val == '' or date_val is None:
        return pd.NaT
    try:
        return pd.to_datetime(str(int(date_val)), format='%Y%m%d')
    except:
        return pd.NaT

# Task 1 results storage
task1_passed = True
task1_failures = []

for beneficiary_id in sample_beneficiaries:
    print(f"\n  --- Beneficiary: {beneficiary_id} ---")
    
    # Get all admissions for this beneficiary, sorted by (CLM_ADMSN_DT, CLM_ID)
    beneficiary_admissions = inpatient_df[inpatient_df['DESYNPUF_ID'] == beneficiary_id].copy()
    beneficiary_admissions['ADMSN_DT'] = beneficiary_admissions['CLM_ADMSN_DT'].apply(parse_date)
    beneficiary_admissions['DSCHRG_DT'] = beneficiary_admissions['NCH_BENE_DSCHRG_DT'].apply(parse_date)
    beneficiary_admissions = beneficiary_admissions.sort_values(['ADMSN_DT', 'CLM_ID']).reset_index(drop=True)
    
    print(f"  Total admissions: {len(beneficiary_admissions)}")
    
    # Calculate manual readmit_30d and prior_admissions
    admissions_list = []
    for i in range(len(beneficiary_admissions)):
        row = beneficiary_admissions.iloc[i]
        admit_date = row['ADMSN_DT']
        discharge_date = row['DSCHRG_DT']
        clm_id = row['CLM_ID']
        
        # prior_admissions_manual = i (0-based index)
        prior_admissions_manual = i
        
        # readmit_30d_manual
        readmit_30d_manual = 0
        if pd.notna(admit_date) and pd.notna(discharge_date):
            window_start = discharge_date + timedelta(days=1)
            window_end = discharge_date + timedelta(days=30)
            
            for j in range(i + 1, len(beneficiary_admissions)):
                later_admit = beneficiary_admissions.iloc[j]['ADMSN_DT']
                if pd.notna(later_admit):
                    if window_start <= later_admit <= window_end:
                        readmit_30d_manual = 1
                        break
        
        admissions_list.append({
            'claim_id': clm_id,
            'admit_date': admit_date,
            'discharge_date': discharge_date,
            'readmit_30d_manual': readmit_30d_manual,
            'prior_admissions_manual': prior_admissions_manual
        })
    
    manual_df = pd.DataFrame(admissions_list)
    print(f"  Manual calculations:")
    print(manual_df[['claim_id', 'readmit_30d_manual', 'prior_admissions_manual']].to_string())
    
    # Query features.parquet
    print(f"  Querying features.parquet...")
    features_df = pd.read_parquet(FEATURES_PARQUET)
    parquet_data = features_df[features_df['beneficiary_id'] == beneficiary_id][['claim_id', 'readmit_30d', 'prior_admissions']]
    parquet_data = parquet_data.sort_values('claim_id').reset_index(drop=True)
    print(f"  Parquet records: {len(parquet_data)}")
    print(f"  Parquet data:")
    print(parquet_data.to_string())
    
    # Ensure claim_id is same type in both dataframes
    manual_df['claim_id'] = manual_df['claim_id'].astype(str)
    parquet_data['claim_id'] = parquet_data['claim_id'].astype(str)
    
    # Compare side-by-side
    # Merge on claim_id
    comparison = manual_df.merge(parquet_data, on='claim_id', how='outer', suffixes=('_manual', '_parquet'))
    
    print(f"  Comparison:")
    print(f"  {'Claim ID':<15} {'Readmit Manual':<16} {'Readmit Parquet':<16} {'Prior Manual':<14} {'Prior Parquet':<14}")
    print(f"  {'-'*75}")
    
    mismatches = []
    for _, row in comparison.iterrows():
        claim_id = row['claim_id']
        readmit_m = row.get('readmit_30d_manual', 'N/A')
        readmit_p = row.get('readmit_30d', 'N/A')
        prior_m = row.get('prior_admissions_manual', 'N/A')
        prior_p = row.get('prior_admissions', 'N/A')
        
        readmit_match = (readmit_m == readmit_p) if readmit_m != 'N/A' and readmit_p != 'N/A' else False
        prior_match = (prior_m == prior_p) if prior_m != 'N/A' and prior_p != 'N/A' else False
        
        if not readmit_match or not prior_match:
            mismatches.append({
                'claim_id': claim_id,
                'readmit_mismatch': not readmit_match,
                'prior_mismatch': not prior_match,
                'readmit_manual': readmit_m,
                'readmit_parquet': readmit_p,
                'prior_manual': prior_m,
                'prior_parquet': prior_p
            })
        
        print(f"  {str(claim_id):<15} {str(readmit_m):<16} {str(readmit_p):<16} {str(prior_m):<14} {str(prior_p):<14}")
    
    if mismatches:
        task1_passed = False
        print(f"  *** MISMATCHES FOUND: {len(mismatches)} ***")
        for m in mismatches:
            print(f"      Claim {m['claim_id']}: readmit_30d manual={m['readmit_manual']} vs parquet={m['readmit_parquet']}, prior_manual={m['prior_manual']} vs parquet={m['prior_parquet']}")
        task1_failures.append(f"Beneficiary {beneficiary_id}: {len(mismatches)} mismatches")

if task1_passed:
    print("\nTASK 1: PASS — All 5 beneficiaries verified correctly")
else:
    print(f"\nTASK 1 FAIL: {task1_failures}")
    print("STOPPING - Task 1 failed.")
    exit(1)

# ============================================================
# TASK 2: Boundary check on prior_admissions
# ============================================================
print("\n" + "=" * 80)
print("TASK 2: Boundary check on prior_admissions")
print("=" * 80)

print("\n[Task 2] Reading features.parquet...")
features_df = pd.read_parquet(FEATURES_PARQUET)
print(f"  Total records: {len(features_df)}")

# For each beneficiary_id, find MINIMUM prior_admissions
min_prior_by_bene = features_df.groupby('beneficiary_id')['prior_admissions'].min()
violations = (min_prior_by_bene != 0).sum()

print(f"  Unique beneficiaries: {len(min_prior_by_bene)}")
print(f"  Min prior_admissions distribution:")
print(f"    Min=0: {(min_prior_by_bene == 0).sum()}")
print(f"    Min>0: {(min_prior_by_bene > 0).sum()}")
print(f"  Beneficiaries with MIN(prior_admissions) != 0: {violations}")

if violations == 0:
    print("\nTASK 2: PASS — All beneficiaries have MIN(prior_admissions) = 0")
else:
    print(f"\nTASK 2 FAIL: {violations} beneficiaries have MIN(prior_admissions) != 0")
    print("STOPPING - Task 2 failed.")
    exit(1)

# ============================================================
# TASK 3: Death-exclusion check
# ============================================================
print("\n" + "=" * 80)
print("TASK 3: Death-exclusion check")
print("=" * 80)

print("\n[Task 3a] Reading beneficiary CSV...")
beneficiary_df = pd.read_csv(BENEFICIARY_CSV)
print(f"  Total beneficiary records: {len(beneficiary_df)}")

# Get beneficiaries with death date
beneficiary_df['BENE_DEATH_DT'] = beneficiary_df['BENE_DEATH_DT'].apply(parse_date)
beneficiaries_with_death = beneficiary_df[beneficiary_df['BENE_DEATH_DT'].notna()][['DESYNPUF_ID', 'BENE_DEATH_DT']].copy()
print(f"  Beneficiaries with death date: {len(beneficiaries_with_death)}")

print("\n[Task 3b] Finding 'death-during-stay' admissions...")
# Read inpatient data again
inpatient_df = pd.read_csv(INPATIENT_CSV)
inpatient_df['ADMSN_DT'] = inpatient_df['CLM_ADMSN_DT'].apply(parse_date)
inpatient_df['DSCHRG_DT'] = inpatient_df['NCH_BENE_DSCHRG_DT'].apply(parse_date)

# Merge with death dates
inpatient_with_death = inpatient_df.merge(
    beneficiaries_with_death, 
    on='DESYNPUF_ID', 
    how='inner'
)

print(f"  Inpatient records for deceased beneficiaries: {len(inpatient_with_death)}")

# Find admissions where CLM_ADMSN_DT <= BENE_DEATH_DT <= NCH_BENE_DSCHRG_DT
death_during_stay = inpatient_with_death[
    (inpatient_with_death['ADMSN_DT'] <= inpatient_with_death['BENE_DEATH_DT']) &
    (inpatient_with_death['BENE_DEATH_DT'] <= inpatient_with_death['DSCHRG_DT'])
]

death_during_stay_clm_ids = set(death_during_stay['CLM_ID'].tolist())
print(f"  'Death-during-stay' admission CLM_IDs: {len(death_during_stay_clm_ids)}")

if len(death_during_stay) > 0:
    print("  Sample death-during-stay records:")
    print(death_during_stay[['DESYNPUF_ID', 'CLM_ID', 'ADMSN_DT', 'DSCHRG_DT', 'BENE_DEATH_DT']].head().to_string())

print("\n[Task 3c] Checking if these CLM_IDs exist in features.parquet...")
# Read features again
features_df = pd.read_parquet(FEATURES_PARQUET)
features_clm_ids = set(features_df['claim_id'].tolist())

violations_3 = death_during_stay_clm_ids.intersection(features_clm_ids)
print(f"  Death-during-stay CLM_IDs found in features.parquet: {len(violations_3)}")

if len(violations_3) > 0:
    print(f"  Violating CLM_IDs: {list(violations_3)[:10]}")

if len(violations_3) == 0:
    print("\nTASK 3: PASS — No death-during-stay admissions in features")
else:
    print(f"\nTASK 3 FAIL: {len(violations_3)} death-during-stay admissions found in features")
    print("STOPPING - Task 3 failed.")
    exit(1)

# ============================================================
# TASK 4: Duplicate check
# ============================================================
print("\n" + "=" * 80)
print("TASK 4: Duplicate check")
print("=" * 80)

print("\n[Task 4] Checking for duplicate claim_ids in features.parquet...")
features_df = pd.read_parquet(FEATURES_PARQUET)

claim_counts = features_df.groupby('claim_id').size()
duplicates = claim_counts[claim_counts > 1]

print(f"  Total unique claim_ids: {len(claim_counts)}")
print(f"  Duplicate claim_ids (count > 1): {len(duplicates)}")

if len(duplicates) > 0:
    print(f"  Duplicate examples:")
    print(duplicates.head(10))

if len(duplicates) == 0:
    print("\nTASK 4: PASS — No duplicate claim_ids in features")
else:
    print(f"\nTASK 4 FAIL: {len(duplicates)} duplicate claim_ids found")
    print("STOPPING - Task 4 failed.")
    exit(1)

# ============================================================
# TASK 5: Visual inspection of EDA
# ============================================================
print("\n" + "=" * 80)
print("TASK 5: Visual inspection of EDA")
print("=" * 80)

print("\n[Task 5a] Reading and analyzing 01_eda.html...")

with open(EDA_HTML, 'r', encoding='utf-8') as f:
    eda_html = f.read()

# Extract numerical outputs from the HTML
import re

# Look for age distribution stats
age_pattern = r'(?:mean|median|average).*?age.*?[:=]\s*(\d+\.?\d*)'
age_matches = re.findall(age_pattern, eda_html, re.IGNORECASE)
print(f"  Age-related stats found in HTML: {age_matches}")

# Look for chronic condition prevalence
chronic_pattern = r'(?:prevalence|percent).*?(\d+\.?\d*)\s*%'
chronic_matches = re.findall(chronic_pattern, eda_html, re.IGNORECASE)
print(f"  Chronic condition percentages found: {chronic_matches}")

# Look for readmission rate
readmit_pattern = r'(?:readmit|readmission).*?rate.*?[:=]\s*(\d+\.?\d*)'
readmit_matches = re.findall(readmit_pattern, eda_html, re.IGNORECASE)
print(f"  Readmission rate found: {readmit_matches}")

# Let's also look for print output sections in the HTML
# Check for key statistics in the HTML
print("\n  Searching for key EDA outputs...")

# Check age distribution
age_mean_pattern = r'Age.*?mean.*?[:=]\s*(\d+\.?\d*)'
age_median_pattern = r'Age.*?median.*?[:=]\s*(\d+\.?\d*)'

age_mean_matches = re.findall(age_mean_pattern, eda_html, re.IGNORECASE)
age_median_matches = re.findall(age_median_pattern, eda_html, re.IGNORECASE)

print(f"    Age mean values found: {age_mean_matches}")
print(f"    Age median values found: {age_median_matches}")

# Verify age > 65
age_check_passed = False
if age_mean_matches:
    try:
        age_mean_val = float(age_mean_matches[0])
        if age_mean_val > 65:
            age_check_passed = True
            print(f"    Age mean {age_mean_val} > 65: PASS")
    except:
        pass

# Check chronic condition prevalence - look for specific conditions
chronic_conditions = ['Alzheimers', 'HeartFailure', 'KidneyDisease', 'Cancer', 'Diabetes', 'COPD']
chronic_found = []
for cond in chronic_conditions:
    pattern = f'{cond}.*?(\\d+\\.?\\d*)\\s*%'
    matches = re.findall(pattern, eda_html, re.IGNORECASE)
    if matches:
        try:
            val = float(matches[0])
            if 5 <= val <= 70:
                chronic_found.append((cond, val, True))
            else:
                chronic_found.append((cond, val, False))
        except:
            chronic_found.append((cond, 'N/A', False))

print(f"    Chronic condition prevalence:")
for cond, val, is_valid in chronic_found:
    status = "PASS" if is_valid else "FAIL"
    print(f"      {cond}: {val}% - {status}")

chronic_check_passed = all(v[2] for v in chronic_found) if chronic_found else False

# Check readmission rate
readmit_rate_pattern = r'(?:overall|base).*?readmit.*?rate.*?[:=]?\\s*(\\d+\\.?\\d*)'
readmit_rate_matches = re.findall(readmit_rate_pattern, eda_html, re.IGNORECASE)

# Also look for specific 0.1013
readmit_exact = re.findall(r'0\.101[0-9]', eda_html)
print(f"    Readmission rate matches (0.1013): {readmit_exact}")

readmit_check_passed = len(readmit_exact) > 0 or len(readmit_rate_matches) > 0

print(f"\n  Task 5a Summary:")
print(f"    Age distribution mean/median > 65: {'PASS' if age_check_passed else 'CHECK HTML'}")
print(f"    Chronic condition prevalence 5-70%: {'PASS' if chronic_check_passed else ('CHECK HTML' if chronic_found else 'NOT FOUND')}")
print(f"    Readmission rate ≈ 0.1013: {'PASS' if readmit_check_passed else 'CHECK HTML'}")

print("\n[Task 5b] Checking PNG file existence and sizes...")
png_files = [
    'eda_readmit_dist.png',
    'eda_age_dist.png',
    'eda_chronic_prev.png',
    'eda_los_dist.png',
    'eda_missing.png',
    'eda_diag_prior.png'
]

png_dir = f"{PROJECT_DIR}/notebooks"
png_info = []

for png_file in png_files:
    png_path = os.path.join(png_dir, png_file)
    if os.path.exists(png_path):
        size = os.path.getsize(png_path)
        png_info.append((png_file, size, True))
        print(f"    {png_file}: {size} bytes")
    else:
        png_info.append((png_file, 0, False))
        print(f"    {png_file}: NOT FOUND")

png_check_passed = all(info[2] and info[1] > 0 for info in png_info)

if png_check_passed and age_check_passed and chronic_check_passed and readmit_check_passed:
    print("\nTASK 5: PASS — All EDA visual checks passed")
else:
    print("\nTASK 5: FAIL - Some EDA checks failed")
    print("STOPPING - Task 5 failed.")
    exit(1)

# ============================================================
# FINAL REPORT
# ============================================================
print("\n" + "=" * 80)
print("FINAL REPORT")
print("=" * 80)
print("  TASK 1: PASS — All 5 beneficiaries verified correctly")
print("  TASK 2: PASS — All beneficiaries have MIN(prior_admissions) = 0")
print("  TASK 3: PASS — No death-during-stay admissions in features")
print("  TASK 4: PASS — No duplicate claim_ids in features")
print("  TASK 5: PASS — All EDA visual checks passed")
print("\nPART 1 QA: ALL TASKS PASSED — Pipeline verified.")