"""
Position Alignment Module
Ensures NER output text matches exact substring in input.
Uses RapidFuzz for fuzzy matching when LLM output doesn't perfectly align.
"""
import re
from typing import List, Dict, Tuple, Optional

try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from difflib import SequenceMatcher
    HAS_DIFFLIB = True
except ImportError:
    HAS_DIFFLIB = False


def find_exact_position(original_text: str, entity_text: str) -> Optional[Tuple[int, int]]:
    """Find exact position of entity_text in original_text."""
    if not entity_text or not original_text:
        return None

    # Try exact match first
    idx = original_text.find(entity_text)
    if idx >= 0:
        return (idx, idx + len(entity_text))

    # Case-insensitive match
    idx = original_text.lower().find(entity_text.lower())
    if idx >= 0:
        return (idx, idx + len(entity_text))

    return None


def fuzzy_find_position(
    original_text: str,
    entity_text: str,
    threshold: float = 70.0,
) -> Optional[Tuple[int, int]]:
    """Fuzzy find position using RapidFuzz or difflib."""
    # Try exact first
    exact = find_exact_position(original_text, entity_text)
    if exact:
        return exact

    if HAS_RAPIDFUZZ:
        return _rapidfuzz_find(original_text, entity_text, threshold)
    elif HAS_DIFFLIB:
        return _difflib_find(original_text, entity_text, threshold)
    return None


def _rapidfuzz_find(
    original_text: str,
    entity_text: str,
    threshold: float = 70.0,
) -> Optional[Tuple[int, int]]:
    """Use RapidFuzz to find best fuzzy match position."""
    # Split into words and find best substring match
    entity_lower = entity_text.lower()

    # Try sliding window approach
    best_score = 0
    best_pos = None

    # For short texts, use direct search
    if len(original_text) < 5000:
        results = rfprocess.extract(
            entity_lower,
            [original_text[i:i+len(entity_text)*2]
             for i in range(0, len(original_text), max(1, len(entity_text)//2))],
            scorer=fuzz.partial_ratio,
            limit=5,
        )
        for match_text, score, idx in results:
            if score >= threshold:
                # Reconstruct position
                actual_idx = idx * max(1, len(entity_text)//2)
                actual_end = min(actual_idx + len(entity_text), len(original_text))
                actual_text = original_text[actual_idx:actual_end]

                # Try to find exact start
                search_start = max(0, actual_idx - len(entity_text))
                search_end = min(len(original_text), actual_idx + len(entity_text) * 2)
                search_region = original_text[search_start:search_end]

                exact_in_region = search_region.find(entity_text)
                if exact_in_region >= 0:
                    abs_start = search_start + exact_in_region
                    return (abs_start, abs_start + len(entity_text))

                # Use fuzzy match position
                if score > best_score:
                    best_score = score
                    best_pos = (actual_idx, actual_idx + len(actual_text))

    if best_score >= threshold and best_pos:
        return best_pos

    return None


def _difflib_find(
    original_text: str,
    entity_text: str,
    threshold: float = 70.0,
) -> Optional[Tuple[int, int]]:
    """Use difflib to find best match position."""
    sm = SequenceMatcher(None, original_text.lower(), entity_text.lower(), autojunk=False)

    best_ratio = 0
    best_match = None

    for block in sm.get_matching_blocks():
        if block.size < 3:
            continue

        match_text = original_text[block.a:block.a + block.size]
        ratio = SequenceMatcher(None, match_text.lower(), entity_text.lower()).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            # Try to extend match to full entity length
            start = block.a
            # Try to align start
            for offset in range(-3, 4):
                test_start = start + offset
                if test_start < 0:
                    continue
                test_end = test_start + len(entity_text)
                if test_end > len(original_text):
                    continue
                test_text = original_text[test_start:test_end]
                test_ratio = SequenceMatcher(None, test_text.lower(), entity_text.lower()).ratio()
                if test_ratio > best_ratio:
                    best_ratio = test_ratio
                    best_match = (test_start, test_end)

    if best_ratio * 100 >= threshold and best_match:
        return best_match

    return None


def align_all_positions(
    original_text: str,
    entities: List[Dict],
    fuzzy_threshold: float = 70.0,
) -> List[Dict]:
    """
    Align all entity positions to original text.
    Returns entities with corrected positions and texts.
    """
    aligned = []

    for entity in entities:
        entity_text = entity.get("text", "")
        position = entity.get("position", [-1, -1])
        etype = entity.get("type", "")

        # First try: use provided position
        if position[0] >= 0 and position[1] > position[0]:
            substring = original_text[position[0]:position[1]]
            # Check if it matches (case-insensitive)
            if substring.lower() == entity_text.lower():
                aligned.append({
                    **entity,
                    "text": substring,  # Use exact substring
                    "position": [position[0], position[1]],
                    "alignment": "exact",
                })
                continue

            # Position might be from normalized text
            exact = find_exact_position(original_text, entity_text)
            if exact:
                aligned.append({
                    **entity,
                    "text": original_text[exact[0]:exact[1]],
                    "position": [exact[0], exact[1]],
                    "alignment": "text_match",
                })
                continue

        # Second try: find exact position
        exact = find_exact_position(original_text, entity_text)
        if exact:
            aligned.append({
                **entity,
                "text": original_text[exact[0]:exact[1]],
                "position": [exact[0], exact[1]],
                "alignment": "exact_search",
            })
            continue

        # Third try: fuzzy match
        fuzzy_pos = fuzzy_find_position(original_text, entity_text, fuzzy_threshold)
        if fuzzy_pos:
            aligned_text = original_text[fuzzy_pos[0]:fuzzy_pos[1]]
            aligned.append({
                **entity,
                "text": aligned_text,
                "position": [fuzzy_pos[0], fuzzy_pos[1]],
                "alignment": "fuzzy",
            })
            continue

        # Skip if can't align
        print(f"  WARNING: Could not align '{entity_text}' ({etype}) to original text")

    return aligned


def validate_positions(text: str, entities: List[Dict]) -> List[Dict]:
    """Validate and fix all entity positions."""
    valid = []
    for ent in entities:
        start, end = ent.get("position", [-1, -1])
        ent_text = ent.get("text", "")

        if start < 0 or end <= start or end > len(text):
            continue

        # Verify substring matches
        actual = text[start:end]
        if actual.lower() == ent_text.lower():
            valid.append(ent)
        else:
            # Try to fix
            fixed_pos = find_exact_position(text, ent_text)
            if fixed_pos:
                ent["text"] = text[fixed_pos[0]:fixed_pos[1]]
                ent["position"] = [fixed_pos[0], fixed_pos[1]]
                valid.append(ent)

    return valid
