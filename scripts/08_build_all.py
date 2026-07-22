"""
Script 08: Master Script - Build all databases and datasets
Usage: python scripts/08_build_all.py [--skip-scrape] [--skip-synthetic]
"""
import subprocess
import os
import sys
import json
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")


def run_script(script_name: str, args: list = None) -> bool:
    """Run a script and return success status."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path] + (args or [])
    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def verify_databases():
    """Verify that databases are built correctly."""
    print("\n" + "="*60)
    print("VERIFYING DATABASES")
    print("="*60)

    # ICD-10
    icd10_path = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd10_database.json")
    if os.path.exists(icd10_path):
        with open(icd10_path, "r", encoding="utf-8") as f:
            icd10 = json.load(f)
        cats = icd10.get('categories', [])
        print(f"  ICD-10: {icd10.get('total_codes', 0)} codes, {len(cats)} categories")
    else:
        print("  ICD-10: NOT FOUND")

    # RxNorm
    rxnorm_path = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rxnorm_database.json")
    if os.path.exists(rxnorm_path):
        with open(rxnorm_path, "r", encoding="utf-8") as f:
            rxnorm = json.load(f)
        cats = rxnorm.get('categories', [])
        print(f"  RxNorm: {rxnorm.get('total_drugs', 0)} drugs, {len(cats)} categories")
    else:
        print("  RxNorm: NOT FOUND")

    # Medical Dictionary
    dict_path = os.path.join(PROJECT_ROOT, "databases", "medical_dictionary.json")
    if os.path.exists(dict_path):
        with open(dict_path, "r", encoding="utf-8") as f:
            med_dict = json.load(f)
        print(f"  Dictionary: {med_dict.get('total_abbreviations', 0)} abbreviations, {med_dict.get('total_synonym_groups', 0)} synonym groups")
    else:
        print("  Dictionary: NOT FOUND")


def verify_datasets():
    """Verify that datasets are available."""
    print("\n" + "="*60)
    print("VERIFYING DATASETS")
    print("="*60)

    datasets = {
        "PhoNER_COVID19": os.path.join(PROJECT_ROOT, "datasets", "phoner_covid19"),
        "VietMed-NER": os.path.join(PROJECT_ROOT, "datasets", "vietmed_ner"),
        "Synthetic": os.path.join(PROJECT_ROOT, "datasets", "synthetic"),
        "Scraped": os.path.join(PROJECT_ROOT, "datasets", "scraped"),
        "Unified Train": os.path.join(PROJECT_ROOT, "datasets", "unified", "train.json"),
        "Unified Val": os.path.join(PROJECT_ROOT, "datasets", "unified", "val.json"),
    }

    for name, path in datasets.items():
        if os.path.exists(path):
            if os.path.isdir(path):
                files = os.listdir(path)
                print(f"  {name}: OK ({len(files)} files)")
            else:
                size = os.path.getsize(path)
                print(f"  {name}: OK ({size:,} bytes)")
        else:
            print(f"  {name}: NOT FOUND")


def verify_datasets():
    """Verify that datasets are available."""
    print("\n" + "="*60)
    print("VERIFYING DATASETS")
    print("="*60)

    datasets = {
        "PhoNER_COVID19": os.path.join(PROJECT_ROOT, "datasets", "phoner_covid19"),
        "VietMed-NER": os.path.join(PROJECT_ROOT, "datasets", "vietmed_ner"),
        "Synthetic": os.path.join(PROJECT_ROOT, "datasets", "synthetic"),
        "Scraped": os.path.join(PROJECT_ROOT, "datasets", "scraped"),
        "Unified Train": os.path.join(PROJECT_ROOT, "datasets", "unified", "train.json"),
        "Unified Val": os.path.join(PROJECT_ROOT, "datasets", "unified", "val.json"),
    }

    for name, path in datasets.items():
        if os.path.exists(path):
            if os.path.isdir(path):
                files = os.listdir(path)
                print(f"  {name}: OK ({len(files)} files)")
            else:
                size = os.path.getsize(path)
                print(f"  {name}: OK ({size:,} bytes)")
        else:
            print(f"  {name}: NOT FOUND")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build all databases and datasets")
    parser.add_argument("--skip-download", action="store_true", help="Skip dataset download")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip web scraping")
    parser.add_argument("--skip-synthetic", action="store_true", help="Skip synthetic data generation")
    parser.add_argument("--skip-convert", action="store_true", help="Skip unified format conversion")
    args = parser.parse_args()

    print("="*60)
    print("MEDICAL NLP - BUILD ALL DATABASES & DATASETS")
    print("="*60)

    # Step 1: Build databases (always)
    print("\n--- Step 1: Build Databases ---")
    run_script("02_build_icd10_database.py")
    run_script("03_build_rxnorm_database.py")
    run_script("06_medical_dictionary.py")
    verify_databases()

    # Step 2: Download existing datasets
    if not args.skip_download:
        print("\n--- Step 2: Download Existing Datasets ---")
        run_script("01_download_datasets.py")

    # Step 3: Scrape web data
    if not args.skip_scrape:
        print("\n--- Step 3: Scrape Web Data ---")
        run_script("04_scrape_medical_data.py")

    # Step 4: Generate synthetic data
    if not args.skip_synthetic:
        print("\n--- Step 4: Generate Synthetic Data ---")
        run_script("05_generate_synthetic_data.py")

    # Step 5: Convert to unified format
    if not args.skip_convert:
        print("\n--- Step 5: Convert to Unified Format ---")
        run_script("07_convert_to_unified_format.py")

    # Final verification
    verify_datasets()

    print("\n" + "="*60)
    print("BUILD COMPLETE!")
    print("="*60)
