"""
Module 2: Rule-based Extractor (Rewritten)
Tight regex patterns for drug/lab/symptom/diagnosis extraction.
"""
import re
import os
from typing import List
from dataclasses import dataclass, field

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Mention:
    text: str
    start: int
    end: int
    type: str
    source: str = "rule"
    confidence: float = 1.0
    assertions: list = field(default_factory=list)
    candidates: list = field(default_factory=list)


# ============================================================
# DRUG PATTERNS (require strength unit: mg, g, ml, etc.)
# ============================================================
DRUG_STRENGTH = r'\d+(?:[.,]\d+)?\s*(?:mg|g|ml|mcg|µg|UI|IU|mEq|mmol)(?:\s*/\s*(?:ml|mg|g))?'
DRUG_ROUTE_FREQ = r'(?:\s+(?:po|iv|im|sc|sl|inh|prn|daily|bid|tid|qid|q\d+h|qd|:\s*prn))*'

DRUG_EXACT = re.compile(
    rf'(?:^|(?<=[\s,;]))'
    rf'((?:[A-Z][a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ]+(?:[- ][A-Z][a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ]+)*))'
    rf'\s+({DRUG_STRENGTH})'
    rf'{DRUG_ROUTE_FREQ}?',
)

DRUG_WITH_BRAND = re.compile(
    rf'([A-Z][A-Za-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ]+)'
    rf'\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml|mcg)(?:\s*/\s*(?:ml|mg|g))?',
    re.IGNORECASE
)

# Known drug names (common Vietnamese/English drugs)
KNOWN_DRUGS = [
    "Paracetamol", "Ibuprofen", "Amoxicillin", "Azithromycin", "Cefuroxime",
    "Metformin", "Gliclazide", "Amlodipine", "Losartan", "Valsartan",
    "Atorvastatin", "Rosuvastatin", "Omeprazole", "Pantoprazole", "Esomeprazole",
    "Levothyroxine", "Prednisolone", "Dexamethasone", "Methylprednisolone",
    "Salbutamol", "Montelukast", "Desloratadine", "Cetirizine", "Loratadine",
    "Chlorpheniramine", "Diphenhydramine", "Ranitidine", "Famotidine",
    "Metoclopramide", "Domperidone", "Loperamide", "ORS",
    "Warfarin", "Clopidogrel", "Aspirin", "Enoxaparin", "Heparin",
    "Insulin", "Glargine", "Lispro", "Aspart",
    "Tramadol", "Codeine", "Morphine", "Diclofenac", "Naproxen",
    "Cephalexin", "Ciprofloxacin", "Levofloxacin", "Doxycycline", "Clindamycin",
    "Metronidazole", "Fluconazole", "Acyclovir", "Oseltamivir",
    "Atenolol", "Bisoprolol", "Metoprolol", "Carvedilol", "Propranolol",
    "Furosemide", "Spironolactone", "Hydrochlorothiazide", "Indapamide",
    "Nifedipine", "Diltiazem", "Verapamil", "Doxazosin", "Prazosin",
    "Tamsulosin", "Finasteride", "Sildenafil", "Tadalafil",
    "Levodopa", "Carbidopa", "Benserazide",
    "Carbamazepine", "Valproic acid", "Phenytoin", "Lamotrigine", "Levetiracetam",
    "Sertraline", "Fluoxetine", "Escitalopram", "Venlafaxine", "Duloxetine",
    "Amitriptyline", "Mirtazapine", "Trazodone", "Quetiapine", "Risperidone",
    "Olanzapine", "Haloperidol", "Lithium", "Buspirone",
    "Lactulose", "Macrogol", "Bisacodyl", "Sennoside",
    "Ezetimibe", "Fenofibrate", "Omega-3",
    "Capsaicin", "Benzydamine", "Thiocolchicoside",
    "Allopurinol", "Colchicine",
    "Iron", "Folic acid", "Vitamin D", "Calcium",
    "Iron sucrose", "Epoetin",
    "Gleevec", "Imatinib",
    "Methadone", "Buprenorphine",
    "Morphine", "Tramadol", "Codeine",
    "Ciprofloxacin", "Levofloxacin",
    "Vancomycin", "Meropenem",
    "Ceftriaxone", "Cefotaxime", "Cefazolin",
    "Piperacillin", "Tazobactam",
    "Fluconazole", "Voriconazole",
    "Prednisone", "Methylprednisolone",
    "Cyclophosphamide", "Methotrexate", "5-Fluorouracil",
    "Doxorubicin", "Paclitaxel", "Carboplatin",
    "Tamoxifen", "Letrozole", "Anastrozole",
    "Sorafenib", "Sunitinib",
    "Lisinopril", "Ramipril", "Enalapril",
    "Simvastatin", "Pravastatin",
    "Clopidogrel", "Prasugrel", "Ticagrelor",
    "Apixaban", "Rivaroxaban", "Dabigatran",
    "Digoxin", "Amiodarone", "Diltiazem",
    "Nitroglycerin", "Isosorbide", "Hydralazine",
    "Albuterol", "Ipratropium", "Fluticasone",
    "Montelukast", "Zafirlukast",
    "Ondansetron", "Granisetron",
    "Docusate", "Polyethylene glycol",
    "Lorazepam", "Diazepam", "Midazolam",
    "Zolpidem", "Melatonin",
    "Gabapentin", "Pregabalin",
    "Duloxetine", "Amitriptyline",
    "Celecoxib", "Naproxen",
    "Colchicine", "Allopurinol", "Febuxostat",
    "Mycophenolate", "Azathioprine", "Tacrolimus", "Cyclosporine",
    "Bumetanide", "Hydromorphone", "Ranolazine",
    "Guaifenesin", "Pseudoephedrine",
    "Coumadin", "Lasix", "Laxis", "Tylenol",
    "Prograf", "Dilaudid", "Ranexa",
    "Acetaminophen", "Acetaminophen",
    "Heparin", "Enoxaparin", "Warfarin",
]

DRUG_KNOWN = re.compile(
    rf'(?:(?<=[\s,;])|(?<=^))'
    rf'({"|".join(re.escape(d) for d in KNOWN_DRUGS)})'
    rf'(?:\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml|mcg)(?:\s*/\s*(?:ml|mg|g))?)?',
    re.IGNORECASE
)

# Drug mentions after "Thuốc" or "đang dùng" or "điều trị"
DRUG_CONTEXT_PATTERN = re.compile(
    r'(?:thuốc\s+(?:đang\s+)?(?:dùng|điều\s+trị|sử\s+dùng)|'
    r'đang\s+dùng|điều\s+trị\s+bằng)\s*'
    r'(?:theo\s+đơn\s*)?(?::\s*)?'
    r'([^\n]+)',
    re.IGNORECASE
)


def extract_drugs(text: str) -> List[Mention]:
    """Extract drug mentions. REQUIRE strength unit to avoid false positives."""
    mentions = []
    seen_spans = set()

    for match in DRUG_EXACT.finditer(text):
        full = match.group(0).strip()
        start, end = match.start(), match.start() + len(full)
        span_key = (start, end)
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            mentions.append(Mention(
                text=full, start=start, end=end,
                type="THUỐC", source="rule_drug", confidence=0.9,
            ))

    for match in DRUG_KNOWN.finditer(text):
        full = match.group(0).strip()
        start, end = match.start(), match.start() + len(full)
        span_key = (start, end)
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            mentions.append(Mention(
                text=full, start=start, end=end,
                type="THUỐC", source="rule_drug_known", confidence=0.95,
            ))

    # Extract from context patterns like "Thuốc đang dùng: ..."
    for match in DRUG_CONTEXT_PATTERN.finditer(text):
        line = match.group(1).strip()
        parts = re.split(r'[,;]+', line)
        for part in parts:
            part = part.strip()
            if len(part) < 3:
                continue
            # Check if part contains any known drug
            for drug in KNOWN_DRUGS:
                if drug.lower() in part.lower():
                    idx = text.lower().find(drug.lower(), match.start(1))
                    if idx != -1:
                        # Try to get full drug mention (name + strength)
                        rest = text[idx:match.end(1)]
                        drug_match = re.search(
                            re.escape(drug) + r'(?:\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml|mcg)(?:\s*/\s*(?:ml|mg|g))?)?',
                            rest, re.I
                        )
                        if drug_match:
                            full = drug_match.group(0)
                            span_key = (idx, idx + len(full))
                            if span_key not in seen_spans:
                                seen_spans.add(span_key)
                                mentions.append(Mention(
                                    text=full, start=idx, end=idx + len(full),
                                    type="THUỐC", source="rule_drug_context", confidence=0.9,
                                ))
                    break

    return mentions


# ============================================================
# LAB TEST PATTERNS
# ============================================================
LAB_TEST_NAMES = [
    "WBC", "RBC", "HGB", "HCT", "PLT",
    "NEUT%", "LYPH%", "MONO%", "EOS%", "BASO%",
    "CRP", "ESR", "BSR", "PCT",
    "AST", "ALT", "GGT", "ALP",
    "Bilirubin", "Creatinine", "BUN",
    "Glucose", "HbA1c",
    "HDL", "LDL",
    "TSH", "FT3", "FT4",
    "BNP", "NT-proBNP", "Troponin",
    "D-dimer",
    "INR", "aPTT", "APTT",
    "Fibrinogen",
    "Amylase", "Lipase",
    "CPK", "CK-MB", "LDH",
    "AFP", "CEA", "CA-125", "CA 19-9",
    "HBsAg",
]

# Short lab tests that need exact case matching
LAB_SHORT_TESTS = re.compile(
    r'(?:^|(?<=\s)|(?<=\())'
    r'(Na|K|Cl|Ca|Mg|Fe|TC|TG|PT|CK|PSA)'
    r'(?=\s|:|;|$|\)|\d)',
)

# Case-insensitive lab tests (longer names)
LAB_TESTS_SORTED = sorted(LAB_TEST_NAMES, key=len, reverse=True)
LAB_TEST_PATTERN = re.compile(
    r'(?:^|(?<=\s)|(?<=\())'
    + '|'.join(re.escape(t) for t in LAB_TESTS_SORTED)
    + r'(?=\s|:|;|$|\)|\d)',
    re.IGNORECASE
)

# Lab result: Name (optional description): value
LAB_RESULT_PATTERN = re.compile(
    r'([A-Za-z0-9%\-/]+(?:\s*\([^)]+\))?)\s*:\s*([<>]?\s*\d+[.,]?\d*(?:\s*-\s*\d+[.,]?\d*)?)\s*(mg/dL|mmol/L|mEq/L|g/dL|U/L|ng/mL|pg/mL|%|bpm|/mm3|\.10\^3|\.10\^9|fL|pg)?',
    re.IGNORECASE
)


def extract_lab_tests(text: str) -> List[Mention]:
    """Extract lab test names and results."""
    mentions = []
    seen_spans = set()

    # Lab result: Name: value (higher priority)
    for match in LAB_RESULT_PATTERN.finditer(text):
        name_text = match.group(1).strip()
        value_text = match.group(2).strip()
        unit = match.group(3) or ""

        # Skip if name is too short or looks like normal text
        if len(name_text) < 2:
            continue

        name_start = match.start(1)
        name_end = match.end(1)
        result_start = match.start(2)
        result_end = match.end(2) + (len(unit) + 1 if unit else 0)

        span_key = (name_start, name_end)
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            mentions.append(Mention(
                text=name_text, start=name_start, end=name_end,
                type="TÊN_XÉT_NGHIỆM", source="rule_lab_result", confidence=0.95,
            ))

        result_span = (result_start, result_end)
        if result_span not in seen_spans:
            seen_spans.add(result_span)
            full_result = f"{value_text} {unit}".strip()
            mentions.append(Mention(
                text=full_result, start=result_start, end=result_end,
                type="KẾT_QUẢ_XÉT_NGHIỆM", source="rule_lab_result", confidence=0.95,
            ))

    # Standalone lab test names (use case-sensitive short tests first)
    for match in LAB_SHORT_TESTS.finditer(text):
        test_name = match.group(0)
        start, end = match.start(), match.end()
        span_key = (start, end)
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            mentions.append(Mention(
                text=test_name, start=start, end=end,
                type="TÊN_XÉT_NGHIỆM", source="rule_lab", confidence=0.9,
            ))

    for match in LAB_TEST_PATTERN.finditer(text):
        test_name = match.group(0)
        start, end = match.start(), match.end()
        span_key = (start, end)
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            mentions.append(Mention(
                text=test_name, start=start, end=end,
                type="TÊN_XÉT_NGHIỆM", source="rule_lab", confidence=0.9,
            ))

    return mentions


# ============================================================
# SYMPTOM PATTERNS
# ============================================================
SYMPTOM_PHRASES = [
    "ho đờm xanh", "ho đờm vàng", "ho khan", "ho có đờm", "ho ra máu",
    "sốt cao", "sốt nhẹ", "sốt rét rung mình", "sốt",
    "đau đầu", "đau ngực", "đau bụng", "đau thượng vị",
    "đau lưng", "đau cơ", "đau khớp", "đau họng", "đau mắt",
    "đau quanh vết mổ", "đau vùng", "đau dữ dội",
    "khó thở", "khó thở khi gắng sức", "khó thở cấp tính", "khó thở kéo dài",
    "buồn nôn", "nôn mửa", "nôn",
    "tiêu chảy", "táo bón",
    "mệt mỏi", "mệt", "chóng mặt", "hoa mắt",
    "phù nề", "phù chân", "phù mặt",
    "ngứa", "khô mắt", "mất ngủ",
    "sụt cân", "tăng cân",
    "tức ngực", "ợ hơi", "ợ chua",
    "nuốt đau", "nuốt khó", "khàn tiếng", "giọng khàn",
    "sổ mũi", "nghẹt mũi", "hắt hơi",
    "đổ mồ hôi", "rét rung mình", "rét",
    "yếu", "yếu nửa người", "yếu liệt",
    "liệt", "liệt hai chi", "liệt hai chân",
    "chảy máu", "chảy máu cam", "chảy máu mũi",
    "tiểu máu", "tiểu rắt", "tiểu khó", "tiểu buốt", "tiểu tiện không tự chủ",
    "da vàng", "vàng da",
    "khát nước", "饮多", "ăn nhiều",
    "gầy sút", "sút cân",
    "trướng bụng", "đầy bụng", "chướng bụng",
    "đái tháo đường", "tăng huyết áp",
    "hồi hộp", " đánh trống ngực",
    "lú lẫn", "thay đổi ý thức", "giảm ý thức",
    "hạ thân nhiệt", "sốt xuất huyết",
    "viêm", "nhiễm trùng",
    "loét", "hoại tử",
    "đau nhức", "đau âm ỉ", "đau quặn",
    "nóng trong người", "khát",
    "tê bì", "tê", "kiến bò",
    "co giật", "động kinh",
    "mờ mắt", "nhìn mờ", "mất thị lực",
    " ù tai", "điếc",
    "ngất", "ngất xỉu",
    "vết thương", "gãy xương", "chấn thương",
]

# Sort by length descending
SYMPTOM_PHRASES_SORTED = sorted(SYMPTOM_PHRASES, key=len, reverse=True)

# Match symptoms after "- " bullet points or in lists
SYMPTOM_BULLET_PATTERN = re.compile(
    r'-\s+(' + '|'.join(re.escape(s) for s in SYMPTOM_PHRASES_SORTED) + r')',
    re.IGNORECASE
)

# Match "Triệu chứng hiện tại: ..." format
SYMPTOM_HEADING_PATTERN = re.compile(
    r'(?:triệu\s+chứng\s+hiện\s+tại|lý\s+do\s+nhập\s+viện|triệu\s+chứng)\s*:\s*'
    r'([^\n]+)',
    re.IGNORECASE
)

# Match after verbs
SYMPTOM_VERB_PATTERN = re.compile(
    r'(?:bị|có|xuất hiện|gặp phải|đau|nổi)\s+'
    r'(' + '|'.join(re.escape(s) for s in SYMPTOM_PHRASES_SORTED) + r')',
    re.IGNORECASE
)


def extract_symptoms(text: str) -> List[Mention]:
    """Extract symptom mentions using known phrases."""
    mentions = []
    seen_spans = set()

    for pattern in [SYMPTOM_BULLET_PATTERN, SYMPTOM_VERB_PATTERN]:
        for match in pattern.finditer(text):
            symptom = match.group(1).strip()
            start = text.find(symptom, match.start())
            if start == -1:
                continue
            end = start + len(symptom)
            span_key = (start, end)
            if span_key not in seen_spans:
                seen_spans.add(span_key)
                mentions.append(Mention(
                    text=symptom, start=start, end=end,
                    type="TRIỆU_CHỨNG", source="rule_symptom", confidence=0.85,
                ))

    # Extract from "Triệu chứng hiện tại: ..." lines
    for match in SYMPTOM_HEADING_PATTERN.finditer(text):
        line = match.group(1).strip()
        # Extract individual symptoms from the line
        parts = re.split(r'[,;]+', line)
        for part in parts:
            part = part.strip()
            if len(part) < 2 or len(part) > 60:
                continue
            # Check if it matches any known symptom
            for symptom in SYMPTOM_PHRASES_SORTED:
                if symptom.lower() in part.lower():
                    idx = text.lower().find(symptom.lower(), match.start(1))
                    if idx != -1:
                        span_key = (idx, idx + len(symptom))
                        if span_key not in seen_spans:
                            seen_spans.add(span_key)
                            mentions.append(Mention(
                                text=symptom, start=idx, end=idx + len(symptom),
                                type="TRIỆU_CHỨNG", source="rule_symptom_heading", confidence=0.9,
                            ))
                    break
            else:
                # No known symptom match - check if it looks like a symptom (short, medical)
                if 3 <= len(part) <= 40 and not part[0].isdigit():
                    # Check context - is it in a symptom/clinical section
                    pos = match.start(1)
                    section_text = text[max(0, pos-200):pos]
                    if any(kw in section_text.lower() for kw in ['triệu chứng', 'lý do', 'khám', 'đau', 'sốt']):
                        start = text.find(part, match.start(1))
                        if start != -1:
                            span_key = (start, start + len(part))
                            if span_key not in seen_spans:
                                seen_spans.add(span_key)
                                mentions.append(Mention(
                                    text=part, start=start, end=start + len(part),
                                    type="TRIỆU_CHỨNG", source="rule_symptom_infer", confidence=0.7,
                                ))

    return mentions

    return mentions


# ============================================================
# DIAGNOSIS PATTERNS
# ============================================================
DIAGNOSIS_PATTERNS = [
    # "được chẩn đoán ..." or "chẩn đoán ..."
    re.compile(r'(?:được\s+)?chẩn đoán\s+(?:mắc\s+(?:bệnh\s+)?)?(.{5,80}?)(?:[.;]|\s+Treatment|\s+điều\s+trị)', re.I),
    re.compile(r'(?:được\s+)?chẩn đoán\s+(?:mắc\s+(?:bệnh\s+)?)?(.{5,80}?)(?:[.;]|$)', re.I),
    # "Bệnh lý mãn tính: ..."
    re.compile(r'bệnh\s+lý\s+(?:mãn\s+tính|mạn\s+tính)\s*:\s*(.{3,100}?)(?:\n|$)', re.I),
    # "Các bệnh lý mạn tính" followed by bullet list
    re.compile(r'các\s+bệnh\s+(?:lý\s+)?(?:mãn|mạn)\s+tính\s*(?:$|\n)([\s\S]{10,500}?)(?=\n\d\.|\nLịch sử|\nThuốc|\nTiền sử|$)', re.I),
    # Specific diseases
    re.compile(r'bệnh\s+(?:trào\s+ngược|viêm|ung\s+thư|tiểu\s+đường|huyết\s+áp|hen|loét|suy|tắc nghẽn|mạn tính)\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'ung\s+thư\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'tiểu\s+đường\s+(?:typpe?\s*\d+|tuyp\s*\d+|type\s*\d+|típ\s*\d+)', re.I),
    re.compile(r'huyết\s+áp\s+cao', re.I),
    re.compile(r'hen\s+suyễn', re.I),
    re.compile(r'nhồi\s+máu\s+cơ\s+tim', re.I),
    re.compile(r'rung\s+nhĩ', re.I),
    re.compile(r'suy\s+tim', re.I),
    re.compile(r'xơ\s+gan', re.I),
    re.compile(r'bệnh\s+thận\s+mạn', re.I),
    re.compile(r'bệnh\s+tim\s+mạch', re.I),
    re.compile(r'đái\s+tháo\s+đường', re.I),
    re.compile(r'tăng\s+lipid\s+máu', re.I),
    re.compile(r'tăng\s+cholesterol', re.I),
    re.compile(r'bệnh\s+bạch\s+cầu', re.I),
    re.compile(r'viêm\s+phổi', re.I),
    re.compile(r'gãy\s+xương', re.I),
    re.compile(r'chấn\s+thương', re.I),
    re.compile(r'trào\s+ngược\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'nghẽn\s+tắc\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'hẹp\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'ung\s+thư\s+(.{3,60}?)(?:[.;]|,|\s+tái phát)', re.I),
    re.compile(r'di\s+căn\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'tràn\s+dịch\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'nốt\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'tiêu\s+chảy\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'viêm\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'suy\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'loét\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'hoại\s+tử\s+(.{3,60}?)(?:[.;]|$)', re.I),
    re.compile(r'bệnh\s+(.{3,60}?)(?:[.;]|$)', re.I),
]


def extract_diagnoses(text: str) -> List[Mention]:
    """Extract diagnosis mentions."""
    mentions = []
    seen_spans = set()

    for pattern in DIAGNOSIS_PATTERNS:
        for match in pattern.finditer(text):
            full = match.group(0).strip()
            full = re.sub(r'[.;]+$', '', full).strip()
            start = text.find(full, match.start())
            if start == -1:
                continue
            end = start + len(full)
            span_key = (start, end)
            if span_key not in seen_spans and len(full) >= 5:
                seen_spans.add(span_key)
                mentions.append(Mention(
                    text=full, start=start, end=end,
                    type="CHẨN_ĐOÁN", source="rule_diagnosis", confidence=0.85,
                ))

    return mentions


# ============================================================
# MAIN FUNCTION
# ============================================================
def extract_all_rules(text: str) -> List[Mention]:
    """Run all rule-based extractors."""
    mentions = []
    mentions.extend(extract_drugs(text))
    mentions.extend(extract_lab_tests(text))
    mentions.extend(extract_symptoms(text))
    mentions.extend(extract_diagnoses(text))
    return mentions
