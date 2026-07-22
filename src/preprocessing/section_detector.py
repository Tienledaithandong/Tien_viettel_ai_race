"""
Module 1: Clinical Text Section Detector
Detects sections like: thuốc trước nhập viện, tiền sử, xét nghiệm, chẩn đoán, etc.
Section context helps assertion detection and type classification.
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Section:
    name: str
    start: int
    end: int
    header: str


# Section header patterns (Vietnamese clinical text)
SECTION_PATTERNS = [
    # Drug lists
    (re.compile(r'danh\s+sách\s+thuốc\s+trước\s+nhập\s+viện', re.I), "MEDICATIONS_BEFORE_ADMISSION"),
    (re.compile(r'thuốc\s+trước\s+nhập\s+viện', re.I), "MEDICATIONS_BEFORE_ADMISSION"),
    (re.compile(r'thuốc\s+đang\s+dùng', re.I), "CURRENT_MEDICATIONS"),
    (re.compile(r'thuốc\s+điều\s+trị', re.I), "TREATMENT_MEDICATIONS"),
    (re.compile(r'đơn\s+thuốc', re.I), "PRESCRIPTION"),
    (re.compile(r'thuốc\s+kháng\s+sinh', re.I), "ANTIBIOTICS"),

    # History
    (re.compile(r'tiền\s+sử\s+bệnh', re.I), "PAST_HISTORY"),
    (re.compile(r'tiền\s+sử', re.I), "PAST_HISTORY"),
    (re.compile(r'bệnh\s+sử', re.I), "MEDICAL_HISTORY"),
    (re.compile(r'tiền\s+sử\s+bệnh\s+gia\s+đình', re.I), "FAMILY_HISTORY"),
    (re.compile(r'gia\s+đình\s+bệnh\s+nhân', re.I), "FAMILY_HISTORY"),
    (re.compile(r'hỏi\s+bệnh', re.I), "HISTORY_OF_ILLNESS"),

    # Current condition
    (re.compile(r'tình\s+trạng\s+hiện\s+tại', re.I), "CURRENT_CONDITION"),
    (re.compile(r'hiện\s+tại', re.I), "CURRENT_CONDITION"),
    (re.compile(r'vào\s+viện', re.I), "ADMISSION"),
    (re.compile(r'nhập\s+viện', re.I), "ADMISSION"),

    # Examination
    (re.compile(r'khám\s+lâm\s+sàng', re.I), "CLINICAL_EXAMINATION"),
    (re.compile(r'khám\s+bệnh', re.I), "CLINICAL_EXAMINATION"),
    (re.compile(r'thăm\s+khám', re.I), "CLINICAL_EXAMINATION"),
    (re.compile(r'triệu\s+chứng\s+lâm\s+sàng', re.I), "CLINICAL_SYMPTOMS"),

    # Diagnosis
    (re.compile(r'chẩn\s+đoán', re.I), "DIAGNOSIS"),
    (re.compile(r'chẩn\s+đoán\s+nhập\s+viện', re.I), "ADMISSION_DIAGNOSIS"),
    (re.compile(r'chẩn\s+đoán\s+xuất\s+viện', re.I), "DISCHARGE_DIAGNOSIS"),
    (re.compile(r'chẩn\s+đoán\s+ban\s+đầu', re.I), "INITIAL_DIAGNOSIS"),

    # Lab tests
    (re.compile(r'xét\s+nghiệm', re.I), "LAB_TESTS"),
    (re.compile(r'kết\s+quả\s+xét\s+nghiệm', re.I), "LAB_RESULTS"),
    (re.compile(r'tổng\s+phân\s+tích\s+tế\s+bào\s+máu', re.I), "CBC"),
    (re.compile(r'sinh\s+hiệu', re.I), "VITAL_SIGNS"),
    (re.compile(r'cận\s+lâm\s+sàng', re.I), "PARACLINICAL"),

    # Imaging
    (re.compile(r'chẩn\s+đoán\s+hình\s+ảnh', re.I), "IMAGING"),
    (re.compile(r'x-quang', re.I), "XRAY"),
    (re.compile(r'ct\s+scan', re.I), "CT_SCAN"),
    (re.compile(r'mri', re.I), "MRI"),
    (re.compile(r'siêu\s+âm', re.I), "ULTRASOUND"),

    # Discharge
    (re.compile(r'xuất\s+viện', re.I), "DISCHARGE"),
    (re.compile(r'tình\s+trạng\s+xuất\s+viện', re.I), "DISCHARGE_CONDITION"),
    (re.compile(r'hướng\s+dẫn', re.I), "DISCHARGE_INSTRUCTIONS"),
]


def detect_sections(text: str) -> List[Section]:
    """Detect clinical sections in text based on header patterns."""
    sections = []
    lines = text.split('\n')

    current_pos = 0
    for line in lines:
        line_stripped = line.strip()
        for pattern, section_name in SECTION_PATTERNS:
            if pattern.search(line_stripped):
                sections.append(Section(
                    name=section_name,
                    start=current_pos,
                    end=current_pos + len(line),
                    header=line_stripped,
                ))
                break
        current_pos += len(line) + 1  # +1 for newline

    # Assign end positions
    for i in range(len(sections) - 1):
        sections[i].end = sections[i + 1].start
    if sections:
        sections[-1].end = len(text)

    return sections


def get_section_for_position(sections: List[Section], position: int) -> Optional[Section]:
    """Get the section containing a given position."""
    for section in sections:
        if section.start <= position < section.end:
            return section
    return None


def get_section_context(text: str, position: int, window: int = 200) -> str:
    """Get surrounding context for a position, up to section boundaries."""
    start = max(0, position - window)
    end = min(len(text), position + window)
    return text[start:end]


def is_in_medication_section(sections: List[Section], position: int) -> bool:
    """Check if position is in a medication section."""
    section = get_section_for_position(sections, position)
    if section:
        return section.name in [
            "MEDICATIONS_BEFORE_ADMISSION",
            "CURRENT_MEDICATIONS",
            "TREATMENT_MEDICATIONS",
            "PRESCRIPTION",
        ]
    return False


def is_in_history_section(sections: List[Section], position: int) -> bool:
    """Check if position is in a history section."""
    section = get_section_for_position(sections, position)
    if section:
        return section.name in [
            "PAST_HISTORY",
            "MEDICAL_HISTORY",
            "FAMILY_HISTORY",
        ]
    return False


def is_in_diagnosis_section(sections: List[Section], position: int) -> bool:
    """Check if position is in a diagnosis section."""
    section = get_section_for_position(sections, position)
    if section:
        return section.name in [
            "DIAGNOSIS",
            "ADMISSION_DIAGNOSIS",
            "DISCHARGE_DIAGNOSIS",
            "INITIAL_DIAGNOSIS",
        ]
    return False
