"""
Module 5: Improved Assertion Detection
Section-aware + scope-based assertion detection.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


# ============================================================
# TRIGGER PATTERNS
# ============================================================

HISTORICAL_TRIGGERS = [
    re.compile(r'tiền\s+sử', re.I),
    re.compile(r'bệnh\s+sử', re.I),
    re.compile(r'trước\s+đây', re.I),
    re.compile(r'đã\s+từng', re.I),
    re.compile(r'đã\s+có', re.I),
    re.compile(r'đã\s+bị', re.I),
    re.compile(r'đã\s+dùng', re.I),
    re.compile(r'đã\s+uống', re.I),
    re.compile(r'đã\s+điều\s+trị', re.I),
    re.compile(r'đã\s+phẫu\s+thuật', re.I),
    re.compile(r'đã\s+chẩn\s+đoán', re.I),
    re.compile(r'cũ', re.I),
    re.compile(r'lịch\s+sử', re.I),
    re.compile(r'trước\s+nhập\s+viện', re.I),
    re.compile(r'previously', re.I),
    re.compile(r'history\s+of', re.I),
    re.compile(r'h/o', re.I),
    re.compile(r's/p', re.I),
    re.compile(r'status\s+post', re.I),
]

NEGATION_TRIGGERS = [
    re.compile(r'(?:^|(?<=\s))không\s+(?:có\s+)?'),
    re.compile(r'(?:^|(?<=\s))chưa\s+(?:có\s+)?'),
    re.compile(r'(?:^|(?<=\s))chưa\s+từng'),
    re.compile(r'(?:^|(?<=\s))không\s+gặp'),
    re.compile(r'(?:^|(?<=\s))không\s+bị'),
    re.compile(r'(?:^|(?<=\s))không\s+xuất\s+hiện'),
    re.compile(r'(?:^|(?<=\s))không\s+phát\s+hiện'),
    re.compile(r'(?:^|(?<=\s))không\s+ghi\s+nhận'),
    re.compile(r'(?:^|(?<=\s))âm\s+tính'),
    re.compile(r'(?:^|(?<=\s))thiếu'),
    re.compile(r'(?<![a-zA-Z])neg(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])negative(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])deny(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])denies(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])without(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])absent(?![a-zA-Z])'),
]

FAMILY_TRIGGERS = [
    re.compile(r'(?:^|(?<=\s))gia\s+đình\s+'),
    re.compile(r'(?:^|(?<=\s))người\s+nhà\s+'),
    re.compile(r'(?:^|(?<=\s))bố\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?:^|(?<=\s))cha\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?:^|(?<=\s))mẹ\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?:^|(?<=\s))anh\s+trai\s+'),
    re.compile(r'(?:^|(?<=\s))chị\s+gái\s+'),
    re.compile(r'(?:^|(?<=\s))em\s+(?:trai|gái)\s+'),
    re.compile(r'(?:^|(?<=\s))ob\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?:^|(?<=\s))bà\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?:^|(?<=\s))ông\s+(?:bệnh\s+nhân\s+)?'),
    re.compile(r'(?<![a-zA-Z])family(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])mother(?![a-zA-Z])'),
    re.compile(r'(?<![a-zA-Z])father(?![a-zA-Z])'),
]


def detect_historical(
    text: str,
    entity_start: int,
    entity_end: int,
    window: int = 80,
) -> bool:
    """Detect if entity is historical."""
    context_start = max(0, entity_start - window)
    prefix = text[context_start:entity_start]

    for trigger in HISTORICAL_TRIGGERS:
        if trigger.search(prefix):
            return True

    # Check entity text itself
    entity_text = text[entity_start:entity_end].lower()
    if re.match(r'^tiền\s+sử\s+', entity_text):
        return True

    return False


def detect_negation(
    text: str,
    entity_start: int,
    entity_end: int,
    window: int = 50,
) -> bool:
    """Detect if entity is negated."""
    context_start = max(0, entity_start - window)
    prefix = text[context_start:entity_start]

    for trigger in NEGATION_TRIGGERS:
        if trigger.search(prefix):
            return True

    return False


def detect_family(
    text: str,
    entity_start: int,
    entity_end: int,
    window: int = 50,
) -> bool:
    """Detect if entity refers to family member."""
    context_start = max(0, entity_start - window)
    prefix = text[context_start:entity_start]

    for trigger in FAMILY_TRIGGERS:
        if trigger.search(prefix):
            return True

    return False


def detect_all_assertions(
    text: str,
    entity_start: int,
    entity_end: int,
    entity_type: str,
    section_name: str = "",
) -> List[str]:
    """
    Detect all assertions for an entity, considering section context.
    """
    assertions = []

    # Type-specific assertion rules
    valid_assertion_types = ["CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"]
    if entity_type not in valid_assertion_types:
        return []

    # Section-based historical detection
    if section_name in ["MEDICATIONS_BEFORE_ADMISSION", "PAST_HISTORY", "MEDICAL_HISTORY"]:
        if not detect_negation(text, entity_start, entity_end):
            assertions.append("isHistorical")
            return assertions  # Section context is very reliable

    # Rule-based detection
    if detect_negation(text, entity_start, entity_end):
        assertions.append("isNegated")

    if detect_historical(text, entity_start, entity_end):
        assertions.append("isHistorical")

    if detect_family(text, entity_start, entity_end):
        assertions.append("isFamily")

    return assertions
