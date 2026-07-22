"""Find exact positions and verify assertions."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, 'src')
from assertion import AssertionDetector

detector = AssertionDetector(use_classifier=False)

tests = [
    ("Bệnh nhân không ho, không khó thở", "ho"),
    ("Tiền sử tăng huyết áp 5 năm", "tăng huyết áp"),
    ("Mẹ bị đái tháo đường type 2", "đái tháo đường type 2"),
    ("Bệnh nhân đã từng phẫu thuật 2020", "phẫu thuật"),
    ("Bố bệnh nhân mắc ung thư phổi", "ung thư phổi"),
    ("Không có tiền sử bệnh tim", "bệnh tim"),
]

for text, entity_text in tests:
    idx = text.find(entity_text)
    if idx < 0:
        idx = text.lower().find(entity_text.lower())
    if idx >= 0:
        entity = {"text": entity_text, "position": [idx, idx + len(entity_text)], "type": "CHẨN_ĐOÁN"}
        result = detector.detect(text, entity)
        actual = text[idx:idx+len(entity_text)]
        print(f"  '{actual}' at [{idx},{idx+len(entity_text)}] -> {result}")
    else:
        print(f"  '{entity_text}' NOT FOUND in text")
