"""
Assertion Detection Module
Rule-based engine + optional classifier for negation/history/family detection.
"""
import re
from typing import List, Dict, Tuple, Optional


# ============================================================
# RULE-BASED PATTERNS
# NOTE: \b word boundary doesn't work with Vietnamese diacritics.
#       Use (?<![a-z]) or simple string matching instead.
# ============================================================

NEGATION_PATTERNS = [
    # Direct negation - Vietnamese
    (re.compile(r'(?<![a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ])không\s+(có\s+)?'), "isNegated"),
    (re.compile(r'không\s+gì'), "isNegated"),
    (re.compile(r'(?<![a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ])chưa\s+(có\s+)?'), "isNegated"),
    (re.compile(r'chưa\s+từng'), "isNegated"),
    (re.compile(r'(không|chưa)\s+gặp'), "isNegated"),
    (re.compile(r'(không|chưa)\s+xuất hiện'), "isNegated"),
    (re.compile(r'(không|chưa)\s+bị'), "isNegated"),
    (re.compile(r'(không|chưa)\s+được chẩn đoán'), "isNegated"),
    (re.compile(r'(?<![a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ])thiếu\s+'), "isNegated"),
    (re.compile(r'(?<![a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôồốổỗộơờớởỡợùúũụủưừứửữựỳýỹỷỵ])miễn\s+'), "isNegated"),
    (re.compile(r'phủ\s+định'), "isNegated"),
    # English negation
    (re.compile(r'(?<![a-zA-Z])neg(?![a-zA-Z])'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])negative(?![a-zA-Z])'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])deny(?![a-zA-Z])'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])denies(?![a-zA-Z])'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])no\s+'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])without(?![a-zA-Z])'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])absent(?![a-zA-Z])'), "isNegated"),
    # Medical shorthand
    (re.compile(r'(?<![a-zA-Z])x\s+bệnh'), "isNegated"),
    (re.compile(r'(?<![a-zA-Z])x\s+tiền sử'), "isNegated"),
    (re.compile(r'-\s+bệnh'), "isNegated"),
    (re.compile(r'-\s+tiền sử'), "isNegated"),
]

HISTORICAL_PATTERNS = [
    # Vietnamese
    (re.compile(r'tiền\s+sử\s+'), "isHistorical"),
    (re.compile(r'(có\s+)?tiền\s+sử\s+bệnh\s+'), "isHistorical"),
    (re.compile(r'đã\s+từng\s+'), "isHistorical"),
    (re.compile(r'đã\s+có\s+'), "isHistorical"),
    (re.compile(r'đã\s+bị\s+'), "isHistorical"),
    (re.compile(r'đã\s+phẫu thuật\s+'), "isHistorical"),
    (re.compile(r'đã\s+điều trị\s+'), "isHistorical"),
    (re.compile(r'lịch\s+sử\s+'), "isHistorical"),
    (re.compile(r'cũ\s+'), "isHistorical"),
    # English
    (re.compile(r'(?<![a-zA-Z])previously(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'(?<![a-zA-Z])past\s+history(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'(?<![a-zA-Z])history\s+of(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'(?<![a-zA-Z])h/o(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'(?<![a-zA-Z])s/p(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'(?<![a-zA-Z])status\s+post(?![a-zA-Z])'), "isHistorical"),
    (re.compile(r'years?\s+of\s+'), "isHistorical"),
    (re.compile(r'năm\s+nay'), "isHistorical"),
    (re.compile(r'tháng\s+nay'), "isHistorical"),
]

FAMILY_PATTERNS = [
    # Vietnamese family terms - use lookbehind for space/start to avoid false matches
    (re.compile(r'(?:^|(?<=\s))gia\s+đình\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))người\s+nhà\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))bố\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))cha\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))mẹ\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))mẫu\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))anh\s+trai\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))chị\s+gái\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))em\s+(?:trai|gái)\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))ob\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))bà\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))ông\s+(?:bệnh nhân\s+)?'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))cháu\s+'), "isFamily"),
    (re.compile(r'(?:^|(?<=\s))con\s+'), "isFamily"),
    # English
    (re.compile(r'(?<![a-zA-Z])family\s+of(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])fam\s+hx(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])fhx(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])mother(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])father(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])sibling(?![a-zA-Z])'), "isFamily"),
    (re.compile(r'(?<![a-zA-Z])parents?(?![a-zA-Z])'), "isFamily"),
]


# ============================================================
# CONTEXT WINDOW RULES
# ============================================================

def detect_negation_context(
    text: str,
    entity_start: int,
    entity_end: int,
    window_size: int = 50,
) -> bool:
    """Detect if entity is negated based on surrounding context."""
    # Look at text before entity
    context_start = max(0, entity_start - window_size)
    prefix = text[context_start:entity_start].lower()

    # Check direct negation patterns
    for pattern, label in NEGATION_PATTERNS:
        if pattern.search(prefix):
            return True

    # Check if entity itself starts with negation
    entity_text = text[entity_start:entity_end].lower()
    if re.match(r'^không\s+', entity_text):
        return True
    if re.match(r'^không có\s+', entity_text):
        return True

    return False


def detect_historical_context(
    text: str,
    entity_start: int,
    entity_end: int,
    window_size: int = 60,
) -> bool:
    """Detect if entity is historical."""
    context_start = max(0, entity_start - window_size)
    prefix = text[context_start:entity_start].lower()

    for pattern, label in HISTORICAL_PATTERNS:
        if pattern.search(prefix):
            return True

    # Check if within "tiền sử" context
    entity_text = text[entity_start:entity_end].lower()
    if re.match(r'^tiền sử\s+', entity_text):
        return True

    return False


def detect_family_context(
    text: str,
    entity_start: int,
    entity_end: int,
    window_size: int = 50,
) -> bool:
    """Detect if entity refers to family member."""
    context_start = max(0, entity_start - window_size)
    prefix = text[context_start:entity_start].lower()

    for pattern, label in FAMILY_PATTERNS:
        if pattern.search(prefix):
            return True

    return False


# ============================================================
# ENTITY-LEVEL ASSERTION DETECTION
# ============================================================

def detect_assertions(
    text: str,
    entity: Dict,
    window_size: int = 50,
) -> List[str]:
    """
    Detect all assertions for a given entity.
    Returns list of assertion labels.
    """
    start = entity.get("position", [-1, -1])[0]
    end = entity.get("position", [-1, -1])[1]

    if start < 0 or end <= start or end > len(text):
        return []

    assertions = []

    if detect_negation_context(text, start, end, window_size):
        assertions.append("isNegated")

    if detect_historical_context(text, start, end, window_size + 10):
        assertions.append("isHistorical")

    if detect_family_context(text, start, end, window_size):
        assertions.append("isFamily")

    return assertions


# ============================================================
# SENTENCE-LEVEL ASSERTION CONTEXT
# ============================================================

def split_sentences(text: str) -> List[Tuple[str, int]]:
    """Split text into sentences with start positions."""
    # Split on sentence boundaries
    parts = re.split(r'(?<=[.!?])\s+|(?<=\n)', text)
    sentences = []
    current_pos = 0
    for part in parts:
        idx = text.find(part, current_pos)
        if idx >= 0:
            sentences.append((part, idx))
            current_pos = idx + len(part)
        else:
            sentences.append((part, current_pos))
            current_pos += len(part)
    return sentences


def get_sentence_for_entity(
    text: str,
    entity_start: int,
    entity_end: int,
) -> Tuple[str, int]:
    """Get the sentence containing the entity and its start position."""
    # Find sentence boundaries
    sentence_enders = re.compile(r'[.!?]\s*|\n')
    starts = [0] + [m.end() for m in sentence_enders.finditer(text)]
    ends = [m.start() for m in sentence_enders.finditer(text)] + [len(text)]

    for s_start, s_end in zip(starts, ends):
        if s_start <= entity_start and entity_end <= s_end:
            return text[s_start:s_end], s_start

    return text, 0


# ============================================================
# COMBINED ASSERTION DETECTOR
# ============================================================

class AssertionDetector:
    """Combined rule-based assertion detection."""

    def __init__(self, use_classifier: bool = False, model_path: str = None):
        self.use_classifier = use_classifier
        self.model_path = model_path
        self.classifier = None

        if use_classifier and model_path:
            self._load_classifier(model_path)

    def _load_classifier(self, model_path: str):
        """Load fine-tuned assertion classifier."""
        try:
            from transformers import pipeline
            self.classifier = pipeline(
                "text-classification",
                model=model_path,
                return_all_scores=True,
            )
            print(f"  Assertion classifier loaded: {model_path}")
        except Exception as e:
            print(f"  Failed to load assertion classifier: {e}")
            self.use_classifier = False

    def detect(
        self,
        text: str,
        entity: Dict,
        window_size: int = 50,
    ) -> List[str]:
        """Detect assertions for an entity."""
        assertions = []

        # Rule-based detection
        rule_assertions = detect_assertions(text, entity, window_size)
        assertions.extend(rule_assertions)

        # Optional classifier
        if self.use_classifier and self.classifier:
            sentence, sent_start = get_sentence_for_entity(
                text,
                entity["position"][0],
                entity["position"][1],
            )
            relative_start = entity["position"][0] - sent_start
            relative_end = entity["position"][1] - sent_start

            # Create input for classifier
            entity_text = entity["text"]
            input_text = f"[SEP] {entity_text} [SEP] {sentence}"

            try:
                results = self.classifier(input_text)
                if results:
                    for r in results[0]:
                        label = r["label"]
                        score = r["score"]
                        if score > 0.5 and label not in assertions:
                            assertions.append(label)
            except Exception as e:
                print(f"  Classifier error: {e}")

        return assertions

    def detect_all(
        self,
        text: str,
        entities: List[Dict],
        window_size: int = 50,
    ) -> List[Dict]:
        """Add assertions to all entities."""
        for entity in entities:
            entity["assertions"] = self.detect(text, entity, window_size)
        return entities
