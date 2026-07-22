"""
Module 10: Local Evaluation Harness
Calculates text_score, assertions_score, candidates_score, final_score
matching the competition's metric formula.
"""
import json
import os
import re
from typing import List, Dict, Tuple


def normalize_text_for_wer(text: str) -> str:
    """Normalize text for WER calculation."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate between reference and hypothesis."""
    ref = normalize_text_for_wer(reference).split()
    hyp = normalize_text_for_wer(hypothesis).split()

    # Special case: both empty
    if not ref and not hyp:
        return 0.0

    # DP-based WER
    n = len(ref)
    m = len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitution = d[i - 1][j - 1] + 1
                insertion = d[i][j - 1] + 1
                deletion = d[i - 1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)

    return d[n][m] / max(n, 1)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / max(union, 1)


def calculate_sample_metrics(
    ground_truth: List[dict],
    prediction: List[dict],
) -> dict:
    """Calculate metrics for a single sample."""
    # --- text_score ---
    text_scores = []
    for pred_ent in prediction:
        best_wer = 1.0
        for gt_ent in ground_truth:
            if gt_ent["type"] == pred_ent["type"]:
                w = wer(gt_ent["text"], pred_ent["text"])
                best_wer = min(best_wer, w)
            else:
                # Wrong type counts as creating new concept -> WER = 1
                pass
        # If no matching type found, this is a new concept -> penalty
        if best_wer == 1.0 and pred_ent["type"] not in [gt["type"] for gt in ground_truth]:
            # Check if this type exists in ground truth at all
            gt_types = set(gt["type"] for gt in ground_truth)
            if pred_ent["type"] not in gt_types:
                best_wer = 1.0  # New concept, full penalty
        text_scores.append(1.0 - best_wer)

    # Also check ground truth concepts not in prediction
    for gt_ent in ground_truth:
        found = False
        for pred_ent in prediction:
            if pred_ent["type"] == gt_ent["type"]:
                w = wer(gt_ent["text"], pred_ent["text"])
                if w < 0.5:  # Close enough match
                    found = True
                    break
        if not found:
            text_scores.append(0.0)  # Missing concept

    text_score = sum(text_scores) / max(len(text_scores), 1)

    # --- assertions_score ---
    assertion_scores = []
    for pred_ent in prediction:
        gt_assertions = set()
        for gt_ent in ground_truth:
            if (gt_ent["type"] == pred_ent["type"] and
                wer(gt_ent["text"], pred_ent["text"]) < 0.3):
                gt_assertions = set(gt_ent.get("assertions", []))
                break

        pred_assertions = set(pred_ent.get("assertions", []))
        j = jaccard_similarity(gt_assertions, pred_assertions)
        assertion_scores.append(j)

    # Check ground truth assertions not matched
    for gt_ent in ground_truth:
        found = False
        for pred_ent in prediction:
            if (pred_ent["type"] == gt_ent["type"] and
                wer(gt_ent["text"], pred_ent["text"]) < 0.3):
                found = True
                break
        if not found:
            assertion_scores.append(0.0)

    assertions_score = sum(assertion_scores) / max(len(assertion_scores), 1)

    # --- candidates_score ---
    candidate_scores = []
    weights = []

    for gt_ent in ground_truth:
        gt_candidates = set(str(c) for c in gt_ent.get("candidates", []))
        weight = len(gt_candidates) + 1

        # Find matching prediction
        best_j = 0.0
        for pred_ent in prediction:
            if (pred_ent["type"] == gt_ent["type"] and
                wer(gt_ent["text"], pred_ent["text"]) < 0.3):
                pred_candidates = set(str(c) for c in pred_ent.get("candidates", []))
                best_j = jaccard_similarity(gt_candidates, pred_candidates)
                break

        candidate_scores.append(best_j * weight)
        weights.append(weight)

    # Check prediction candidates not in ground truth
    for pred_ent in prediction:
        if pred_ent["type"] in ["CHẨN_ĐOÁN", "THUỐC"]:
            found = False
            for gt_ent in ground_truth:
                if (gt_ent["type"] == pred_ent["type"] and
                    wer(gt_ent["text"], pred_ent["text"]) < 0.3):
                    found = True
                    break
            if not found:
                # No matching ground truth -> penalty
                candidate_scores.append(0.0)
                weights.append(1)

    candidates_score = sum(candidate_scores) / max(sum(weights), 1)

    return {
        "text_score": text_score,
        "assertions_score": assertions_score,
        "candidates_score": candidates_score,
    }


def calculate_final_score(metrics: dict) -> float:
    """Calculate final score from component scores."""
    return (
        0.3 * metrics["text_score"] +
        0.3 * metrics["assertions_score"] +
        0.4 * metrics["candidates_score"]
    )


def evaluate_dataset(
    predictions_dir: str,
    ground_truth_dir: str,
) -> dict:
    """Evaluate entire dataset."""
    all_metrics = []

    for i in range(1, 101):
        pred_path = os.path.join(predictions_dir, f"{i}.json")
        gt_path = os.path.join(ground_truth_dir, f"{i}.json")

        if not os.path.exists(pred_path) or not os.path.exists(gt_path):
            continue

        with open(pred_path, "r", encoding="utf-8") as f:
            pred = json.load(f)
        with open(gt_path, "r", encoding="utf-8") as f:
            gt = json.load(f)

        metrics = calculate_sample_metrics(gt, pred)
        metrics["sample_id"] = i
        all_metrics.append(metrics)

    if not all_metrics:
        return {"error": "No samples found"}

    avg_metrics = {
        "text_score": sum(m["text_score"] for m in all_metrics) / len(all_metrics),
        "assertions_score": sum(m["assertions_score"] for m in all_metrics) / len(all_metrics),
        "candidates_score": sum(m["candidates_score"] for m in all_metrics) / len(all_metrics),
    }
    avg_metrics["final_score"] = calculate_final_score(avg_metrics)
    avg_metrics["n_samples"] = len(all_metrics)

    return avg_metrics


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 3:
        print("Usage: python evaluator.py <predictions_dir> <ground_truth_dir>")
        sys.exit(1)

    results = evaluate_dataset(sys.argv[1], sys.argv[2])
    print(json.dumps(results, indent=2, ensure_ascii=False))
