"""
Full Inference Pipeline
Orchestrates all modules for competition inference.
"""
import json
import os
import sys
import io
import time
from typing import List, Dict, Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from normalization import normalize_clinical_text
from preprocessing.section_detector import detect_sections, is_in_medication_section, is_in_history_section
from preprocessing.rule_extractor import extract_all_rules
from ner import NEREnsemble, NERLLMEngine
from ner.span_merger import merge_mentions, postprocess_mentions, MergedMention
from ner.position_align import align_all_positions
from entity_linking import EntityLinker
from assertion.section_aware import detect_all_assertions
from postprocessing import postprocess, fix_entity_type, remove_overlapping_entities
from postprocessing.validator import validate_output, save_output


class CompetitionPipeline:
    """Full competition inference pipeline."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.entity_linker = None
        self._loaded = False

    def load(self):
        """Load all components."""
        print("="*60)
        print("LOADING COMPETITION PIPELINE")
        print("="*60)

        # Entity Linking (FAISS + Cross-Encoder)
        print("\n--- Loading Entity Linking ---")
        self.entity_linker = EntityLinker(
            embedding_model=self.config.get("embedding_model", "BAAI/bge-m3"),
            cross_encoder_model=self.config.get("cross_encoder_model", "BAAI/bge-reranker-v2-m3"),
        )
        self.entity_linker.load()

        self._loaded = True
        print("\n=== Pipeline Loaded ===")

    def process(self, text: str, use_llm: bool = False, llm_model: str = "qwen2.5:7b") -> List[Dict]:
        """Process a single text through the full pipeline."""
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded")

        start_time = time.time()

        # Step 1: Section detection
        sections = detect_sections(text)

        # Step 2: Rule-based extraction
        rule_mentions = extract_all_rules(text)

        # Step 3: NER (if LLM available)
        llm_mentions = []
        if use_llm:
            try:
                ner_engine = NERLLMEngine(model=llm_model)
                ner_results = ner_engine.predict(text)
                for ent in ner_results:
                    llm_mentions.append(MergedMention(
                        text=ent["text"],
                        start=ent["position"][0],
                        end=ent["position"][1],
                        type=ent["type"],
                        confidence=ent.get("confidence", 0.7),
                        sources=["llm"],
                    ))
            except Exception as e:
                print(f"  LLM NER failed: {e}")

        # Step 4: Merge mentions
        all_mentions = rule_mentions + llm_mentions
        merged = merge_mentions(all_mentions, text)

        # Step 5: Post-process (split drug+symptom, verify spans)
        merged = postprocess_mentions(merged, text)

        # Step 6: Assertion detection (section-aware)
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

        # Step 7: Entity linking
        for mention in merged:
            if mention.type in ["THUỐC", "CHẨN_ĐOÁN"]:
                candidates = self.entity_linker.link_entity(
                    mention.text, mention.type, text, top_k=5
                )
                mention.candidates = candidates
            else:
                mention.candidates = []

        # Step 8: Type classification fixes
        for mention in merged:
            mention = fix_entity_type(mention.__dict__)

        # Step 9: Convert to output format
        entities = []
        for m in merged:
            entities.append({
                "text": m.text,
                "type": m.type,
                "candidates": m.candidates,
                "assertions": m.assertions,
                "position": [m.start, m.end],
            })

        # Step 10: Validate
        entities, warnings = validate_output(text, entities)
        for w in warnings:
            print(f"  WARNING: {w}")

        elapsed = time.time() - start_time
        print(f"  Processed in {elapsed:.2f}s, {len(entities)} entities")

        return entities

    def process_file(self, input_path: str, output_path: str, use_llm: bool = False):
        """Process a single file."""
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        entities = self.process(text, use_llm=use_llm)
        save_output(entities, output_path)
        return entities

    def process_batch(self, input_dir: str, output_dir: str, use_llm: bool = False):
        """Process all .txt files in input_dir."""
        os.makedirs(output_dir, exist_ok=True)

        files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
        print(f"\nFound {len(files)} input files")

        for i, filename in enumerate(files):
            input_path = os.path.join(input_dir, filename)
            output_filename = filename.replace(".txt", ".json")
            output_path = os.path.join(output_dir, output_filename)

            print(f"\n[{i+1}/{len(files)}] Processing {filename}...")
            self.process_file(input_path, output_path, use_llm=use_llm)

        print(f"\n=== Done! {len(files)} files processed ===")
        print(f"Output saved to: {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Competition Inference Pipeline")
    parser.add_argument("--input", required=True, help="Input directory with .txt files")
    parser.add_argument("--output", required=True, help="Output directory for .json files")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for NER")
    parser.add_argument("--llm-model", default="qwen2.5:7b", help="LLM model name")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-v2-m3")
    args = parser.parse_args()

    config = {
        "embedding_model": args.embedding_model,
        "cross_encoder_model": args.reranker_model,
    }

    pipeline = CompetitionPipeline(config)
    pipeline.load()
    pipeline.process_batch(args.input, args.output, use_llm=args.use_llm)
