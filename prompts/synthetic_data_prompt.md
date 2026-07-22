# Prompt sinh dữ liệu Synthetic cho Medical NER

## System Prompt

```
Bạn là một chuyên gia y tế và NLP. Nhiệm vụ của bạn là tạo dữ liệu huấn luyện cho hệ thống Medical NER (Named Entity Recognition) tiếng Việt.

Bạn cần đóng vai một bác sĩ Việt Nam viết các đoạn ghi chú lâm sàng thực tế và gán nhãn cho các thực thể y tế trong đoạn văn.

QUAN TRỌNG: Mọi thông tin bệnh nhân là dữ liệu tổng hợp (synthetic), không phải người thật.
```

## Main Prompt Template

```
Hãy tạo {n_samples} mẫu dữ liệu huấn luyện cho bài toán Medical NER tiếng Việt.

## YÊU CẦU:
1. Mỗi mẫu gồm 1 đoạn văn bản y khoa tự do (tiếng Việt) và JSON output tương ứng
2. Văn bản phải thực tế, giống ghi chú bác sĩ thật (có thể viết tắt, thiếu dấu câu)
3. Mỗi văn bản PHẢI chứa từ 2-8 khái niệm y tế
4. Đảm bảo diversity: đa dạng chuyên khoa, độ dài, phong cách viết

## CÁC LOẠI KHÁI NIỆM:
- TRIỆU_CHỨNG: triệu chứng mà bệnh nhân mắc (VD: ho, đau đầu, khó thở, buồn nôn)
- THUỐC: tên thuốc điều trị (VD: amlodipine 10mg, omeprazole 20mg)
- CHẨN_ĐOÁN: tên bệnh chẩn đoán (VD: tăng huyết áp, đái tháo đường typ 2)
- TÊN_XÉT_NGHIỆM: tên xét nghiệm (VD: WBC, HbA1c, creatinine)
- KẾT_QUẢ_XÉT_NGHIỆM: kết quả xét nghiệm (VD: 14.5, 7.2 g/dL)

## ASSERTIONS (quan hệ ngữ cảnh):
- "isNegated": phủ định (VD: "không ho", "không có tiền sử")
- "isFamily": liên quan người nhà (VD: "bố bị ung thư", "mẹ mắc tiểu đường")
- "isHistorical": tiền sử (VD: "tiền sử tăng huyết áp", "đã từng phẫu thuật")

## OUTPUT FORMAT (cho mỗi mẫu):
```json
{
  "text": "đoạn văn bản y khoa",
  "concepts": [
    {
      "text": "cụm từ trong văn bản",
      "type": "TRIỆU_CHỨNG|THUỐC|CHẨN_ĐOÁN|TÊN_XÉT_NGHIỆM|KẾT_QUẢ_XÉT_NGHIỆM",
      "assertions": ["isNegated", "isFamily", "isHistorical"],
      "position": [start_char, end_char],
      "candidates": ["ICD10_code hoặc RxNorm_CUI"]
    }
  ]
}
```

## VÍ DẪM:
Input: "Bệnh nhân nam 55 tuổi, tiền sử tăng huyết áp 5 năm nay, đang dùng amlodipine 10mg每天. Hôm nay đến khám vì đau ngực trái, khó thở khi gắng sức. ECG: ST chênh xuống D2, D3, aVF. Cấy máu: WBC 12.5, CRP 45. Chẩn đoán: Đau thồi ngực không ổn định."

Output:
```json
{
  "text": "Bệnh nhân nam 55 tuổi, tiền sử tăng huyết áp 5 năm nay, đang dùng amlodipine 10mg每天. Hôm nay đến khám vì đau ngực trái, khó thở khi gắng sức. ECG: ST chênh xuống D2, D3, aVF. Cấy máu: WBC 12.5, CRP 45. Chẩn đoán: Đau thồi ngực không ổn định.",
  "concepts": [
    {
      "text": "tăng huyết áp",
      "type": "CHẨN_ĐOÁN",
      "assertions": ["isHistorical"],
      "position": [35, 49],
      "candidates": ["I10"]
    },
    {
      "text": "amlodipine 10mg",
      "type": "THUỐC",
      "assertions": ["isHistorical"],
      "position": [64, 80],
      "candidates": ["308135"]
    },
    {
      "text": "đau ngực trái",
      "type": "TRIỆU_CHỨNG",
      "assertions": [],
      "position": [108, 121],
      "candidates": ["R07.9"]
    },
    {
      "text": "khó thở khi gắng sức",
      "type": "TRIỆU_CHỨNG",
      "assertions": [],
      "position": [123, 143],
      "candidates": ["R06.02"]
    },
    {
      "text": "WBC",
      "type": "TÊN_XÉT_NGHIỆM",
      "assertions": [],
      "position": [168, 171],
      "candidates": []
    },
    {
      "text": "12.5",
      "type": "KẾT_QUẢ_XÉT_NGHIỆM",
      "assertions": [],
      "position": [172, 176],
      "candidates": []
    },
    {
      "text": "CRP",
      "type": "TÊN_XÉT_NGHIỆM",
      "assertions": [],
      "position": [178, 181],
      "candidates": []
    },
    {
      "text": "45",
      "type": "KẾT_QUẢ_XÉT_NGHIỆM",
      "assertions": [],
      "position": [182, 184],
      "candidates": []
    },
    {
      "text": "Đau thồi ngực không ổn định",
      "type": "CHẨN_ĐOÁN",
      "assertions": [],
      "position": [196, 224],
      "candidates": ["I20.0"]
    }
  ]
}
```

## CHUYÊN KHOA CẦN BAO PHỦ (mỗi chuyên khoa ít nhất 10% mẫu):
1. Tim mạch: tăng huyết áp, ĐMTN, suy tim, rung nhĩ
2. Nội tiết: đái tháo đường, cường giáp, suy giáp
3. Hô hấp: COPD, hen phế quản, viêm phổi
4. Tiêu hóa: trào ngược, viêm dạ dày, viêm tụy
5. Thần kinh: đau đầu, đột quỵ, động kinh
6. Cơ xương khớp: thoái hóa khớp, đau lưng
7. Nhiễm trùng: nhiễm trùng tiểu, viêm phổi
8. Ngoại khoa: viêm ruột thừa, thoát vị

## PHONG CÁCH VIẾT (đa dạng):
- Ghi chú nhanh bác sĩ (ngắn, viết tắt)
- Giấy xuất viện (formal hơn)
- Tờ khám bệnh
- Kết quả xét nghiệm

Hãy tạo dữ liệu ngay và trả về danh sách JSON.
```

## Batch Prompt (sinh nhiều lần)

```
Bạn đã tạo dữ liệu ở batch trước. Bây giờ hãy tạo thêm {n_samples} mẫu MỚI, khác hoàn toàn với các mẫu đã tạo.
Tập trung vào chuyên khoa: {focus_specialty}

Vẫn tuân thủ format output như trên.

LƯU Ý QUAN TRỌNG:
- KHÔNG được trùng lặp nội dung với batch trước
- Mỗi batch nên tập trung vào chuyên khoa khác nhau
- Đảm bảo đa dạng cả về độ dài văn bản (50-500 ký tự)
```

## Assertion-Specific Prompt

```
Hãy tạo 100 mẫu dữ liệu tập trung vào detection ASSERTIONS (quan hệ ngữ cảnh).

Mỗi mẫu phải có ít nhất 1 assertion. Phân bổ:
- 35% mẫu có isNegated
- 25% mẫu có isFamily
- 35% mẫu có isHistorical
- 5% mẫu có nhiều hơn 1 assertion

VÍ DỤ isNegated:
"Khám: Bệnh nhân không ho, không khó thở, không sốt"

VÍ DỤ isFamily:
"Bố bệnh nhân có tiền sử đái tháo đường typ 2, mẹ bị tăng huyết áp"

VÍ DỤ isHistorical:
"Bệnh nhân có tiền sử phẫu thuật appendix năm 2020"
```

## Specialty-Specific Prompts

### Tim Mạch
```
Tạo 100 mẫu ghi chú y khoa CHUYÊN KHOA TIM M mạch.
Bao gồm: tăng huyết áp, ĐMTN, suy tim, rung nhĩ, nhồi máu cơ tim, hẹp mạch vành
Thuốc thường dùng: amlodipine, metoprolol, aspirin, clopidogrel, atorvastatin, warfarin, apixaban
Xét nghiệm: ECG, Troponin, BNP, Echo, lipid profile
```

### Nội Tiết
```
Tạo 100 mẫu ghi chú y khoa CHUYÊN KHOA NỘI TIẾT.
Bao gồm: đái tháo đường typ 1/2, cường giáp, suy giáp, bệnh Basedow
Thuốc: metformin, glipizide, insulin, levothyroxine, methimazole
Xét nghiệm: HbA1c, fasting glucose, TSH, FT4, anti-TPO
```

### Hô Hấp
```
Tạo 100 mẫu ghi chú y khoa CHUYÊN KHOA HÔ HẤP.
Bao gồm: COPD, hen phế quản, viêm phổi, lao phổi
Thuốc: salbutamol, budesonide, montelukast, amoxicillin, azithromycin
Xét nghiệm: CXR, CT scan, Spirometry, PCR lao
```
