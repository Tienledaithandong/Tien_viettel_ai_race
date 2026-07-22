"""
Module 8: JSON Validator + Format Checker
Ensures output matches competition format exactly.
"""
import json
import os
from typing import List, Dict, Tuple


VALID_TYPES = [
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    "CHẨN_ĐOÁN",
    "THUỐC",
]

VALID_ASSERTIONS = ["isNegated", "isFamily", "isHistorical"]


def validate_entity(raw_text: str, entity: dict, idx: int) -> Tuple[bool, str]:
    """Validate a single entity. Returns (is_valid, error_message)."""
    # Required fields
    for field in ["text", "type", "position"]:
        if field not in entity:
            return False, f"Entity {idx}: missing field '{field}'"

    text = entity["text"]
    etype = entity["type"]
    position = entity["position"]

    # Type validation
    if etype not in VALID_TYPES:
        return False, f"Entity {idx}: invalid type '{etype}'"

    # Position validation
    if not isinstance(position, list) or len(position) != 2:
        return False, f"Entity {idx}: position must be [start, end]"

    start, end = position
    if not isinstance(start, int) or not isinstance(end, int):
        return False, f"Entity {idx}: position must be integers"

    if start < 0 or end <= start:
        return False, f"Entity {idx}: invalid position [{start}, {end}]"

    if end > len(raw_text):
        return False, f"Entity {idx}: position end {end} exceeds text length {len(raw_text)}"

    # Text must be exact substring
    actual = raw_text[start:end]
    if actual != text:
        return False, f"Entity {idx}: text mismatch '{text}' != '{actual}'"

    # Assertions validation
    assertions = entity.get("assertions", [])
    if not isinstance(assertions, list):
        return False, f"Entity {idx}: assertions must be a list"

    for a in assertions:
        if a not in VALID_ASSERTIONS:
            return False, f"Entity {idx}: invalid assertion '{a}'"

    # Candidates validation
    candidates = entity.get("candidates", [])
    if not isinstance(candidates, list):
        return False, f"Entity {idx}: candidates must be a list"

    # Candidates should only be for CHẨN_ĐOÁN and THUỐC
    if etype not in ["CHẨN_ĐOÁN", "THUỐC"] and candidates:
        return False, f"Entity {idx}: candidates should be empty for type '{etype}'"

    # Check for duplicate positions
    for c in candidates:
        if not isinstance(c, str):
            return False, f"Entity {idx}: candidate must be string"

    return True, ""


def validate_output(raw_text: str, entities: List[dict]) -> Tuple[List[dict], List[str]]:
    """
    Validate and fix output entities.
    Returns (valid_entities, warnings).
    """
    warnings = []
    valid_entities = []

    seen_positions = set()

    for idx, entity in enumerate(entities):
        is_valid, error = validate_entity(raw_text, entity, idx)

        if is_valid:
            # Check for duplicate position
            pos_key = (entity["position"][0], entity["position"][1], entity["type"])
            if pos_key in seen_positions:
                warnings.append(f"Entity {idx}: duplicate position+type, skipping")
                continue
            seen_positions.add(pos_key)
            valid_entities.append(entity)
        else:
            warnings.append(error)

    # Sort by position
    valid_entities.sort(key=lambda x: (x["position"][0], x["position"][1]))

    return valid_entities, warnings


def format_output_json(entities: List[dict]) -> str:
    """Format entities as competition JSON output."""
    output = []
    for ent in entities:
        output.append({
            "text": ent["text"],
            "type": ent["type"],
            "candidates": ent.get("candidates", []),
            "assertions": ent.get("assertions", []),
            "position": ent["position"],
        })
    return json.dumps(output, ensure_ascii=False, indent=2)


def save_output(entities: List[dict], output_path: str):
    """Save entities to JSON file."""
    output = format_output_json(entities)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)
