#!/usr/bin/env python3
"""Validate public-safe Pawsfect operating-readiness evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / ".github/portfolio/pawsfect-launch"
DEFAULT_EVIDENCE = PACKET / "P026_LAUNCH_EVIDENCE_TEMPLATE.json"
NATIVE_SOURCE_COMMIT = "ea5e02497e9b5d846be3e19e6ab18b68970114e3"
COORDINATOR_ISSUES = [39, 40, 41, 42, 43, 44, 45]
HELD_DOMAINS = {
    "sxswasted.com", "austinfcsoccer.com", "austinfcsoccer.net",
    "austinfcjerseys.com", "atxsoccerjerseys.com",
}
PROPOSED_PILOT = {
    "status": "proposal_pending_owner_approval",
    "service_model": "managed-walker pilot",
    "included_services": ["individual household dog walks", "simple drop-ins"],
    "excluded_services": [
        "routine pet transportation", "boarding", "group or off-leash walks",
        "medication administration", "in-home sitting",
    ],
}
GATES = [
    ("insurance_and_ccc", 39, {"owner_with_insurer_confirmation"}, []),
    ("service_area_and_availability", 40, {"owner_operations_reviewer"}, ["insurance_and_ccc"]),
    ("intake_and_meet_and_greet", 41, {"owner_operations_security_reviewer"}, ["service_area_and_availability"]),
    ("handling_and_transportation", 42, {"owner_with_insurer_and_care_review"}, ["insurance_and_ccc", "service_area_and_availability"]),
    ("service_agreement", 43, {"owner_with_qualified_legal_review"}, [
        "insurance_and_ccc", "service_area_and_availability",
        "intake_and_meet_and_greet", "handling_and_transportation",
    ]),
    ("cancellation_and_refunds", 44, {"owner_with_qualified_terms_review"}, ["service_agreement"]),
    ("payment_method_and_booking_controls", 45, {"owner_finance_operations_reviewer"}, [
        "service_agreement", "cancellation_and_refunds",
    ]),
]
PENDING_NOTES = {
    "insurance_and_ccc": "Pending insurer confirmation of in-force coverage for the approved model, including care, custody or control; no coverage is claimed.",
    "service_area_and_availability": "Pending owner approval of one initial zone, genuine capacity, travel buffers and private primary or backup coverage.",
    "intake_and_meet_and_greet": "Pending approval and rehearsal of restricted intake, meet-and-greet acceptance criteria and secure access handling.",
    "handling_and_transportation": "Pending approval and rehearsal of handling, weather, escape, injury, no-access and transportation boundaries.",
    "service_agreement": "Pending qualified review, owner approval and a private signature process for the final service agreement.",
    "cancellation_and_refunds": "Pending one approved cancellation and refund policy aligned across the agreement, invoices and support procedure.",
    "payment_method_and_booking_controls": "Pending owner-controlled processor activation and private receipt, refund, settlement and reconciliation tests.",
}
VERIFIED_NOTE = (
    "Gate marked verified by the owner; supporting evidence remains private "
    "and must be independently checked before reliance."
)
GATE_FIELDS = {
    "id", "issue", "status", "checked_at", "reviewer_role",
    "private_evidence_recorded", "notes",
}
ROOT_FIELDS = {
    "version", "project", "source_repository", "native_source_commit",
    "coordinator_issues", "proposed_pilot",
    "p003_operating_requirements_complete", "owner_operating_approved_at",
    "commercial_hosting_verified", "public_inquiry_receipt_verified",
    "owner_go_live_authorized", "bookings_authorized",
    "payment_collection_authorized", "recruiting_authorized",
    "paid_care_launch_ready", "gates",
}
PERMANENT_FALSE_FIELDS = (
    "commercial_hosting_verified", "public_inquiry_receipt_verified",
    "owner_go_live_authorized", "bookings_authorized",
    "payment_collection_authorized", "recruiting_authorized",
    "paid_care_launch_ready",
)
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b\d{1,6}\s+[A-Za-z0-9.' -]+\s(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|boulevard|blvd)\b", re.I),
    re.compile(r"\b(?:policy|quote|claim|account|routing|invoice|transaction)[-_ ]?(?:number|id)?\s*[:=]\s*[A-Za-z0-9-]{4,}\b", re.I),
    re.compile(r"\b(?:customer|client|walker|dog)[-_ ]?(?:name|id|address|record)\s*[:=]", re.I),
    re.compile(r"\b(?:password|secret|api[_ -]?key|door code|access code|medical record|bank|tax id)\s*[:=]", re.I),
)


class LaunchEvidenceError(ValueError):
    """A Pawsfect operating-readiness boundary failed."""


def reject_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def _assert_safe_file(path: Path) -> None:
    absolute = path.absolute()
    cursor = absolute
    while True:
        try:
            info = cursor.lstat()
        except OSError as exc:
            raise LaunchEvidenceError(f"Unsafe JSON path: {path}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise LaunchEvidenceError(f"Unsafe JSON path: {path}")
        if cursor == absolute:
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65_536:
                raise LaunchEvidenceError(f"Unsafe JSON file: {path}")
        if cursor.parent == cursor:
            break
        cursor = cursor.parent


def read_json(path: Path) -> object:
    try:
        _assert_safe_file(path)
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except LaunchEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise LaunchEvidenceError(f"Cannot read JSON: {path}") from exc


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    normalized = parsed.astimezone(timezone.utc)
    return normalized if normalized <= datetime.now(timezone.utc) else None


def has_sensitive_or_held_text(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=True)
    lowered = text.lower()
    return any(domain in lowered for domain in HELD_DOMAINS) or any(
        pattern.search(text) for pattern in SENSITIVE_PATTERNS
    )


def validate_evidence(path: Path = DEFAULT_EVIDENCE) -> dict:
    value = read_json(path)
    if not isinstance(value, dict) or set(value) != ROOT_FIELDS:
        raise LaunchEvidenceError("Evidence root does not match the reviewed schema")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise LaunchEvidenceError("Evidence version must be integer 1")
    if (
        value.get("project") != "Pawsfect Walks operating readiness"
        or value.get("source_repository") != "jordanistan/PawfectWalks"
        or value.get("native_source_commit") != NATIVE_SOURCE_COMMIT
        or value.get("coordinator_issues") != COORDINATOR_ISSUES
        or value.get("proposed_pilot") != PROPOSED_PILOT
    ):
        raise LaunchEvidenceError("Evidence source or proposed pilot boundary is invalid")
    if has_sensitive_or_held_text(value):
        raise LaunchEvidenceError("Evidence contains sensitive-looking data or a held domain")

    gates = value.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise LaunchEvidenceError("Evidence must contain all seven operating gates")
    statuses: dict[str, str] = {}
    gate_times: dict[str, datetime] = {}
    for item, (gate_id, issue, roles, dependencies) in zip(gates, GATES):
        if (
            not isinstance(item, dict)
            or set(item) != GATE_FIELDS
            or item.get("id") != gate_id
            or item.get("issue") != issue
            or type(item.get("issue")) is not int
        ):
            raise LaunchEvidenceError("Operating gate identity, issue, order or fields are invalid")
        status = item.get("status")
        if status == "pending":
            if (
                item.get("checked_at") != ""
                or item.get("reviewer_role") != ""
                or item.get("private_evidence_recorded") is not False
                or item.get("notes") != PENDING_NOTES[gate_id]
            ):
                raise LaunchEvidenceError("Pending gate cannot contain completion claims")
        elif status == "verified":
            if any(statuses.get(dependency) != "verified" for dependency in dependencies):
                raise LaunchEvidenceError("Operating gates must be verified in dependency order")
            if item.get("reviewer_role") not in roles:
                raise LaunchEvidenceError("Operating gate lacks the reviewed role label")
            checked_at = parse_timestamp(item.get("checked_at"))
            if item.get("private_evidence_recorded") is not True or checked_at is None:
                raise LaunchEvidenceError("Verified gate lacks a dated private-evidence attestation")
            if any(checked_at < gate_times[dependency] for dependency in dependencies):
                raise LaunchEvidenceError("Operating gate predates a required dependency")
            if item.get("notes") != VERIFIED_NOTE:
                raise LaunchEvidenceError("Verified gate must use the fixed public note")
            gate_times[gate_id] = checked_at
        else:
            raise LaunchEvidenceError("Unknown operating gate status")
        statuses[gate_id] = status

    completed = value.get("p003_operating_requirements_complete")
    if not isinstance(completed, bool):
        raise LaunchEvidenceError("p003_operating_requirements_complete must be boolean")
    approved_at_value = value.get("owner_operating_approved_at")
    if completed:
        if any(status != "verified" for status in statuses.values()):
            raise LaunchEvidenceError("Operating requirements cannot be complete while a gate is pending")
        approved_at = parse_timestamp(approved_at_value)
        if approved_at is None:
            raise LaunchEvidenceError("Completed operating requirements need a current owner approval timestamp")
        if approved_at < max(gate_times.values()):
            raise LaunchEvidenceError("Owner approval timestamp cannot predate the final gate")
    elif approved_at_value is not None:
        raise LaunchEvidenceError("Incomplete operating requirements cannot contain an approval timestamp")

    for key in PERMANENT_FALSE_FIELDS:
        if value.get(key) is not False:
            raise LaunchEvidenceError(f"P026 cannot set {key}")
    return {"p003_operating_requirements_complete": completed, "statuses": statuses}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--path", type=Path, default=DEFAULT_EVIDENCE)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = validate_evidence(args.path)
    except LaunchEvidenceError as exc:
        print(f"Pawsfect launch evidence validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
