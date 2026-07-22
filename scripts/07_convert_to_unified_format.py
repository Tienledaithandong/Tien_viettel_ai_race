"""
Script 07: Convert all raw data into unified training format
Input: datasets/synthetic/, datasets/scraped/
Output: datasets/unified/train.json
"""
import json
import os
import re
import random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets")
UNIFIED_DIR = os.path.join(DATASETS_DIR, "unified")


def find_position(text: str, entity_text: str) -> list:
    """Find the position of entity_text in text."""
    idx = text.lower().find(entity_text.lower())
    if idx >= 0:
        return [idx, idx + len(entity_text)]
    return [-1, -1]


def normalize_concept(concept: dict, full_text: str) -> dict:
    """Normalize a concept entry."""
    text = concept.get("text", "").strip()
    if not text:
        return None

    ctype = concept.get("type", "")
    valid_types = ["TRIỆU_CHỨNG", "THUỐC", "CHẨN_ĐOÁN", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"]
    if ctype not in valid_types:
        return None

    position = concept.get("position", [-1, -1])
    if position == [-1, -1] or position[0] < 0:
        position = find_position(full_text, text)

    assertions = concept.get("assertions", [])
    valid_assertions = ["isNegated", "isFamily", "isHistorical"]
    assertions = [a for a in assertions if a in valid_assertions]

    candidates = concept.get("candidates", [])
    candidates = [str(c) for c in candidates if c]

    return {
        "text": text,
        "type": ctype,
        "assertions": assertions,
        "position": position,
        "candidates": candidates,
    }


def convert_synthetic_data(data: list) -> list:
    """Convert synthetic data to unified format."""
    converted = []
    for item in data:
        text = item.get("text", "")
        if not text or len(text) < 10:
            continue

        concepts = item.get("concepts", [])
        if not concepts:
            continue

        normalized_concepts = []
        for concept in concepts:
            nc = normalize_concept(concept, text)
            if nc:
                normalized_concepts.append(nc)

        if normalized_concepts:
            converted.append({
                "id": item.get("id", ""),
                "text": text,
                "concepts": normalized_concepts,
                "source": item.get("phase", "synthetic"),
            })

    return converted


def extract_medical_text_from_scraped(data: list) -> list:
    """Extract usable medical text from scraped data."""
    results = []
    for item in data:
        content = item.get("content", "")
        if not content or len(content) < 30:
            continue

        sentences = re.split(r'[.!?]', content)
        medical_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20:
                medical_keywords = [
                    "bệnh", "triệu chứng", "điều trị", "thuốc", "khám",
                    "xét nghiệm", "chẩn đoán", "viêm", "đau", "sốt",
                    "ho", "khó thở", "tiểu đường", "huyết áp", "tim",
                    "phổi", "bụng", "gan", "thận", "khớp"
                ]
                if any(kw in sent.lower() for kw in medical_keywords):
                    medical_sentences.append(sent)

        if medical_sentences:
            results.append({
                "text": ". ".join(medical_sentences[:3]),
                "concepts": [],
                "source": item.get("source", "scraped"),
            })

    return results


def load_all_datasets() -> list:
    """Load all available datasets."""
    all_data = []

    # Synthetic data
    synthetic_path = os.path.join(DATASETS_DIR, "synthetic", "synthetic_data.json")
    if os.path.exists(synthetic_path):
        with open(synthetic_path, "r", encoding="utf-8") as f:
            synthetic = json.load(f)
        print(f"Loaded {len(synthetic)} synthetic samples")
        all_data.extend(convert_synthetic_data(synthetic))

    # Scraped data
    scraped_dir = os.path.join(DATASETS_DIR, "scraped")
    if os.path.exists(scraped_dir):
        for filename in os.listdir(scraped_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(scraped_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    scraped = json.load(f)
                print(f"Loaded {len(scraped)} scraped samples from {filename}")
                converted = extract_medical_text_from_scraped(scraped)
                all_data.extend(converted)

    return all_data


def validate_data(data: list) -> dict:
    """Validate dataset quality."""
    stats = {
        "total": len(data),
        "with_concepts": sum(1 for d in data if d.get("concepts")),
        "without_concepts": sum(1 for d in data if not d.get("concepts")),
        "type_distribution": {},
        "assertion_distribution": {},
        "avg_concepts_per_sample": 0,
        "avg_text_length": 0,
    }

    total_concepts = 0
    total_text_len = 0
    type_dist = {}
    assertion_dist = {}

    for item in data:
        text = item.get("text", "")
        total_text_len += len(text)

        concepts = item.get("concepts", [])
        total_concepts += len(concepts)

        for concept in concepts:
            ctype = concept.get("type", "unknown")
            type_dist[ctype] = type_dist.get(ctype, 0) + 1

            for assertion in concept.get("assertions", []):
                assertion_dist[assertion] = assertion_dist.get(assertion, 0) + 1

    stats["type_distribution"] = type_dist
    stats["assertion_distribution"] = assertion_dist
    stats["avg_concepts_per_sample"] = total_concepts / max(len(data), 1)
    stats["avg_text_length"] = total_text_len / max(len(data), 1)

    return stats


def create_train_val_split(data: list, val_ratio: float = 0.1):
    """Split data into train and validation sets."""
    random.seed(42)
    random.shuffle(data)

    val_size = int(len(data) * val_ratio)
    val_data = data[:val_size]
    train_data = data[val_size:]

    return train_data, val_data


if __name__ == "__main__":
    os.makedirs(UNIFIED_DIR, exist_ok=True)

    print("=== Loading All Datasets ===")
    all_data = load_all_datasets()

    print(f"\n=== Total: {len(all_data)} samples ===")

    print("\n=== Validating Data Quality ===")
    stats = validate_data(all_data)
    print(f"  Total samples: {stats['total']}")
    print(f"  With concepts: {stats['with_concepts']}")
    print(f"  Without concepts: {stats['without_concepts']}")
    print(f"  Avg concepts/sample: {stats['avg_concepts_per_sample']:.1f}")
    print(f"  Avg text length: {stats['avg_text_length']:.0f} chars")
    print(f"  Type distribution: {json.dumps(stats['type_distribution'], ensure_ascii=False)}")
    print(f"  Assertion distribution: {json.dumps(stats['assertion_distribution'], ensure_ascii=False)}")

    print("\n=== Splitting Train/Val ===")
    train_data, val_data = create_train_val_split(all_data)
    print(f"  Train: {len(train_data)} samples")
    print(f"  Val: {len(val_data)} samples")

    train_path = os.path.join(UNIFIED_DIR, "train.json")
    val_path = os.path.join(UNIFIED_DIR, "val.json")

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved train to {train_path}")
    print(f"Saved val to {val_path}")

    # Save stats
    stats_path = os.path.join(UNIFIED_DIR, "stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"Saved stats to {stats_path}")
