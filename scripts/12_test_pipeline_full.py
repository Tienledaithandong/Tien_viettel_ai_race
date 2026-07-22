"""
Test pipeline with all 3 sample texts and compare with ground truth.
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


# Ground truth from competition example
GROUND_TRUTH = {
    "1": [
        {"text": "amlodipine 10 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["308135"]},
        {"text": "aspirin 81 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["243670"]},
        {"text": "metoprolol succinate xl 50 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["866436"]},
        {"text": "guaifenesin ml po q6h:prn", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["392085"]},
        {"text": "ho", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "nystatin oral suspension 5 ml po qid:prn", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["7597"]},
        {"text": "đau nhức", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "acetaminophen 325-650 mg po q6h:prn", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["313782"]},
        {"text": "sốt đau", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "pravastatin 40 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["904475"]},
        {"text": "docusate sodium 100 mg po bid", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["1099279"]},
        {"text": "táo bón", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "senna 8.6 mg po bid:prn", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["312935"]},
        {"text": "táo bón", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "clonazepam 0.5 mg po qam:prn", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["197527"]},
        {"text": "lo âu", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "clonazepam 1.5 mg po qhs", "type": "THUỐC", "assertions": ["isHistorical"], "candidates": ["197528"]},
        {"text": "lo âu", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
        {"text": "mất ngủ", "type": "TRIỆU_CHỨNG", "assertions": [], "candidates": []},
    ]
}


def test_assertion_detection():
    """Test assertion detection on various contexts."""
    print("="*60)
    print("TEST: ASSERTION DETECTION")
    print("="*60)

    detector = AssertionDetector(use_classifier=False)

    test_cases = [
        ("Bệnh nhân không ho, không khó thở", "ho", [15, 17], ["isNegated"]),
        ("Tiền sử tăng huyết áp 5 năm", "tăng huyết áp", [11, 25], ["isHistorical"]),
        ("Mẹ bị đái tháo đường type 2", "đái tháo đường type 2", [7, 28], ["isFamily"]),
        ("Bệnh nhân đã từng phẫu thuật 2020", "phẫu thuật", [22, 33], ["isHistorical"]),
        ("Bố bệnh nhân mắc ung thư phổi", "ung thư phổi", [23, 35], ["isFamily"]),
        ("Không có tiền sử bệnh tim", "bệnh tim", [20, 28], ["isNegated", "isHistorical"]),
    ]

    for text, entity_text, expected_pos, expected_assertions in test_cases:
        entity = {"text": entity_text, "position": expected_pos, "type": "CHẨN_ĐOÁN"}
        result = detector.detect(text, entity)
        match = set(result) == set(expected_assertions)
        status = "PASS" if match else "FAIL"
        print(f"  [{status}] '{entity_text}' in '{text[:40]}...'")
        if not match:
            print(f"    Expected: {expected_assertions}")
            print(f"    Got:      {result}")


def test_entity_linking():
    """Test entity linking accuracy."""
    print("\n" + "="*60)
    print("TEST: ENTITY LINKING")
    print("="*60)

    linker = EntityLinker()
    linker.load()

    test_cases = [
        # (entity_text, type, expected_code)
        ("amlodipine 10mg", "THUỐC", "308135"),
        ("aspirin 81mg", "THUỐC", "243670"),
        ("metformin 500mg", "THUỐC", "861006"),
        ("omeprazole 20mg", "THUỐC", "198205"),
        ("tăng huyết áp", "CHẨN_ĐOÁN", "I10"),
        ("đái tháo đường typ 2", "CHẨN_ĐOÁN", "E11.9"),
        ("viêm phổi", "CHẨN_ĐOÁN", "J18.9"),
        ("COPD", "CHẨN_ĐOÁN", "J44.9"),
    ]

    for entity_text, etype, expected_code in test_cases:
        candidates = linker.link_entity(entity_text, etype, "", top_k=5)
        found = expected_code in candidates
        status = "PASS" if found else "FAIL"
        print(f"  [{status}] '{entity_text}' ({etype}) -> expected={expected_code}, got={candidates[:3]}")


def test_full_pipeline():
    """Test full pipeline on all sample texts."""
    print("\n" + "="*60)
    print("TEST: FULL PIPELINE")
    print("="*60)

    # Load components
    detector = AssertionDetector(use_classifier=False)
    linker = EntityLinker()
    linker.load()

    # Process sample 1
    sample_path = os.path.join(PROJECT_ROOT, "test_input", "1.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # Simulated NER output (same as competition example)
    entities = [
        {"text": "amlodipine 10 mg po daily", "type": "THUỐC", "position": [58, 83]},
        {"text": "aspirin 81 mg po daily", "type": "THUỐC", "position": [89, 111]},
        {"text": "metoprolol succinate xl 50 mg po daily", "type": "THUỐC", "position": [117, 155]},
        {"text": "guaifenesin ml po q6h:prn", "type": "THUỐC", "position": [161, 186]},
        {"text": "ho", "type": "TRIỆU_CHỨNG", "position": [196, 198]},
        {"text": "nystatin oral suspension 5 ml po qid:prn", "type": "THUỐC", "position": [204, 244]},
        {"text": "đau nhức", "type": "TRIỆU_CHỨNG", "position": [254, 262]},
        {"text": "acetaminophen 325-650 mg po q6h:prn", "type": "THUỐC", "position": [268, 303]},
        {"text": "sốt đau", "type": "TRIỆU_CHỨNG", "position": [313, 320]},
        {"text": "pravastatin 40 mg po daily", "type": "THUỐC", "position": [326, 352]},
        {"text": "docusate sodium 100 mg po bid", "type": "THUỐC", "position": [358, 387]},
        {"text": "táo bón", "type": "TRIỆU_CHỨNG", "position": [397, 404]},
        {"text": "senna 8.6 mg po bid:prn", "type": "THUỐC", "position": [410, 433]},
        {"text": "táo bón", "type": "TRIỆU_CHỨNG", "position": [443, 450]},
        {"text": "clonazepam 0.5 mg po qam:prn", "type": "THUỐC", "position": [457, 485]},
        {"text": "lo âu", "type": "TRIỆU_CHỨNG", "position": [495, 500]},
        {"text": "clonazepam 1.5 mg po qhs", "type": "THUỐC", "position": [507, 531]},
        {"text": "lo âu", "type": "TRIỆU_CHỨNG", "position": [541, 546]},
        {"text": "mất ngủ", "type": "TRIỆU_CHỨNG", "position": [547, 554]},
    ]

    # Verify all positions
    print("\nPosition verification:")
    all_ok = True
    for ent in entities:
        s, e = ent["position"]
        if e > len(text):
            print(f"  OOB: '{ent['text']}' pos=[{s},{e}] text_len={len(text)}")
            all_ok = False
        elif text[s:e].lower() != ent["text"].lower():
            print(f"  MISMATCH: '{ent['text']}' != '{text[s:e]}'")
            all_ok = False
    if all_ok:
        print("  All positions OK!")

    # Assertions
    print("\nAssertion detection:")
    entities = detector.detect_all(text, entities)
    historical_count = sum(1 for e in entities if "isHistorical" in e.get("assertions", []))
    print(f"  Historical assertions: {historical_count} (expected: 10)")

    # Entity linking
    print("\nEntity linking:")
    entities = linker.link_entities(entities, text, top_k=5)

    correct_links = 0
    for ent, gt in zip(entities, GROUND_TRUTH["1"]):
        if ent["type"] == "THUỐC" and ent.get("candidates"):
            if gt["candidates"][0] in ent["candidates"]:
                correct_links += 1
                print(f"  CORRECT: '{ent['text'][:30]}' -> {ent['candidates'][0]}")
            else:
                print(f"  WRONG:   '{ent['text'][:30]}' -> {ent['candidates'][:2]}, expected={gt['candidates'][0]}")

    drug_entities = [e for e in entities if e["type"] == "THUỐC"]
    print(f"\nLinking accuracy: {correct_links}/{len(drug_entities)} = {correct_links/max(len(drug_entities),1)*100:.0f}%")

    return entities


if __name__ == "__main__":
    test_assertion_detection()
    test_entity_linking()
    test_full_pipeline()
