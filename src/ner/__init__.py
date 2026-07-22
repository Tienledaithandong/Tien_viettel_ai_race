"""
Medical NER Module - Ensemble Approach
Supports:
1. LLM-based NER (Qwen, Gemma, InternLM via vLLM/Ollama)
2. Transformer-based NER (PhoBERT, XLM-R, ModernBERT)
3. Span-level voting ensemble
"""
import json
import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# Optional imports
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


VALID_ENTITY_TYPES = [
    "TRIỆU_CHỨNG",
    "THUỐC",
    "CHẨN_ĐOÁN",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
]

ENTITY_PROMPT = """Bạn là chuyên gia Medical NER tiếng Việt. Hãy trích xuất tất cả thực thể y tế từ đoạn văn sau.

Đoạn văn:
\"\"\"
{text}
\"\"\"

YÊU CẦU:
1. Trích xuất MỌI thực thể y tế xuất hiện trong đoạn văn
2. Gán đúng loại cho mỗi thực thể
3. Trả về vị trí chính xác (chỉ số ký tự, tính từ 0)
4. Bao gồm cả tên xét nghiệm và kết quả xét nghiệm riêng biệt

LOẠI THỰC THỂ:
- TRIỆU_CHỨNG: triệu chứng (ho, đau đầu, khó thở, buồn nôn, mệt mỏi, đau ngực...)
- THUỐC: tên thuốc + liều (paracetamol 500mg, amlodipine 10mg)
- CHẨN_ĐOÁN: tên bệnh (tăng huyết áp, đái tháo đường, viêm phổi)
- TÊN_XÉT_NGHIỆM: tên xét nghiệm (WBC, HbA1c, creatinine, CRP)
- KẾT_QUẢ_XÉT_NGHIỆM: giá trị + đơn vị (14.5, 7.2 g/dL, 120 mg/dL)

QUAN TRỌNG:
- Position tính từ 0, end là exclusive (vd: "abc" start=0 end=3)
- Bắt buộc text trong output PHẢI là substring chính xác của input
- Nếu có "WBC: 14,5" thì "WBC" là TÊN_XÉT_NGHIỆM và "14,5" là KẾT_QUẢ_XÉT_NGHIỆM

OUTPUT FORMAT (JSON array):
[
  {"text": "chuỗi chính xác trong input", "type": "LOẠI", "position": [start, end]},
  ...
]

Chỉ trả về JSON array, không giải thích."""


class NERLLMEngine:
    """NER using LLM via Ollama or API."""

    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def predict(self, text: str, temperature: float = 0.0) -> List[Dict]:
        prompt = ENTITY_PROMPT.format(text=text)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 4096},
        }
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                content = resp.json().get("response", "")
                return self._parse_response(content, text)
        except Exception as e:
            print(f"  LLM NER error ({self.model}): {e}")
        return []

    def _parse_response(self, content: str, original_text: str) -> List[Dict]:
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                entities = json.loads(json_match.group())
                validated = []
                for ent in entities:
                    if self._validate_entity(ent, original_text):
                        validated.append(ent)
                return validated
        except json.JSONDecodeError:
            pass
        return []

    def _validate_entity(self, entity: dict, original_text: str) -> bool:
        text = entity.get("text", "")
        etype = entity.get("type", "")
        position = entity.get("position", [-1, -1])

        if not text or etype not in VALID_ENTITY_TYPES:
            return False
        if position[0] < 0 or position[1] <= position[0]:
            return False
        if position[1] > len(original_text):
            return False

        # Verify substring match
        substring = original_text[position[0]:position[1]]
        if substring.lower() != text.lower():
            return False

        return True


class NERTransformerEngine:
    """NER using fine-tuned transformer models."""

    def __init__(self, model_path: str, model_name: str = "vinai/phobert-base"):
        self.model_name = model_name
        self.model_path = model_path
        self.pipe = None

    def load(self):
        if not HAS_TRANSFORMERS:
            print(f"  transformers not available, skipping {self.model_name}")
            return

        try:
            if os.path.exists(self.model_path):
                self.pipe = pipeline(
                    "token-classification",
                    model=self.model_path,
                    aggregation_strategy="simple",
                    device=0 if torch.cuda.is_available() else -1,
                )
                print(f"  Loaded NER model: {self.model_name}")
            else:
                print(f"  Model not found: {self.model_path}")
        except Exception as e:
            print(f"  Failed to load {self.model_name}: {e}")

    def predict(self, text: str) -> List[Dict]:
        if self.pipe is None:
            return []

        try:
            results = self.pipe(text)
            entities = []
            for r in results:
                entity_text = r.get("word", "")
                start = r.get("start", -1)
                end = r.get("end", -1)
                label = r.get("entity_group", "")
                score = r.get("score", 0.0)

                if score < 0.3:
                    continue

                # Map label to standard type
                mapped_type = self._map_label(label)
                if mapped_type and start >= 0 and end <= len(text):
                    entities.append({
                        "text": text[start:end],
                        "type": mapped_type,
                        "position": [start, end],
                        "score": score,
                    })
            return entities
        except Exception as e:
            print(f"  NER prediction error: {e}")
            return []

    def _map_label(self, label: str) -> Optional[str]:
        label_map = {
            "SYMPTOM": "TRIỆU_CHỨNG",
            "DISEASE": "CHẨN_ĐOÁN",
            "DRUG": "THUỐC",
            "MEDICATION": "THUỐC",
            "TEST_NAME": "TÊN_XÉT_NGHIỆM",
            "TEST_RESULT": "KẾT_QUẢ_XÉT_NGHIỆM",
            "LAB_TEST": "TÊN_XÉT_NGHIỆM",
            "LAB_RESULT": "KẾT_QUẢ_XÉT_NGHIỆM",
        }
        return label_map.get(label.upper().replace("B-", "").replace("I-", ""))


class NEREnsemble:
    """Ensemble of multiple NER engines with voting."""

    def __init__(self, engines: List = None):
        self.engines = engines or []

    def add_engine(self, engine):
        self.engines.append(engine)

    def predict(self, text: str, n_runs: int = 3) -> List[Dict]:
        """Run all engines and merge results with voting."""
        all_predictions = []

        for engine in self.engines:
            if isinstance(engine, NERLLMEngine):
                # Run multiple times for self-consistency
                for temp in [0.0, 0.2, 0.5][:n_runs]:
                    preds = engine.predict(text, temperature=temp)
                    all_predictions.append(preds)
            elif isinstance(engine, NERTransformerEngine):
                preds = engine.predict(text)
                all_predictions.append(preds)
                all_predictions.append(preds)  # count twice as stable
            else:
                preds = engine.predict(text)
                all_predictions.append(preds)

        # Merge and vote
        return self._merge_predictions(all_predictions, text)

    def _merge_predictions(self, all_predictions: list, original_text: str) -> List[Dict]:
        """Merge predictions from multiple runs using voting."""
        if not all_predictions:
            return []

        # Collect all entities with their spans
        span_votes = {}  # (start, end) -> {type: count}

        for preds in all_predictions:
            for ent in preds:
                key = (ent["position"][0], ent["position"][1])
                if key not in span_votes:
                    span_votes[key] = {"counts": {}, "texts": [], "scores": []}
                etype = ent["type"]
                span_votes[key]["counts"][etype] = span_votes[key]["counts"].get(etype, 0) + 1
                span_votes[key]["texts"].append(ent["text"])
                if "score" in ent:
                    span_votes[key]["scores"].append(ent["score"])

        # Select best type for each span based on votes
        results = []
        for (start, end), data in span_votes.items():
            if start < 0 or end > len(original_text) or start >= end:
                continue

            # Pick type with most votes
            best_type = max(data["counts"], key=data["counts"].get)
            vote_count = data["counts"][best_type]
            total_votes = sum(data["counts"].values())

            # Require at least 40% agreement
            if vote_count / max(total_votes, 1) < 0.4:
                continue

            # Pick the most common text variant
            text_counter = {}
            for t in data["texts"]:
                t_lower = t.lower().strip()
                text_counter[t_lower] = text_counter.get(t_lower, 0) + 1
            best_text = max(text_counter, key=text_counter.get)

            # Use the actual substring from original
            actual_text = original_text[start:end]

            avg_score = sum(data["scores"]) / max(len(data["scores"]), 1)

            results.append({
                "text": actual_text,
                "type": best_type,
                "position": [start, end],
                "confidence": vote_count / max(total_votes, 1),
                "avg_score": avg_score,
                "n_votes": vote_count,
            })

        # Sort by position
        results.sort(key=lambda x: x["position"][0])
        return results
