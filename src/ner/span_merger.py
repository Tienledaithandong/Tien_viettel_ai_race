"""
Module 3: Span Merger
Merges mentions from multiple sources (rule, NER, LLM), resolves overlaps.
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class MergedMention:
    text: str
    start: int
    end: int
    type: str
    confidence: float
    sources: list = field(default_factory=list)
    assertions: list = field(default_factory=list)
    candidates: list = field(default_factory=list)


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Check if two spans overlap."""
    return a_start < b_end and b_start < a_end


def iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    """Calculate Intersection over Union."""
    inter_start = max(a_start, b_start)
    inter_end = min(a_end, b_end)
    if inter_start >= inter_end:
        return 0.0
    intersection = inter_end - inter_start
    union = (a_end - a_start) + (b_end - b_start) - intersection
    return intersection / max(union, 1)


def merge_mentions(
    all_mentions: List,
    raw_text: str,
    type_priorities: Dict[str, float] = None,
) -> List[MergedMention]:
    """
    Merge mentions from multiple sources.
    Priority: rule_drug > ner > llm > rule_symptom
    """
    if type_priorities is None:
        type_priorities = {
            "rule_drug": 1.0,
            "rule_drug_simple": 0.9,
            "rule_lab": 0.95,
            "rule_lab_result": 0.95,
            "rule_symptom": 0.8,
            "ner": 0.85,
            "llm": 0.7,
        }

    # Convert to MergedMention
    merged = []
    for m in all_mentions:
        merged.append(MergedMention(
            text=m.text if hasattr(m, 'text') else m.get('text', ''),
            start=m.start if hasattr(m, 'start') else m.get('position', [0, 0])[0],
            end=m.end if hasattr(m, 'end') else m.get('position', [0, 0])[1],
            type=m.type if hasattr(m, 'type') else m.get('type', ''),
            confidence=m.confidence if hasattr(m, 'confidence') else m.get('confidence', 0.5),
            sources=[m.source if hasattr(m, 'source') else m.get('source', 'unknown')],
            assertions=m.assertions if hasattr(m, 'assertions') else m.get('assertions', []),
            candidates=m.candidates if hasattr(m, 'candidates') else m.get('candidates', []),
        ))

    # Sort by start position, then by confidence (descending)
    merged.sort(key=lambda x: (x.start, -x.confidence))

    # Resolve overlaps
    resolved = []
    for mention in merged:
        if not resolved:
            resolved.append(mention)
            continue

        # Check overlap with ALL resolved mentions
        merged_with_existing = False
        for i, existing in enumerate(resolved):
            if overlaps(existing.start, existing.end, mention.start, mention.end):
                # Same type -> check containment
                if existing.type == mention.type:
                    # One is contained in the other -> keep longer
                    if (mention.start >= existing.start and mention.end <= existing.end):
                        # mention is shorter, skip it
                        merged_with_existing = True
                        break
                    elif (existing.start >= mention.start and existing.end <= mention.end):
                        # existing is shorter, replace it
                        resolved[i] = mention
                        merged_with_existing = True
                        break
                    # Same text, different case -> merge sources
                    elif existing.text.lower() == mention.text.lower():
                        existing.sources.extend(mention.sources)
                        existing.confidence = max(existing.confidence, mention.confidence)
                        merged_with_existing = True
                        break
                else:
                    # Different type, significant overlap -> keep longer/higher confidence
                    overlap_ratio = iou(existing.start, existing.end, mention.start, mention.end)
                    if overlap_ratio > 0.3:
                        if len(mention.text) > len(existing.text):
                            resolved[i] = mention
                        merged_with_existing = True
                        break

        if not merged_with_existing:
            resolved.append(mention)

    return resolved


def split_drug_and_symptom(
    text: str,
    mention: MergedMention,
) -> List[MergedMention]:
    """
    Split 'drug + điều trị symptom' into separate mentions.
    Example: 'guaifenesin ml po q6h:prn điều trị ho'
    -> THUỐC: 'guaifenesin ml po q6h:prn'
    -> TRIỆU_CHỨNG: 'ho'
    """
    import re

    treat_match = re.search(r'\s+điều\s+trị\s+', mention.text, re.I)
    if not treat_match or mention.type != "THUỐC":
        return [mention]

    drug_text = mention.text[:treat_match.start()].strip()
    symptom_text = mention.text[treat_match.end():].strip()

    results = []

    if drug_text:
        results.append(MergedMention(
            text=drug_text,
            start=mention.start,
            end=mention.start + len(drug_text),
            type="THUỐC",
            confidence=mention.confidence,
            sources=mention.sources.copy(),
            assertions=mention.assertions.copy(),
            candidates=mention.candidates.copy(),
        ))

    if symptom_text:
        results.append(MergedMention(
            text=symptom_text,
            start=mention.start + treat_match.end(),
            end=mention.start + treat_match.end() + len(symptom_text),
            type="TRIỆU_CHỨNG",
            confidence=0.85,
            sources=["drug_split"],
        ))

    return results if results else [mention]


def postprocess_mentions(
    mentions: List[MergedMention],
    raw_text: str,
) -> List[MergedMention]:
    """Post-process merged mentions."""
    results = []
    for mention in mentions:
        # Split drug+symptom
        splits = split_drug_and_symptom(raw_text, mention)
        results.extend(splits)

    # Verify all spans are substrings of raw_text
    valid = []
    for m in results:
        actual = raw_text[m.start:m.end]
        if actual and actual.lower() == m.text.lower():
            m.text = actual  # Use exact substring
            valid.append(m)
        elif m.start >= 0 and m.end <= len(raw_text):
            # Try to find correct position
            idx = raw_text.lower().find(m.text.lower())
            if idx >= 0:
                m.start = idx
                m.end = idx + len(m.text)
                m.text = raw_text[idx:idx + len(m.text)]
                valid.append(m)
            else:
                # Skip if can't align
                pass

    return valid
