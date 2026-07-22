"""
Optimized Inference Pipeline for Competition
Specifically tuned to maximize:
1. Text Score (WER) - Exact span matching
2. Assertion Score (Jaccard) - Better context detection  
3. Candidate Score (Jaccard) - Hybrid mapping strategy
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from src.normalization import normalize_clinical_text
from src.preprocessing.section_detector import detect_sections
from src.preprocessing.rule_extractor import extract_all_rules
from src.ner import NEREnsemble, NERLLMEngine
from src.ner.span_merger import merge_mentions, postprocess_mentions, MergedMention
from src.ner.position_align import align_all_positions
from src.entity_linking import EntityLinker
from src.assertion.section_aware import detect_all_assertions
from src.postprocessing import fix_entity_type
from src.postprocessing.validator import validate_output, save_output


class OptimizedCompetitionPipeline:
    """
    Optimized pipeline with focus on competition metrics.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.entity_linker: Optional[EntityLinker] = None
        self._loaded = False
        
        # Load local databases for hybrid mapping
        self.icd_db = self._load_local_db("data/icd10_cleaned.json")
        self.rxnorm_db = self._load_local_db("data/rxnorm_cleaned.json")

    def _load_local_db(self, path: str) -> Dict[str, str]:
        """Load local knowledge base for fast exact matching."""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        print(f"  Warning: Local DB not found at {path}")
        return {}

    def load(self) -> None:
        """Load all components."""
        print("=" * 60)
        print("LOADING OPTIMIZED COMPETITION PIPELINE")
        print("=" * 60)

        # Load Entity Linking
        print("\n--- Loading Entity Linking ---")
        self.entity_linker = EntityLinker(
            embedding_model=self.config.get("embedding_model", "BAAI/bge-m3"),
            cross_encoder_model=self.config.get("cross_encoder_model", "BAAI/bge-reranker-v2-m3"),
        )
        self.entity_linker.load()

        self._loaded = True
        print("\n=== Pipeline Loaded ===")

    def _find_exact_span(self, text: str, entity_text: str) -> Optional[Tuple[int, int]]:
        """
        CRITICAL FOR WER SCORE: Find exact character span in original text.
        Handles whitespace normalization and case variations.
        """
        # Strategy 1: Exact match
        start = text.find(entity_text)
        if start != -1:
            return start, start + len(entity_text)
        
        # Strategy 2: Normalized match (handle extra spaces)
        normalized_entity = " ".join(entity_text.split())
        start = text.find(normalized_entity)
        if start != -1:
            return start, start + len(normalized_entity)
        
        # Strategy 3: Case-insensitive match
        lower_text = text.lower()
        lower_entity = normalized_entity.lower()
        start = lower_text.find(lower_entity)
        if start != -1:
            return start, start + len(normalized_entity)
        
        # Strategy 4: Fuzzy match for slight variations
        best_ratio = 0.90
        best_pos = None
        
        entity_words = normalized_entity.split()
        if not entity_words:
            return None
            
        text_words = text.split()
        window_size = len(entity_words)
        
        for i in range(len(text_words) - window_size + 1):
            window = " ".join(text_words[i:i+window_size])
            ratio = SequenceMatcher(None, window.lower(), lower_entity).ratio()
            
            if ratio > best_ratio:
                # Find char position of this word sequence
                start_char = text.find(text_words[i])
                if start_char != -1:
                    end_char = start_char + len(window)
                    best_pos = (start_char, end_char)
                    best_ratio = ratio
        
        return best_pos

    def _enhance_candidates(self, entity_text: str, entity_type: str, 
                           llm_candidates: List[str]) -> List[str]:
        """
        CRITICAL FOR CANDIDATE SCORE: Hybrid mapping strategy.
        Combines LLM predictions with local DB exact matching.
        """
        if entity_type not in ["CHẨN_ĐOÁN", "THUỐC"]:
            return []
        
        candidates = list(llm_candidates)  # Start with LLM predictions
        search_text = " ".join(entity_text.split()).lower()
        
        # Select appropriate database
        db = self.icd_db if entity_type == "CHẨN_ĐOÁN" else self.rxnorm_db
        
        # Strategy 1: Exact match in local DB
        if search_text in db:
            code = db[search_text]
            if code not in candidates:
                candidates.append(code)
        
        # Strategy 2: Fuzzy match in local DB
        best_match = None
        best_score = 0.92
        
        for key, code in db.items():
            score = SequenceMatcher(None, search_text, key).ratio()
            if score > best_score and code not in candidates:
                best_score = score
                best_match = code
        
        if best_match:
            candidates.append(best_match)
        
        return candidates

    def _build_enhanced_prompt(self, text: str) -> str:
        """
        Build optimized prompt for better assertion and type detection.
        """
        return f"""Bạn là hệ thống AI chuyên gia xử lý văn bản y khoa tiếng Việt.

NHIỆM VỤ: Trích xuất thực thể y tế với độ chính xác cao.

LOẠI THỰC THỂ:
1. TRIỆU_CHỨNG: Triệu chứng lâm sàng (ho, đau, sốt, buồn nôn...)
2. TÊN_XÉT_NGHIỆM: Tên xét nghiệm (Công thức máu, WBC, NEUT%, X-quang...)
3. KẾT_QUẢ_XÉT_NGHIỆM: Giá trị số + đơn vị (14.43 G/L, 76.4%, 120 mmHg...)
4. CHẨN_ĐOÁN: Bệnh lý được chẩn đoán (trào ngược dạ dày, viêm phổi...)
5. THUỐC: Tên thuốc + hàm lượng (amlodipine 10mg, aspirin 81mg...)

ASSERTIONS (KIỂM TRA KỸ):
- "isNegated": Có từ phủ định (không, chưa, loại trừ, âm tính, không thấy...)
- "isFamily": Đề cập người thân (bố, mẹ, anh, chị, em, ông, bà, người nhà...)
- "isHistorical": Tiền sử (có tiền sử, đã từng, trước đây, cũ) HOẶC thuốc trước nhập viện

LƯU Ý QUAN TRỌNG:
- Thuốc trong danh sách "trước nhập viện" → isHistorical
- Triệu chứng đi kèm thuốc để điều trị → KHÔNG phải isHistorical
- Phân biệt rõ TÊN_XÉT_NGHIỆM và TRIỆU_CHỨNG
- Chỉ CHẨN_ĐOÁN và THUỐC mới có candidates (ICD-10/RxNorm)

OUTPUT FORMAT: JSON array, mỗi phần tử:
{{
  "text": "chuỗi gốc CHÍNH XÁC trong văn bản",
  "type": "loại thực thể",
  "position": [start, end],
  "assertions": [],
  "candidates": ["mã1", "mã2"]
}}

VĂN BẢN:
{text}

JSON OUTPUT (chỉ trả về JSON, không giải thích):
"""

    def process(self, text: str, use_llm: bool = True, 
                llm_model: str = "qwen2.5:7b") -> List[Dict]:
        """
        Process text with optimizations for competition metrics.
        """
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded")

        entities = []

        # === STRATEGY 1: LLM-based extraction (better for complex contexts) ===
        if use_llm:
            try:
                from ollama import chat
                from ollama import ChatResponse
                
                prompt = self._build_enhanced_prompt(text)
                
                response = chat(model=llm_model, messages=[
                    {'role': 'user', 'content': prompt}
                ])
                
                llm_text = response['message']['content']
                
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', llm_text, re.DOTALL)
                if json_match:
                    llm_entities = json.loads(json_match.group())
                    
                    # Post-process LLM results
                    for ent in llm_entities:
                        # Fix 1: Validate and correct positions (WER optimization)
                        orig_text = ent.get("text", "")
                        pos = self._find_exact_span(text, orig_text)
                        
                        if pos:
                            ent["position"] = list(pos)
                            # Ensure text matches span exactly
                            start, end = pos
                            if text[start:end] != orig_text:
                                ent["text"] = text[start:end]
                            
                            # Fix 2: Enhance candidates (Candidate score optimization)
                            ent_type = ent.get("type", "")
                            llm_candidates = ent.get("candidates", [])
                            enhanced_candidates = self._enhance_candidates(
                                ent["text"], ent_type, llm_candidates
                            )
                            ent["candidates"] = enhanced_candidates
                            
                            # Fix 3: Sanitize assertions
                            valid_assertions = ["isNegated", "isFamily", "isHistorical"]
                            ent["assertions"] = [
                                a for a in ent.get("assertions", []) 
                                if a in valid_assertions
                            ]
                            
                            entities.append(ent)
                
            except Exception as e:
                print(f"  LLM extraction failed: {e}, falling back to rule-based")

        # === STRATEGY 2: Rule-based fallback/augmentation ===
        if not entities:
            print("  Using rule-based extraction...")
            
            # Section detection
            sections = detect_sections(text)
            
            # Rule-based extraction
            rule_mentions = extract_all_rules(text)
            
            # Merge and post-process
            merged = merge_mentions(rule_mentions, text)
            merged = postprocess_mentions(merged, text)
            
            # Assertion detection
            for mention in merged:
                section = None
                for s in sections:
                    if s.start <= mention.start < s.end:
                        section = s
                        break
                
                section_name = section.name if section else ""
                mention.assertions = detect_all_assertions(
                    text, mention.start, mention.end, mention.type, section_name
                )
                
                # Entity linking
                if mention.type in ["THUỐC", "CHẨN_ĐOÁN"] and self.entity_linker:
                    candidates = self.entity_linker.link_entity(
                        mention.text, mention.type, text, top_k=5
                    )
                    # Enhance with local DB
                    enhanced = self._enhance_candidates(mention.text, mention.type, candidates)
                    mention.candidates = enhanced
                else:
                    mention.candidates = []
            
            # Convert to dict format
            for m in merged:
                entities.append({
                    "text": m.text,
                    "type": m.type,
                    "candidates": m.candidates,
                    "assertions": m.assertions,
                    "position": [m.start, m.end],
                })

        # Final validation
        entities, warnings = validate_output(text, entities)
        for w in warnings:
            print(f"  WARNING: {w}")

        return entities

    def process_batch(self, input_dir: str, output_dir: str, 
                     use_llm: bool = True) -> None:
        """Process all files with optimized pipeline."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        input_path = Path(input_dir)
        files = sorted(input_path.glob("*.txt"))
        print(f"\nFound {len(files)} input files")

        for i, filepath in enumerate(files):
            output_filename = filepath.stem + ".json"
            output_filepath = output_path / output_filename

            print(f"\n[{i+1}/{len(files)}] Processing {filepath.name}...")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            entities = self.process(text, use_llm=use_llm)
            save_output(entities, str(output_filepath))

        print(f"\n=== Done! {len(files)} files processed ===")
        print(f"Output saved to: {output_dir}")


def main():
    """Main entry point for optimized inference."""
    import argparse

    parser = argparse.ArgumentParser(description="Optimized Competition Inference")
    parser.add_argument("--input", required=True, help="Input directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--use-llm", action="store_true", default=True, 
                       help="Use LLM for NER (recommended)")
    parser.add_argument("--llm-model", default="qwen2.5:7b", help="LLM model")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-v2-m3")
    args = parser.parse_args()

    config = {
        "embedding_model": args.embedding_model,
        "cross_encoder_model": args.reranker_model,
    }

    pipeline = OptimizedCompetitionPipeline(config)
    pipeline.load()
    pipeline.process_batch(args.input, args.output, use_llm=args.use_llm)


if __name__ == "__main__":
    main()
