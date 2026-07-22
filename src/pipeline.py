"""
Main Medical NLP Pipeline
Orchestrates all modules: Normalization -> NER -> Alignment -> Linking -> Assertions -> Postprocessing
"""
import json
import os
import sys
import time
from typing import List, Dict, Optional

# Add src to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from normalization import normalize_clinical_text, create_normalization_mapping, remap_positions
from ner import NEREnsemble, NERLLMEngine, NERTransformerEngine
from ner.position_align import align_all_positions
from entity_linking import EntityLinker
from assertion import AssertionDetector
from postprocessing import postprocess, remove_overlapping_entities, fix_entity_type


class MedicalNLPPipeline:
    """Complete Medical NLP pipeline."""

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.ner_ensemble = None
        self.entity_linker = None
        self.assertion_detector = None
        self._loaded = False

    def _default_config(self) -> Dict:
        return {
            "ner": {
                "llm_models": ["qwen2.5:7b", "gemma3:4b"],
                "llm_url": "http://localhost:11434",
                "transformer_models": [],
                "n_runs": 3,
            },
            "entity_linking": {
                "embedding_model": "BAAI/bge-m3",
                "cross_encoder_model": "BAAI/bge-reranker-v2-m3",
                "top_k": 5,
            },
            "assertion": {
                "use_classifier": False,
                "window_size": 50,
            },
            "normalization": {
                "enabled": True,
            },
        }

    def load(self):
        """Load all pipeline components."""
        print("="*60)
        print("LOADING MEDICAL NLP PIPELINE")
        print("="*60)

        # NER Ensemble
        print("\n--- Loading NER ---")
        self.ner_ensemble = NEREnsemble()
        for model in self.config["ner"].get("llm_models", []):
            engine = NERLLMEngine(
                model=model,
                base_url=self.config["ner"].get("llm_url", "http://localhost:11434"),
            )
            self.ner_ensemble.add_engine(engine)
            print(f"  Added LLM engine: {model}")

        for model_path in self.config["ner"].get("transformer_models", []):
            engine = NERTransformerEngine(model_path)
            engine.load()
            self.ner_ensemble.add_engine(engine)

        # Entity Linking
        print("\n--- Loading Entity Linking ---")
        self.entity_linker = EntityLinker(
            embedding_model=self.config["entity_linking"].get("embedding_model", "BAAI/bge-m3"),
            cross_encoder_model=self.config["entity_linking"].get("cross_encoder_model", "BAAI/bge-reranker-v2-m3"),
        )
        self.entity_linker.load()

        # Assertion Detection
        print("\n--- Loading Assertion Detection ---")
        self.assertion_detector = AssertionDetector(
            use_classifier=self.config["assertion"].get("use_classifier", False),
            model_path=self.config["assertion"].get("classifier_path"),
        )

        self._loaded = True
        print("\n=== Pipeline Loaded ===")

    def process(self, text: str) -> List[Dict]:
        """
        Process a single clinical text through the full pipeline.
        Returns list of entities in competition JSON format.
        """
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded. Call load() first.")

        start_time = time.time()

        # Step 1: Normalize
        if self.config["normalization"].get("enabled", True):
            normalized_text = normalize_clinical_text(text)
            orig_to_norm, norm_to_orig = create_normalization_mapping(text, normalized_text)
        else:
            normalized_text = text
            norm_to_orig = {i: i for i in range(len(text))}

        # Step 2: NER (on normalized text)
        entities = self.ner_ensemble.predict(
            normalized_text,
            n_runs=self.config["ner"].get("n_runs", 3),
        )

        # Step 3: Position Alignment (map back to original text)
        if self.config["normalization"].get("enabled", True):
            entities = align_all_positions(text, entities)
        else:
            entities = align_all_positions(text, entities)

        # Step 4: Assertion Detection
        entities = self.assertion_detector.detect_all(
            text,
            entities,
            window_size=self.config["assertion"].get("window_size", 50),
        )

        # Step 5: Entity Linking
        top_k = self.config["entity_linking"].get("top_k", 5)
        entities = self.entity_linker.link_entities(
            entities, text, top_k=top_k,
        )

        # Step 6: Post-processing
        output = postprocess(text, entities)

        elapsed = time.time() - start_time
        print(f"  Processed in {elapsed:.2f}s, {len(output)} entities found")

        return output

    def process_batch(self, texts: List[Dict], output_dir: str = None) -> List[Dict]:
        """
        Process a batch of texts.
        Input: list of {"id": "1", "text": "..."}
        Output: list of {"id": "1", "entities": [...]}
        """
        results = []
        total = len(texts)

        for i, item in enumerate(texts):
            text_id = item.get("id", str(i + 1))
            text = item.get("text", "")

            print(f"\n[{i+1}/{total}] Processing {text_id}...")

            entities = self.process(text)
            result = {
                "id": text_id,
                "text": text,
                "entities": entities,
            }
            results.append(result)

            # Save individual output
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{text_id}.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(entities, f, ensure_ascii=False, indent=2)

        return results


def run_inference(
    input_dir: str,
    output_dir: str,
    config_path: str = None,
):
    """Run inference on all .txt files in input_dir."""
    # Load config
    config = None
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    # Initialize pipeline
    pipeline = MedicalNLPPipeline(config)
    pipeline.load()

    # Read input files
    texts = []
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith(".txt"):
            filepath = os.path.join(input_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().strip()
            text_id = filename.replace(".txt", "")
            texts.append({"id": text_id, "text": text})

    print(f"\nFound {len(texts)} input files")

    # Process
    results = pipeline.process_batch(texts, output_dir)

    print(f"\n=== Done! {len(results)} files processed ===")
    print(f"Output saved to: {output_dir}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Medical NLP Pipeline")
    parser.add_argument("--input", required=True, help="Input directory with .txt files")
    parser.add_argument("--output", required=True, help="Output directory for .json files")
    parser.add_argument("--config", default=None, help="Pipeline config JSON file")
    args = parser.parse_args()

    run_inference(args.input, args.output, args.config)
