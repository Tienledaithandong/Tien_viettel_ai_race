"""
Script 05: Generate Synthetic Medical Data using GPT-4o / LLM API
Output: datasets/synthetic/*.json
"""
import json
import os
import time
import random
import requests
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets", "synthetic")
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")

# Load ICD-10 and RxNorm databases for reference
def load_databases():
    icd10_path = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd10_database.json")
    rxnorm_path = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rxnorm_database.json")

    icd10_data = {}
    rxnorm_data = {}

    if os.path.exists(icd10_path):
        with open(icd10_path, "r", encoding="utf-8") as f:
            icd10_data = json.load(f)

    if os.path.exists(rxnorm_path):
        with open(rxnorm_path, "r", encoding="utf-8") as f:
            rxnorm_data = json.load(f)

    return icd10_data, rxnorm_data


# ============================================================
# System Prompt
# ============================================================
SYSTEM_PROMPT = """Bạn là một chuyên gia y tế và NLP. Nhiệm vụ của bạn là tạo dữ liệu huấn luyện cho hệ thống Medical NER tiếng Việt.

Bạn cần đóng vai một bác sĩ Việt Nam viết các đoạn ghi chú lâm sàng thực tế và gán nhãn cho các thực thể y tế.

QUAN TRỌNG: Mọi thông tin bệnh nhân là dữ liệu tổng hợp (synthetic), không phải người thật.

## CÁC LOẠI KHÁI NIỆM:
- TRIỆU_CHỨNG: triệu chứng (ho, đau đầu, khó thở, buồn nôn, mệt mỏi)
- THUỐC: tên thuốc (amlodipine 10mg, omeprazole 20mg)
- CHẨN_ĐOÁN: tên bệnh (tăng huyết áp, đái tháo đường typ 2)
- TÊN_XÉT_NGHIỆM: tên xét nghiệm (WBC, HbA1c, creatinine)
- KẾT_QUẢ_XÉT_NGHIỆM: kết quả xét nghiệm (14.5, 7.2 g/dL)

## ASSERTIONS:
- "isNegated": phủ định ("không ho", "không có tiền sử")
- "isFamily": người nhà ("bố bị ung thư", "mẹ mắc tiểu đường")
- "isHistorical": tiền sử ("tiền sử tăng huyết áp", "đã từng phẫu thuật")

## OUTPUT FORMAT:
Mỗi mẫu phải có "text" và "concepts" list.
Mỗi concept có: text, type, assertions, position [start, end], candidates.

Ví dụ:
{
  "text": "Bệnh nhân nam 55 tuổi, đau ngực trái. ECG: ST chênh xuống.",
  "concepts": [
    {"text": "đau ngực trái", "type": "TRIỆU_CHỨNG", "assertions": [], "position": [30, 43], "candidates": ["R07.9"]}
  ]
}"""


def generate_batch_openai(
    prompt: str,
    api_key: str,
    model: str = "gpt-4o",
    n_samples: int = 10,
    temperature: float = 0.9,
    max_tokens: int = 8000,
) -> Optional[list]:
    """Generate data using OpenAI API."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    full_prompt = f"{prompt}\n\nHãy tạo {n_samples} mẫu dữ liệu. Trả về JSON array, mỗi phần tử là 1 mẫu."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "samples" in data:
                return data["samples"]
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return [data]
        else:
            print(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"OpenAI API exception: {e}")
        return None


def generate_batch_anthropic(
    prompt: str,
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    n_samples: int = 10,
    temperature: float = 0.9,
    max_tokens: int = 8000,
) -> Optional[list]:
    """Generate data using Anthropic API."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    full_prompt = f"{prompt}\n\nHãy tạo {n_samples} mẫu dữ liệu. Trả về JSON array."

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            content = result["content"][0]["text"]
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["samples", "data", "examples", "records"]:
                    if key in data:
                        return data[key]
                return [data]
        else:
            print(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"Anthropic API exception: {e}")
        return None


def generate_batch_ollama(
    prompt: str,
    model: str = "llama3.1:8b",
    n_samples: int = 10,
    temperature: float = 0.9,
) -> Optional[list]:
    """Generate data using local Ollama."""
    url = "http://localhost:11434/api/generate"

    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}\n\nTạo {n_samples} mẫu. Trả về JSON array."

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 8000},
    }

    try:
        resp = requests.post(url, json=payload, timeout=300)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("response", "")
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["samples", "data", "examples"]:
                    if key in data:
                        return data[key]
        else:
            print(f"Ollama error {resp.status_code}")
            return None
    except Exception as e:
        print(f"Ollama exception: {e}")
        return None


# ============================================================
# PROMPT TEMPLATES
# ============================================================

GENERAL_PROMPT = """Tạo {n} mẫu dữ liệu Medical NER tiếng Việt.
Mỗi mẫu là 1 đoạn ghi chú bác sĩ (50-300 ký tự) với các khái niệm y tế được gán nhãn.
Đa dạng chuyên khoa: Tim mạch, Nội tiết, Hô hấp, Tiêu hóa, Thần kinh, Cơ xương khớp.
Mỗi đoạn có 2-6 khái niệm."""

SPECIALTY_PROMPTS = {
    "tim_mach": """Tạo {n} mẫu ghi chú TIM MẠCH tiếng Việt.
Bệnh: tăng huyết áp, ĐMTN, suy tim, rung nhĩ, hẹp mạch vành, nhồi máu cơ tim.
Thuốc: amlodipine, metoprolol, aspirin, clopidogrel, atorvastatin, warfarin, apixaban, losartan.
Xét nghiệm: ECG, Troponin, BNP, Echo, lipid profile, D-dimer.
Triệu chứng: đau ngực, khó thở, phù, đánh trống ngực.
Phong cách: giấy xuất viện, tờ khám bệnh, ghi chú nhanh.""",

    "noi_tiet": """Tạo {n} mẫu ghi chú NỘI TIẾT tiếng Việt.
Bệnh: đái tháo đường typ 1/2, cường giáp, suy giáp, Basedow, loãng xương.
Thuốc: metformin, glipizide, gliclazide, insulin, levothyroxine, methimazole.
Xét nghiệm: HbA1c, fasting glucose, TSH, FT4, anti-TPO, calcium, vitamin D.
Triệu chứng: khát nước, tiểu nhiều, gầy sút, run tay.
Đa dạng phong cách viết.""",

    "ho_hap": """Tạo {n} mẫu ghi chú HÔ HẤP tiếng Việt.
Bệnh: COPD, hen phế quản, viêm phổi, lao phổi, viêm phế quản cấp.
Thuốc: salbutamol, budesonide, montelukast, amoxicillin, azithromycin, augmentin.
Xét nghiệm: CXR, CT scan phổi, Spirometry, PCR lao, cấy đờm.
Triệu chứng: ho, khó thở, khạc đờm, đau ngực, sốt.
Ghi chú bệnh viện, giấy xuất viện.""",

    "tieu_hoa": """Tạo {n} mẫu ghi chú TIÊU HÓA tiếng Việt.
Bệnh: trào ngược GERD, viêm dạ dày, loét dạ dày, viêm tụy, sỏi mật, viêm ruột thừa.
Thuốc: omeprazole, pantoprazole, domperidone, ranitidine, metoclopramide.
Xét nghiệm: nội soi, CT scan bụng, siêu âm bụng, AST, ALT, lipase.
Triệu chứng: đau bụng, buồn nôn, nôn, ợ hơi, tiêu chảy, táo bón.""",

    "than_kinh": """Tạo {n} mẫu ghi chú THẦN KINH tiếng Việt.
Bệnh: đau đầu migraine, đột quỵ, động kinh, Parkinson, Alzheimer.
Thuốc: gabapentin, pregabalin, levetiracetam, donepezil, sumatriptan.
Xét nghiệm: CT/MRI não, EEG, điện cơ.
Triệu chứng: đau đầu, chóng mặt, tê bì, yếu liệt, co giật.""",

    "co_xuong_khop": """Tạo {n} mẫu ghi chú CƠ XƯƠNG KHỚP tiếng Việt.
Bệnh: thoái hóa khớp gối, thoái hóa cột sống, viêm đa khớp dạng thấp, gout.
Thuốc: diclofenac, celecoxib, glucosamine, methotrexate, allopurinol.
Xét nghiệm: X-quang khớp, CRP, ESR, RF, anti-CCP.
Triệu chứng: đau khớp, cứng khớp, sưng khớp, hạn chế vận động.""",
}

NEGATION_PROMPT = """Tạo {n} mẫu dữ liệu tập trung vào PHỦ ĐỊNH (isNegated).
Mỗi mẫu phải có ít nhất 1 khái niệm bị phủ định.
Ví dụ: "không ho", "không khó thở", "không sốt", "không đau bụng"
Cũng có thể phủ định gián tiếp: "Bệnh nhân denies chest pain"
Phân bổ: 60% phủ định rõ ràng, 40% phủ định gián tiếp."""

HISTORICAL_PROMPT = """Tạo {n} mẫu dữ liệu tập trung vào TIỀN SỬ (isHistorical).
Mỗi mẫu phải có ít nhất 1 khái niệm tiền sử.
Ví dụ: "tiền sử tăng huyết áp 5 năm", "đã phẫu thuật appendix 2020"
"Có tiền sử đái tháo đường typ 2"
Phân bổ: 50% dùng từ 'tiền sử', 30% dùng 'đã từng', 20% diễn đạt khác."""

FAMILY_PROMPT = """Tạo {n} mẫu dữ liệu tập trung vào GIA ĐÌNH (isFamily).
Mỗi mẫu phải có ít nhất 1 khái niệm liên quan người nhà.
Ví dụ: "bố bị ung thư phổi", "mẹ mắc đái tháo đường"
"Anh trai tử vong vì nhồi máu cơ tim 45 tuổi"
"Bà nội mất vì đột quỵ"
Phân bổ: 40% bố/mẹ, 30% anh chị em, 30% ông bà/người thân khác."""


def generate_all_synthetic_data(
    api_provider: str = "openai",
    api_key: str = "",
    model: str = "",
    total_samples: int = 5000,
    batch_size: int = 50,
):
    """Generate synthetic data using the specified API."""
    os.makedirs(DATASETS_DIR, exist_ok=True)

    if api_provider == "openai":
        generate_fn = lambda p, n: generate_batch_openai(p, api_key, model or "gpt-4o", n)
    elif api_provider == "anthropic":
        generate_fn = lambda p, n: generate_batch_anthropic(p, api_key, model or "claude-3-5-sonnet-20241022", n)
    elif api_provider == "ollama":
        generate_fn = lambda p, n: generate_batch_ollama(p, model or "llama3.1:8b", n)
    else:
        print(f"Unknown provider: {api_provider}")
        return

    all_data = []
    sample_id = 0

    # Phase 1: General mixed data
    print("\n=== Phase 1: General Mixed Data ===")
    n_general = int(total_samples * 0.5)
    for batch_start in range(0, n_general, batch_size):
        batch_n = min(batch_size, n_general - batch_start)
        prompt = GENERAL_PROMPT.format(n=batch_n)
        data = generate_fn(prompt, batch_n)
        if data:
            for item in data:
                item["id"] = f"syn_{sample_id:05d}"
                item["phase"] = "general"
                all_data.append(item)
                sample_id += 1
            print(f"  Generated {len(data)} samples (total: {sample_id})")
        time.sleep(1)

    # Phase 2: Specialty data
    print("\n=== Phase 2: Specialty Data ===")
    n_specialty = int(total_samples * 0.3)
    per_specialty = n_specialty // len(SPECIALTY_PROMPTS)
    for specialty, prompt_template in SPECIALTY_PROMPTS.items():
        print(f"\n--- {specialty} ---")
        for batch_start in range(0, per_specialty, batch_size):
            batch_n = min(batch_size, per_specialty - batch_start)
            prompt = prompt_template.format(n=batch_n)
            data = generate_fn(prompt, batch_n)
            if data:
                for item in data:
                    item["id"] = f"syn_{sample_id:05d}"
                    item["phase"] = f"specialty_{specialty}"
                    all_data.append(item)
                    sample_id += 1
                print(f"  Generated {len(data)} samples (total: {sample_id})")
            time.sleep(1)

    # Phase 3: Assertion-focused data
    print("\n=== Phase 3: Assertion-Focused Data ===")
    assertion_prompts = {
        "negation": NEGATION_PROMPT,
        "historical": HISTORICAL_PROMPT,
        "family": FAMILY_PROMPT,
    }
    n_assertion = int(total_samples * 0.2)
    per_assertion = n_assertion // len(assertion_prompts)
    for assertion_type, prompt_template in assertion_prompts.items():
        print(f"\n--- {assertion_type} ---")
        for batch_start in range(0, per_assertion, batch_size):
            batch_n = min(batch_size, per_assertion - batch_start)
            prompt = prompt_template.format(n=batch_n)
            data = generate_fn(prompt, batch_n)
            if data:
                for item in data:
                    item["id"] = f"syn_{sample_id:05d}"
                    item["phase"] = f"assertion_{assertion_type}"
                    all_data.append(item)
                    sample_id += 1
                print(f"  Generated {len(data)} samples (total: {sample_id})")
            time.sleep(1)

    # Save
    output_file = os.path.join(DATASETS_DIR, "synthetic_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n=== Total: {len(all_data)} synthetic samples saved to {output_file} ===")
    return all_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic medical data")
    parser.add_argument("--provider", choices=["openai", "anthropic", "ollama"], default="openai")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--model", default="")
    parser.add_argument("--total-samples", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=50)

    args = parser.parse_args()

    generate_all_synthetic_data(
        api_provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        total_samples=args.total_samples,
        batch_size=args.batch_size,
    )
