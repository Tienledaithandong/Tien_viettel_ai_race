"""
FAISS Index Builder for ICD-10 and RxNorm databases.
Run once to precompute embeddings and build indexes.
"""
import json
import os
import re
import unicodedata
import numpy as np
from typing import List, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


def remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for better matching."""
    # Decompose unicode then remove combining marks
    nfkd = unicodedata.normalize('NFKD', text)
    result = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    # Fix common Vietnamese characters that get mangled
    replacements = {
        'đ': 'd', 'Đ': 'D',
        'ă': 'a', 'Â': 'A', 'â': 'a',
        'ê': 'e', 'Ê': 'E',
        'ô': 'o', 'Ô': 'O',
        'ơ': 'o', 'Ơ': 'O',
        'ư': 'u', 'Ư': 'U',
    }
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result.lower()


# Common medical abbreviation mappings for ICD-10
ICD_SYNONYMS = {
    "I10": ["tang huyet ap", "tang ap", "tha", "hypertension", "high blood pressure", "htn"],
    "E11.9": ["dai thuong duong", "tieuduong", "td", "diabetes", "dm2", "t2dm"],
    "J44.9": ["copd", "benh phoi tac nghen man", "phoi tac nghen"],
    "J45.909": ["hen", "hen phe quan", "asthma"],
    "K21.0": ["gerd", "trao nguoc", "trao nguoc da day", "reflux"],
    "I48.91": ["rung nhi", "af", "afib", "atrial fibrillation"],
    "I50.9": ["suy tim", "heart failure", "hf"],
    "I25.10": ["benh dong mach vonh", "cad", "coronary artery disease"],
    "I63.9": ["dot quy", "nhieu mau nao", "stroke", "ischemic stroke"],
    "N18.5": ["suy than", "ckd", "chronic kidney disease"],
    "M54.5": ["dau that lung", "low back pain", "lbp"],
    "K80.20": ["soi mat", "gallstones", "soi tui mat"],
    "E78.5": ["tang lipid mau", "hyperlipidemia", "mo mau cao"],
    "J18.9": ["viem phoi", "pneumonia"],
    "K85.9": ["viem tuy cap", "acute pancreatitis"],
    "M17.11": ["thoai hoa khop goi", "knee osteoarthritis", "knee oa"],
}


def load_icd10_database() -> List[Dict]:
    """Load ICD-10 database and prepare entries for embedding."""
    path = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd10_database.json")
    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    entries = []
    for code, info in db.get("codes", {}).items():
        name_vi = info.get("name_vi", "")
        name_en = info.get("name_en", "")
        search_text = info.get("search_text", "")
        category = info.get("category", "")

        # Remove diacritics for additional matching
        name_vi_no_diac = remove_diacritics(name_vi)
        name_en_lower = name_en.lower()

        # Get synonyms if available
        synonyms = ICD_SYNONYMS.get(code, [])
        synonym_text = " ".join(synonyms)

        # Build rich embedding text with multiple representations
        parts = [
            name_vi,           # Vietnamese with diacritics
            name_vi_no_diac,   # Vietnamese without diacritics
            name_en,           # English
            code,              # ICD code
            category,          # Category
            synonym_text,      # Synonyms
            search_text,       # Combined search text
        ]
        embedding_text = " ".join(p for p in parts if p).strip()

        entries.append({
            "code": code,
            "name_vi": name_vi,
            "name_en": name_en,
            "category": category,
            "search_text": search_text,
            "synonyms": synonyms,
            "embedding_text": embedding_text,
        })

    return entries


def load_rxnorm_database() -> List[Dict]:
    """Load RxNorm database and prepare entries for embedding."""
    path = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rxnorm_database.json")
    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    entries = []
    for rxcui, info in db.get("drugs", {}).items():
        name_vi = info.get("name_vi", "")
        name_en = info.get("name_en", "")
        generic = info.get("generic", "")
        category = info.get("category", "")
        search_text = info.get("search_text", "")

        # Build rich embedding text
        parts = [
            name_vi,
            name_en,
            generic,
            rxcui,
            category,
            search_text,
        ]
        embedding_text = " ".join(p for p in parts if p).strip()

        entries.append({
            "rxcui": rxcui,
            "name_vi": name_vi,
            "name_en": name_en,
            "generic": generic,
            "category": category,
            "search_text": search_text,
            "embedding_text": embedding_text,
        })

    return entries


def build_index(
    entries: List[Dict],
    output_path: str,
    metadata_path: str,
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 32,
):
    """Build FAISS index from entries."""
    if not HAS_FAISS:
        raise ImportError("faiss-cpu or faiss-gpu required")
    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence-transformers required")

    print(f"Building index for {len(entries)} entries...")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and batch_size == 32:
        batch_size = 128
    print(f"  Loaded model: {model_name} on device: {device} (batch_size={batch_size})")
    model = SentenceTransformer(model_name, device=device)

    # Encode all texts
    texts = [e["embedding_text"] for e in entries]
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype=np.float32)

    # Build FAISS index
    dimension = embeddings.shape[1]
    n_entries = embeddings.shape[0]

    # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"  Index built: {index.ntotal} vectors, dimension={dimension}")

    # Save index
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    faiss.write_index(index, output_path)
    print(f"  Index saved to {output_path}")

    # Save metadata (without embedding_text to save space)
    metadata = []
    for entry in entries:
        meta = {k: v for k, v in entry.items() if k != "embedding_text"}
        metadata.append(meta)

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  Metadata saved to {metadata_path}")

    return index, metadata


def build_all_indexes(model_name: str = "BAAI/bge-m3"):
    """Build both ICD-10 and RxNorm indexes."""
    index_dir = os.path.join(PROJECT_ROOT, "indices")
    os.makedirs(index_dir, exist_ok=True)

    # ICD-10
    print("\n=== Building ICD-10 Index ===")
    icd_entries = load_icd10_database()
    if icd_entries:
        build_index(
            icd_entries,
            os.path.join(index_dir, "icd10.faiss"),
            os.path.join(index_dir, "icd10_metadata.json"),
            model_name,
        )

    # RxNorm
    print("\n=== Building RxNorm Index ===")
    rxnorm_entries = load_rxnorm_database()
    if rxnorm_entries:
        build_index(
            rxnorm_entries,
            os.path.join(index_dir, "rxnorm.faiss"),
            os.path.join(index_dir, "rxnorm_metadata.json"),
            model_name,
        )

    print("\n=== All indexes built ===")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="BAAI/bge-m3", help="Embedding model name")
    args = parser.parse_args()
    build_all_indexes(args.model)
