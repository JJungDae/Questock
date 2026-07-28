from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_m5_d1_evidence_comparisons import classify_title_pair

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_FIXTURE = _ROOT / "tests" / "fixtures" / "m5_d1_event_pairs.json"


def evaluate_event_pairs(payload: dict[str, Any]) -> dict[str, Any]:
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("event pair fixture is invalid")
    evaluation = [
        item for item in pairs if item.get("partition") == "evaluation"
    ]
    true_positive = false_positive = false_negative = true_negative = 0
    results = []
    for item in evaluation:
        predicted = classify_title_pair(
            left_title=item["left_title"],
            right_title=item["right_title"],
            hours_apart=item["hours_apart"],
        )
        expected = item["expected_same_event"]
        if predicted and expected:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif expected:
            false_negative += 1
        else:
            true_negative += 1
        results.append(
            {
                "pair_id": item["pair_id"],
                "expected": expected,
                "predicted": predicted,
            }
        )
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 1.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 1.0
    )
    return {
        "schema_version": "m5-d1-event-evaluation-v1",
        "evaluation_pair_count": len(evaluation),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "results": results,
    }


def main() -> int:
    payload = json.loads(_DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    result = evaluate_event_pairs(payload)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["precision"] >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
