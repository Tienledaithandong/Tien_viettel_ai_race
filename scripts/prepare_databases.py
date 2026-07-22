#!/usr/bin/env python3
"""
Prepare Local Knowledge Bases for Hybrid Mapping
Creates optimized JSON dictionaries for fast exact matching.
"""
import json
import os
from pathlib import Path


def prepare_icd_database(input_path: str = "data/icd10_raw.json", 
                         output_path: str = "data/icd10_cleaned.json"):
    """
    Prepare ICD-10 database for diagnosis mapping.
    Creates a dictionary: {normalized_disease_name: icd_code}
    """
    print("Preparing ICD-10 database...")
    
    if not os.path.exists(input_path):
        print(f"  Warning: {input_path} not found. Creating empty database.")
        icd_db = {}
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        icd_db = {}
        for entry in raw_data:
            code = entry.get('code', '')
            name = entry.get('name', '')
            synonyms = entry.get('synonyms', [])
            
            # Add main name
            if name and code:
                normalized = " ".join(name.lower().split())
                icd_db[normalized] = code
            
            # Add synonyms
            for syn in synonyms:
                if syn and code:
                    normalized = " ".join(syn.lower().split())
                    icd_db[normalized] = code
    
    # Save cleaned database
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(icd_db, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Created {output_path} with {len(icd_db)} entries")
    return icd_db


def prepare_rxnorm_database(input_path: str = "data/rxnorm_raw.json",
                            output_path: str = "data/rxnorm_cleaned.json"):
    """
    Prepare RxNorm database for drug mapping.
    Creates a dictionary: {normalized_drug_name: rxnorm_code}
    """
    print("Preparing RxNorm database...")
    
    if not os.path.exists(input_path):
        print(f"  Warning: {input_path} not found. Creating empty database.")
        rxnorm_db = {}
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        rxnorm_db = {}
        for entry in raw_data:
            code = entry.get('rxcui', '')
            name = entry.get('name', '')
            synonyms = entry.get('synonyms', [])
            
            # Add main name
            if name and code:
                normalized = " ".join(name.lower().split())
                rxnorm_db[normalized] = code
            
            # Add synonyms
            for syn in synonyms:
                if syn and code:
                    normalized = " ".join(syn.lower().split())
                    rxnorm_db[normalized] = code
    
    # Save cleaned database
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rxnorm_db, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Created {output_path} with {len(rxnorm_db)} entries")
    return rxnorm_db


def main():
    """Main function to prepare all databases."""
    print("=" * 60)
    print("PREPARING LOCAL KNOWLEDGE BASES")
    print("=" * 60)
    
    prepare_icd_database()
    prepare_rxnorm_database()
    
    print("\n=== Database Preparation Complete ===")
    print("\nNext steps:")
    print("1. Run: python src/optimized_inference.py --input test/input --output output")
    print("2. Check output files for improved candidate mappings")


if __name__ == "__main__":
    main()
