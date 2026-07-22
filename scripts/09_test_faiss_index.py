"""
Quick test: verify FAISS indexes work correctly with search queries.
"""
import json
import os
import sys
import io
import numpy as np

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import faiss
from sentence_transformers import SentenceTransformer


def test_search():
    print("=== Testing FAISS Indexes ===\n")

    # Load model
    model = SentenceTransformer("BAAI/bge-m3")
    print("Model loaded: BAAI/bge-m3\n")

    # --- ICD-10 Test ---
    print("--- ICD-10 Index ---")
    icd_index = faiss.read_index(os.path.join(PROJECT_ROOT, "indices", "icd10.faiss"))
    with open(os.path.join(PROJECT_ROOT, "indices", "icd10_metadata.json"), "r", encoding="utf-8") as f:
        icd_meta = json.load(f)
    print(f"  Loaded: {icd_index.ntotal} vectors, dimension={icd_index.d}")

    # Test queries
    icd_queries = [
        "tang huyet ap",
        "dai thuong duong",
        "viem phoi",
        "dau that lung",
        "suy than",
        "trao nguoc da day thuc quan",
    ]

    for q in icd_queries:
        emb = model.encode([q], normalize_embeddings=True).astype(np.float32)
        scores, indices = icd_index.search(emb, 3)
        print(f"\n  Query: {q}")
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(icd_meta):
                m = icd_meta[idx]
                code = m.get('code', '?')
                name = m.get('name_vi', '')[:40]
                print(f"    {code:10s} score={score:.4f} | {name}")

    # --- RxNorm Test ---
    print("\n--- RxNorm Index ---")
    rx_index = faiss.read_index(os.path.join(PROJECT_ROOT, "indices", "rxnorm.faiss"))
    with open(os.path.join(PROJECT_ROOT, "indices", "rxnorm_metadata.json"), "r", encoding="utf-8") as f:
        rx_meta = json.load(f)
    print(f"  Loaded: {rx_index.ntotal} vectors, dimension={rx_index.d}")

    rx_queries = [
        "amlodipine 10mg",
        "paracetamol",
        "metformin",
        "omeprazole",
        "aspirin",
        "insulin",
    ]

    for q in rx_queries:
        emb = model.encode([q], normalize_embeddings=True).astype(np.float32)
        scores, indices = rx_index.search(emb, 3)
        print(f"\n  Query: {q}")
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(rx_meta):
                m = rx_meta[idx]
                cui = m.get('rxcui', '?')
                name = m.get('name_vi', '')[:40]
                print(f"    CUI={cui:8s} score={score:.4f} | {name}")

    print("\n=== All tests passed ===")


if __name__ == "__main__":
    test_search()
