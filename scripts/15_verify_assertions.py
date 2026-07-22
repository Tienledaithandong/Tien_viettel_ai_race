"""Verify assertion detection works correctly with RIGHT positions."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, 'src')
from assertion import AssertionDetector

detector = AssertionDetector(use_classifier=False)

# Test with CORRECT positions
tests = [
    ("Bệnh nhân không ho, không khó thở", {"text": "ho", "position": [17, 19], "type": "TRIỆU_CHỨNG"}, ["isNegated"]),
    ("Tiền sử tăng huyết áp 5 năm", {"text": "tăng huyết áp", "position": [11, 25], "type": "CHẨN_ĐOÁN"}, ["isHistorical"]),
    ("Mẹ bị đái tháo đường type 2", {"text": "đái tháo đường type 2", "position": [7, 28], "type": "CHẨN_ĐOÁN"}, ["isFamily"]),
    ("Bệnh nhân đã từng phẫu thuật 2020", {"text": "phẫu thuật", "position": [22, 33], "type": "CHẨN_ĐOÁN"}, ["isHistorical"]),
    ("Bố bệnh nhân mắc ung thư phổi", {"text": "ung thư phổi", "position": [23, 35], "type": "CHẨN_ĐOÁN"}, ["isFamily"]),
    ("Không có tiền sử bệnh tim", {"text": "bệnh tim", "position": [20, 28], "type": "CHẨN_ĐOÁN"}, ["isNegated", "isHistorical"]),
]

passed = 0
for text, entity, expected in tests:
    result = detector.detect(text, entity)
    match = set(result) == set(expected)
    status = "PASS" if match else "FAIL"
    if match: passed += 1
    actual_text = text[entity["position"][0]:entity["position"][1]]
    print(f"  [{status}] '{actual_text}' -> {result} (expected {expected})")

print(f"\nResult: {passed}/{len(tests)} passed")
