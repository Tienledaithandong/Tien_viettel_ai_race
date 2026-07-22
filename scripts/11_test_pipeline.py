"""
Test pipeline on sample data - step by step debug output.
"""
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from normalization import normalize_clinical_text
from ner import NERLLMEngine, NEREnsemble
from ner.position_align import align_all_positions
from entity_linking import EntityLinker
from assertion import AssertionDetector
from postprocessing import postprocess


def test_without_llm():
    """Test pipeline without LLM NER (just normalization + linking + assertion)."""
    print("="*60)
    print("TESTING PIPELINE (without LLM NER)")
    print("="*60)

    # Read sample
    sample_path = os.path.join(PROJECT_ROOT, "test_input", "1.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    print(f"\n--- INPUT TEXT ---")
    print(text[:300])

    # Step 1: Normalize
    print(f"\n--- STEP 1: NORMALIZATION ---")
    normalized = normalize_clinical_text(text)
    print(f"  Original length: {len(text)}")
    print(f"  Normalized length: {len(normalized)}")
    print(f"  Diff: {text != normalized}")

    # Step 2: Simulate NER output (hardcoded for testing)
    print(f"\n--- STEP 2: NER (simulated) ---")
    # Use the example output from the competition
    simulated_entities = [
        {"text": "ho", "type": "TRIỆU_CHỨNG", "position": [108, 110]},
        {"text": "tức ngực", "type": "TRIỆU_CHỨNG", "position": [119, 127]},
        {"text": "đau thượng vị", "type": "TRIỆU_CHỨNG", "position": [129, 142]},
        {"text": "ợ hơi", "type": "TRIỆU_CHỨNG", "position": [144, 149]},
        {"text": "Chlorpheniramine 0.4 MG/ML", "type": "THUỐC", "position": [186, 214]},
        {"text": "Capsaicin 0.38 MG/ML", "type": "THUỐC", "position": [216, 237]},
        {"text": "WBC", "type": "TÊN_XÉT_NGHIỆM", "position": [298, 301]},
        {"text": "14,43", "type": "KẾT_QUẢ_XÉT_NGHIỆM", "position": [302, 307]},
        {"text": "NEUT%", "type": "TÊN_XÉT_NGHIỆM", "position": [309, 314]},
        {"text": "76,4", "type": "KẾT_QUẢ_XÉT_NGHIỆM", "position": [340, 344]},
        {"text": "LYPH%", "type": "TÊN_XÉT_NGHIỆM", "position": [346, 351]},
        {"text": "12,8", "type": "KẾT_QUẢ_XÉT_NGHIỆM", "position": [374, 378]},
        {"text": "trào ngược dạ dày - thực quản", "type": "CHẨN_ĐOÁN", "position": [162, 191]},
    ]

    # Verify positions against actual text
    for ent in simulated_entities:
        start, end = ent["position"]
        if start >= 0 and end <= len(text):
            actual = text[start:end]
            match = actual.lower() == ent["text"].lower()
            status = "OK" if match else "MISMATCH"
            print(f"  [{status}] '{ent['text']}' -> actual='{actual}' pos={ent['position']}")
            if not match:
                # Try to find correct position
                idx = text.lower().find(ent["text"].lower())
                if idx >= 0:
                    ent["position"] = [idx, idx + len(ent["text"])]
                    print(f"    -> FIXED to [{idx}, {idx + len(ent['text'])}]")
        else:
            print(f"  [OOB] '{ent['text']}' pos={ent['position']} exceeds text length {len(text)}")

    # Step 3: Assertion Detection
    print(f"\n--- STEP 3: ASSERTION DETECTION ---")
    detector = AssertionDetector(use_classifier=False)
    entities = detector.detect_all(text, simulated_entities)
    for ent in entities:
        assertions = ent.get("assertions", [])
        if assertions:
            print(f"  '{ent['text']}' -> {assertions}")

    # Step 4: Entity Linking
    print(f"\n--- STEP 4: ENTITY LINKING ---")
    linker = EntityLinker()
    linker.load()

    for ent in entities:
        etype = ent.get("type", "")
        if etype in ["THUỐC", "CHẨN_ĐOÁN"]:
            candidates = linker.link_entity(ent["text"], etype, text, top_k=5)
            ent["candidates"] = candidates
            print(f"  '{ent['text']}' ({etype}) -> {candidates[:3]}")
        else:
            ent["candidates"] = []

    # Step 5: Post-processing
    print(f"\n--- STEP 5: POST-PROCESSING ---")
    output = postprocess(text, entities)

    # Final output
    print(f"\n--- FINAL OUTPUT ({len(output)} entities) ---")
    print(json.dumps(output, ensure_ascii=False, indent=2))

    return output


if __name__ == "__main__":
    test_without_llm()
