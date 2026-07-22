"""
Script 01: Download PhoNER_COVID19 and VietMed-NER datasets
"""
import subprocess
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets")

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    else:
        print(f"STDOUT: {result.stdout[:500]}")
    return result.returncode == 0

def download_phoner():
    target = os.path.join(DATASETS_DIR, "phoner_covid19")
    if os.path.exists(os.path.join(target, "data")):
        print("PhoNER_COVID19 already downloaded, skipping...")
        return True
    
    print("=== Downloading PhoNER_COVID19 ===")
    tmp_dir = os.path.join(DATASETS_DIR, "phoner_tmp")
    run_cmd(f'git clone https://github.com/VinAIResearch/PhoNER_COVID19.git "{tmp_dir}"')
    
    data_src = os.path.join(tmp_dir, "data")
    if os.path.exists(data_src):
        import shutil
        shutil.copytree(data_src, target, dirs_exist_ok=True)
        shutil.rmtree(tmp_dir)
        print(f"PhoNER data saved to {target}")
        return True
    print("ERROR: PhoNER data directory not found")
    return False

def download_vietmed():
    target = os.path.join(DATASETS_DIR, "vietmed_ner")
    if os.path.exists(target) and len(os.listdir(target)) > 2:
        print("VietMed-NER already downloaded, skipping...")
        return True
    
    print("=== Downloading VietMed-NER from HuggingFace ===")
    try:
        from datasets import load_dataset
        ds = load_dataset("leduckhai/VietMed-NER", trust_remote_code=True)
        
        for split_name, split_data in ds.items():
            split_data.to_csv(os.path.join(target, f"{split_name}.csv"), index=False)
            print(f"Saved {split_name} split: {len(split_data)} rows")
        
        print(f"VietMed-NER saved to {target}")
        return True
    except Exception as e:
        print(f"ERROR downloading VietMed-NER: {e}")
        return False

def download_acrdrAid():
    target = os.path.join(DATASETS_DIR, "acrdrAid")
    if os.path.exists(target) and len(os.listdir(target)) > 1:
        print("acrDrAid already downloaded, skipping...")
        return True
    
    print("=== Downloading acrDrAid from GitHub ===")
    tmp_dir = os.path.join(DATASETS_DIR, "acrdrAid_tmp")
    run_cmd(f'git clone https://github.com/demdecuong/vihealthbert.git "{tmp_dir}"')
    
    acrdraid_src = None
    for root, dirs, files in os.walk(tmp_dir):
        for f in files:
            if "acrdrAid" in f.lower() or "acrdr" in f.lower():
                acrdraid_src = root
                break
        if acrdraid_src:
            break
    
    if acrdraid_src:
        import shutil
        os.makedirs(target, exist_ok=True)
        shutil.copytree(acrdraid_src, target, dirs_exist_ok=True)
        shutil.rmtree(tmp_dir)
        print(f"acrDrAid saved to {target}")
        return True
    
    if os.path.exists(tmp_dir):
        import shutil
        shutil.rmtree(tmp_dir)
    print("WARNING: acrDrAid files not found in vihealthbert repo")
    return False

if __name__ == "__main__":
    os.makedirs(DATASETS_DIR, exist_ok=True)
    
    results = {}
    results["PhoNER"] = download_phoner()
    results["VietMed"] = download_vietmed()
    results["acrDrAid"] = download_acrdrAid()
    
    print("\n=== Download Summary ===")
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {name}: {status}")
