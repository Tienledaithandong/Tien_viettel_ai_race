"""
Text Normalization for Vietnamese Clinical Text
- Unicode normalization
- Whitespace cleanup
- Punctuation standardization
- Abbreviation expansion
"""
import re
import unicodedata
from typing import Tuple


# Common noise patterns in clinical text
NOISE_PATTERNS = [
    (re.compile(r'\s+:\s*'), ': '),           # "WBC : 14" -> "WBC: 14"
    (re.compile(r'\s*,\s*'), ', '),           # normalize commas
    (re.compile(r'\s+\.\s*'), '. '),          # normalize periods
    (re.compile(r'\n{3,}'), '\n\n'),          # max 2 newlines
    (re.compile(r'[ \t]{2,}'), ' '),          # multiple spaces -> 1
    (re.compile(r'(\d)[.,](\d)'), r'\1.\2'),  # "14,3" -> "14.3" (decimal)
    (re.compile(r'(\d)\s*mg\b'), r'\1 mg'),   # "500mg" -> "500 mg"
    (re.compile(r'(\d)\s*mcg\b'), r'\1 mcg'),
    (re.compile(r'(\d)\s*ml\b'), r'\1 ml'),
    (re.compile(r'(\d)\s*g\b'), r'\1 g'),
    (re.compile(r'(\d)\s*U\b'), r'\1 U'),
    (re.compile(r'(\d)\s*IU\b'), r'\1 IU'),
    (re.compile(r'(\d)\s*mEq\b'), r'\1 mEq'),
    (re.compile(r'(\d)\s*mmol\b'), r'\1 mmol'),
    (re.compile(r'(\d)\s*µmol\b'), r'\1 µmol'),
]


def normalize_unicode(text: str) -> str:
    """Normalize Vietnamese unicode to NFC form."""
    text = unicodedata.normalize('NFC', text)
    # Fix common encoding issues
    text = text.replace('Đ', 'Đ').replace('đ', 'đ')
    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving structure."""
    # Replace tabs with spaces
    text = text.replace('\t', ' ')
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove trailing whitespace on each line
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_punctuation(text: str) -> str:
    """Standardize punctuation in clinical text."""
    # Fix spacing around colons (common in lab results)
    text = re.sub(r'\s*:\s*', ': ', text)
    # Fix semicolons
    text = re.sub(r'\s*;\s*', '; ', text)
    # Normalize parentheses
    text = re.sub(r'\s*\(\s*', '(', text)
    text = re.sub(r'\s*\)\s*', ')', text)
    return text


def normalize_numbers_and_units(text: str) -> str:
    """Normalize numbers and units for consistency."""
    # Standardize decimal separator (Vietnamese uses comma)
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)
    # Add space between number and unit
    for pattern, replacement in NOISE_PATTERNS[8:]:  # unit patterns
        text = pattern.sub(replacement, text)
    return text


def fix_common_clinical_patterns(text: str) -> str:
    """Fix common patterns in clinical text."""
    # "Bệnh nhân" variants
    text = re.sub(r'\bBN\b', 'bệnh nhân', text)
    # Common abbreviations that should be expanded for NER
    text = re.sub(r'\bvs\b', 'vs', text, flags=re.IGNORECASE)
    return text


def normalize_clinical_text(text: str) -> str:
    """Main normalization pipeline for clinical text."""
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = normalize_punctuation(text)
    text = normalize_numbers_and_units(text)
    text = fix_common_clinical_patterns(text)
    return text


def create_normalization_mapping(original: str, normalized: str) -> list:
    """
    Create character-level mapping between original and normalized text.
    Returns list of (original_start, original_end, normalized_start, normalized_end).
    This is needed for position alignment after NER on normalized text.
    """
    # Simple approach: track character mapping
    mapping = []
    orig_idx = 0
    norm_idx = 0

    orig_chars = list(original)
    norm_chars = list(normalized)

    # Build mapping by tracking which original characters map to which normalized
    # This is a simplified version - for production, use a proper alignment algorithm
    orig_to_norm = {}
    norm_to_orig = {}

    # Use difflib for alignment
    import difflib
    sm = difflib.SequenceMatcher(None, original, normalized)

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for k in range(i2 - i1):
                orig_to_norm[i1 + k] = j1 + k
                norm_to_orig[j1 + k] = i1 + k
        elif op == 'replace':
            # Map proportional
            orig_len = i2 - i1
            norm_len = j2 - j1
            for k in range(max(orig_len, norm_len)):
                orig_pos = i1 + min(k, orig_len - 1)
                norm_pos = j1 + min(k, norm_len - 1)
                orig_to_norm[orig_pos] = norm_pos
                norm_to_orig[norm_pos] = orig_pos
        elif op == 'insert':
            # New characters in normalized
            for k in range(j2 - j1):
                norm_to_orig[j1 + k] = i1
        elif op == 'delete':
            # Characters removed
            for k in range(i2 - i1):
                orig_to_norm[i1 + k] = j1

    return orig_to_norm, norm_to_orig


def remap_positions(
    positions: list,
    norm_to_orig: dict
) -> list:
    """Remap positions from normalized text back to original text."""
    remapped = []
    for start, end in positions:
        orig_start = norm_to_orig.get(start, start)
        orig_end = norm_to_orig.get(end - 1, end - 1) + 1
        remapped.append([orig_start, orig_end])
    return remapped
