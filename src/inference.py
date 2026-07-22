"""
Full Inference Pipeline
Orchestrates all modules for competition inference.
"""
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional

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


class CompetitionPipeline:
    """Full competition inference pipeline."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.entity_linker: Optional[EntityLinker] = None
        self._loaded = False

    def load(self) -> None:
        """Load all components."""
        print("=" * 60)
        print("LOADING COMPETITION PIPELINE")
        print("=" * 60)

        # Load Entity Linking (FAISS + Cross-Encoder)
        print("\n--- Loading Entity Linking ---")
        self.entity_linker = EntityLinker(
            embedding_model=self.config.get(
                "embedding_model", "BAAI/bge-m3"
            ),
            cross_encoder_model=self.config.get(
                "cross_encoder_model", "BAAI/bge-reranker-v2-m3"
            ),
        )
        self.entity_linker.load()

        self._loaded = True
        print("\n=== Pipeline Loaded ===")

    def process(
        self, 
        text: str, 
        use_llm: bool = False, 
        llm_model: str = "qwen2.5:7b"
    ) -> List[Dict]:
        """
        Process a single text through the full pipeline.
        
        Args:
            text: Input clinical text
            use_llm: Whether to use LLM for NER
            llm_model: LLM model name to use
            
        Returns:
            List of entities
        """
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded")

        start_time = time.time()

        # Step 1: Section detection
        sections = detect_sections(text)

        # Step 2: Rule-based extraction
        rule_mentions = extract_all_rules(text)

        # Step 3: NER (if LLM available)
        llm_mentions: List[MergedMention] = []
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

    def process_file(
        self, 
        input_path: str, 
        output_path: str, 
        use_llm: bool = False
    ) -> List[Dict]:
        """Process a single file."""
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        entities = self.process(text, use_llm=use_llm)
        save_output(entities, output_path)
        return entities

    def process_batch(
        self, 
        input_dir: str, 
        output_dir: str, 
        use_llm: bool = False
    ) -> None:
        """Process all .txt files in input_dir."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        input_path = Path(input_dir)
        files = sorted(input_path.glob("*.txt"))
        print(f"\nFound {len(files)} input files")

        for i, filepath in enumerate(files):
            output_filename = filepath.stem + ".json"
            output_filepath = output_path / output_filename

            print(f"\n[{i+1}/{len(files)}] Processing {filepath.name}...")
            self.process_file(str(filepath), str(output_filepath), use_llm=use_llm)

        print(f"\n=== Done! {len(files)} files processed ===")
        print(f"Output saved to: {output_dir}")


def main():
    """Main entry point for competition inference."""
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


if __name__ == "__main__":
    main()
