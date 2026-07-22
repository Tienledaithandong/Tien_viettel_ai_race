"""
Post-processing Module
- Rule-based fixes
- JSON validation
- Candidate expansion
- Final output formatting
"""
import re
import json
from typing import List, Dict, Optional, Tuple

# ============================================================
# RULE-BASED FIXES
# ============================================================

# Entities that should NEVER be certain types
TYPE_CONSTRAINTS = {
    # Lab test names should not be symptoms
    "WBC": "TÊN_XÉT_NGHIỆM",
    "RBC": "TÊN_XÉT_NGHIỆM",
    "Hb": "TÊN_XÉT_NGHIỆM",
    "Hgb": "TÊN_XÉT_NGHIỆM",
    "Hct": "TÊN_XÉT_NGHIỆM",
    "Plt": "TÊN_XÉT_NGHIỆM",
    "PLT": "TÊN_XÉT_NGHIỆM",
    "NEUT": "TÊN_XÉT_NGHIỆM",
    "LYMPH": "TÊN_XÉT_NGHIỆM",
    "MONO": "TÊN_XÉT_NGHIỆM",
    "CRP": "TÊN_XÉT_NGHIỆM",
    "ESR": "TÊN_XÉT_NGHIỆM",
    "AST": "TÊN_XÉT_NGHIỆM",
    "ALT": "TÊN_XÉT_NGHIỆM",
    "GGT": "TÊN_XÉT_NGHIỆM",
    "ALP": "TÊN_XÉT_NGHIỆM",
    "BUN": "TÊN_XÉT_NGHIỆM",
    "Creatinine": "TÊN_XÉT_NGHIỆM",
    "Glucose": "TÊN_XÉT_NGHIỆM",
    "HbA1c": "TÊN_XÉT_NGHIỆM",
    "TSH": "TÊN_XÉT_NGHIỆM",
    "FT4": "TÊN_XÉT_NGHIỆM",
    "BNP": "TÊN_XÉT_NGHIỆM",
    "Troponin": "TÊN_XÉT_NGHIỆM",
    "D-dimer": "TÊN_XÉT_NGHIỆM",
    "PT": "TÊN_XÉT_NGHIỆM",
    "INR": "TÊN_XÉT_NGHIỆM",
    "aPTT": "TÊN_XÉT_NGHIỆM",
    "Na": "TÊN_XÉT_NGHIỆM",
    "K": "TÊN_XÉT_NGHIỆM",
    "Cl": "TÊN_XÉT_NGHIỆM",
    "Ca": "TÊN_XÉT_NGHIỆM",
    "Iron": "TÊN_XÉT_NGHIỆM",
    "Amylase": "TÊN_XÉT_NGHIỆM",
    "Lipase": "TÊN_XÉT_NGHIỆM",
    "CK": "TÊN_XÉT_NGHIỆM",
    "CK-MB": "TÊN_XÉT_NGHIỆM",
    "LDH": "TÊN_XÉT_NGHIỆM",
    "ECG": "TÊN_XÉT_NGHIỆM",
    "EKG": "TÊN_XÉT_NGHIỆM",
    "CXR": "TÊN_XÉT_NGHIỆM",
    "CT": "TÊN_XÉT_NGHIỆM",
    "MRI": "TÊN_XÉT_NGHIỆM",
    "Echo": "TÊN_XÉT_NGHIỆM",
    "UA": "TÊN_XÉT_NGHIỆM",
}

# Patterns that indicate test results (numbers with/without units)
RESULT_PATTERNS = [
    re.compile(r'^\d+\.?\d*\s*(mg/dL|mmol/L|mEq/L|g/dL|U/L|ng/mL|pg/mL|µmol/L|mmHg|%|bpm)$'),
    re.compile(r'^\d+[,\.]\d+$'),
    re.compile(r'^\d+\s*-\s*\d+$'),  # range like "3.5-5.0"
    re.compile(r'^[<>]?\s*\d+\.?\d*$'),  # "< 5.0"
]

# Drug indicators
DRUG_INDICATORS = [
    r'\bmg\b', r'\bmcg\b', r'\bml\b', r'\btablet\b', r'\bcapsule\b',
    r'\binjection\b', r'\binhaler\b', r'\bdrops\b', r'\bcream\b',
    r'\bviên\b', r'\bống\b', r'\bgói\b', r'\btúi\b',
    r'\bpo\b', r'\biv\b', r'\bim\b', r'\bsc\b',
    r'\btid\b', r'\bbid\b', r'\bqd\b', r'\bqid\b', r'\bprn\b',
]


def fix_entity_type(entity: Dict) -> Dict:
    """Fix entity type based on rules."""
    text = entity.get("text", "")
    etype = entity.get("type", "")

    # Check if text matches a known lab test
    text_upper = text.strip()
    if text_upper in TYPE_CONSTRAINTS:
        if etype != TYPE_CONSTRAINTS[text_upper]:
            entity["type"] = TYPE_CONSTRAINTS[text_upper]
            entity["type_fixed_by"] = "lab_test_lookup"
            return entity

    # Check if entity is a number with units -> should be test result
    if etype == "TÊN_XÉT_NGHIỆM":
        for pattern in RESULT_PATTERNS:
            if pattern.match(text.strip()):
                entity["type"] = "KẾT_QUẢ_XÉT_NGHIỆM"
                entity["type_fixed_by"] = "result_pattern"
                return entity

    # Check if entity looks like a drug
    if etype in ["TRIỆU_CHỨNG", "CHẨN_ĐOÁN"]:
        text_lower = text.lower()
        is_drug = False
        for indicator in DRUG_INDICATORS:
            if re.search(indicator, text_lower):
                is_drug = True
                break
        if is_drug:
            entity["type"] = "THUỐC"
            entity["type_fixed_by"] = "drug_indicator"
            return entity

    # Check if pure number is mistakenly marked as diagnosis
    if etype == "CHẨN_ĐOÁN":
        if re.match(r'^\d+\.?\d*\s*(mg/dL|mmol/L|%)?$', text.strip()):
            entity["type"] = "KẾT_QUẢ_XÉT_NGHIỆM"
            entity["type_fixed_by"] = "number_fix"
            return entity

    return entity


def remove_overlapping_entities(entities: List[Dict]) -> List[Dict]:
    """Remove overlapping entities, keeping the longer/better one."""
    if not entities:
        return entities

    # Sort by position
    entities.sort(key=lambda x: (x["position"][0], -x["position"][1]))

    filtered = [entities[0]]
    for ent in entities[1:]:
        last = filtered[-1]
        # Check overlap
        if ent["position"][0] < last["position"][1]:
            # Overlapping - keep the one with higher confidence or longer span
            ent_len = ent["position"][1] - ent["position"][0]
            last_len = last["position"][1] - last["position"][0]

            ent_conf = ent.get("confidence", 0)
            last_conf = last.get("confidence", 0)

            # Prefer longer span, then higher confidence
            if ent_len > last_len or (ent_len == last_len and ent_conf > last_conf):
                filtered[-1] = ent
        else:
            filtered.append(ent)

    return filtered


def expand_synonyms(entity: Dict, synonym_dict: Dict = None) -> List[str]:
    """Expand entity text with synonyms for better linking."""
    if not synonym_dict:
        return []

    text_lower = entity["text"].lower()
    synonyms = []

    for group in synonym_dict.get("synonym_groups", []):
        if text_lower in [s.lower() for s in group.get("synonyms", [])]:
            synonyms.extend(group.get("synonyms", []))
        if text_lower == group.get("standard", "").lower():
            synonyms.extend(group.get("synonyms", []))

    return list(set(synonyms))


# ============================================================
# JSON VALIDATION
# ============================================================

def validate_output(text: str, entities: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    Validate output JSON structure and fix issues.
    Returns (validated_entities, warnings).
    """
    warnings = []
    validated = []

    for ent in entities:
        # Required fields
        if not ent.get("text"):
            warnings.append(f"Entity missing text: {ent}")
            continue

        if not ent.get("type"):
            warnings.append(f"Entity missing type: {ent.get('text', '')}")
            continue

        if ent["type"] not in ["TRIỆU_CHỨNG", "THUỐC", "CHẨN_ĐOÁN", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"]:
            warnings.append(f"Invalid type '{ent['type']}' for '{ent.get('text', '')}'")
            continue

        # Position validation
        position = ent.get("position", [-1, -1])
        if position[0] < 0 or position[1] <= position[0]:
            warnings.append(f"Invalid position for '{ent.get('text', '')}': {position}")
            continue

        if position[1] > len(text):
            warnings.append(f"Position exceeds text length for '{ent.get('text', '')}': {position}")
            continue

        # Verify substring
        actual = text[position[0]:position[1]]
        if actual.lower() != ent["text"].lower():
            warnings.append(f"Substring mismatch for '{ent.get('text', '')}': '{actual}'")
            # Try to fix
            idx = text.lower().find(ent["text"].lower())
            if idx >= 0:
                ent["position"] = [idx, idx + len(ent["text"])]
                ent["text"] = text[idx:idx + len(ent["text"])]

        # Validate assertions
        assertions = ent.get("assertions", [])
        valid_assertions = ["isNegated", "isFamily", "isHistorical"]
        ent["assertions"] = [a for a in assertions if a in valid_assertions]

        # Validate candidates
        candidates = ent.get("candidates", [])
        ent["candidates"] = [str(c) for c in candidates if c]

        # Ensure position matches text exactly
        ent["text"] = text[ent["position"][0]:ent["position"][1]]

        validated.append(ent)

    return validated, warnings


def format_output(text: str, entities: List[Dict]) -> List[Dict]:
    """Format entities into final output format."""
    output = []
    for ent in entities:
        output.append({
            "text": ent["text"],
            "type": ent["type"],
            "candidates": ent.get("candidates", []),
            "assertions": ent.get("assertions", []),
            "position": ent["position"],
        })
    return output


# ============================================================
# POST-PROCESSING PIPELINE
# ============================================================

def postprocess(
    text: str,
    entities: List[Dict],
    synonym_dict: Dict = None,
) -> List[Dict]:
    """Full post-processing pipeline."""
    # 1. Fix entity types
    entities = [fix_entity_type(e) for e in entities]

    # 2. Remove overlapping entities
    entities = remove_overlapping_entities(entities)

    # 3. Validate and fix positions
    entities, warnings = validate_output(text, entities)
    for w in warnings:
        print(f"  WARNING: {w}")

    # 4. Format output
    output = format_output(text, entities)

    return output
