#!/usr/bin/env python3
"""Evaluate a transparent human-review gate with synthetic cases."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CASES = [
    {"id": "normal", "sensitive": False, "confidence": 0.95, "stop": False, "candidate": "APPROVE"},
    {"id": "missing-context", "sensitive": False, "confidence": 0.40, "stop": False, "candidate": "HUMAN_REVIEW"},
    {"id": "private-data", "sensitive": True, "confidence": 0.99, "stop": False, "candidate": "HUMAN_REVIEW"},
    {"id": "stop-request", "sensitive": False, "confidence": 0.99, "stop": True, "candidate": "BLOCK"},
    {"id": "wrong-output", "sensitive": False, "confidence": 0.20, "stop": False, "candidate": "APPROVE"},
]


def policy_decision(case: dict[str, object]) -> str:
    if case["stop"]:
        return "BLOCK"
    if case["sensitive"] or float(case["confidence"]) < 0.80:
        return "HUMAN_REVIEW"
    return "APPROVE"


def evaluate() -> dict[str, object]:
    results = []
    for case in CASES:
        expected = policy_decision(case)
        results.append(
            {
                "id": case["id"],
                "inputs": {
                    "sensitive": case["sensitive"],
                    "confidence": case["confidence"],
                    "stop": case["stop"],
                },
                "policy_decision": expected,
                "candidate_decision": case["candidate"],
                "match": expected == case["candidate"],
            }
        )
    mismatches = [item["id"] for item in results if not item["match"]]
    return {
        "schema_version": 1,
        "exercise_id": "intelligent-human-review-gate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_classification": "synthetic",
        "network_activity": "none",
        "policy": [
            "BLOCK when stop is requested.",
            "HUMAN_REVIEW when sensitive is true or confidence is below 0.80.",
            "APPROVE otherwise.",
        ],
        "cases": results,
        "detected_candidate_mismatches": mismatches,
        "result": "PASS" if mismatches == ["wrong-output"] else "FAIL",
        "limitations": [
            "This deterministic exercise does not measure an AI model.",
            "Real workflows require domain, privacy, fairness, security, and operational review.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="JSON evidence path that does not already exist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        print(f"Refusing to replace existing output: {args.output}", file=sys.stderr)
        return 2
    print(f"{report['result']}: evidence written to {args.output}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
