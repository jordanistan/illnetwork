#!/usr/bin/env python3
"""Validate public-safe SpaceGhostKilla consulting-readiness evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / ".github/portfolio/spaceghostkilla-consulting"
DEFAULT_EVIDENCE = PACKET / "P027_CONSULTING_EVIDENCE_TEMPLATE.json"
NATIVE_SOURCE_COMMIT = "57e38f934a6ab5feedb7e855ac4472966af895cd"
COORDINATOR_ISSUE = 110
SOURCE_PATHS = [
    "docs/consulting/00_Consulting_Launch.md",
    "docs/consulting/01_Inquiry_and_Fit.md",
    "docs/consulting/02_Scope_and_Authorization.md",
    "docs/consulting/03_Evidence_Handling.md",
    "docs/consulting/04_Delivery_and_Closeout.md",
    "docs/consulting/05_Owner_Decisions.md",
]
HELD_DOMAINS = {
    "sxswasted.com", "austinfcsoccer.com", "austinfcsoccer.net",
    "austinfcjerseys.com", "atxsoccerjerseys.com",
}
PROPOSED_OFFER = {
    "status": "proposal_pending_owner_approval",
    "boundary": "one Entra identity OR one CI/CD evidence review",
    "direct_system_access": "excluded_by_default",
    "production_changes": "excluded",
    "certification": "not_offered",
}
ENGAGEMENT_BOUNDARY = {
    "status": "not_evaluated_by_p027",
    "required_for_each_engagement": True,
    "requirements": [
        "verified client authority and asset control",
        "written approved activities and time window",
        "applicable third-party permissions",
        "approved stop and revocation path",
    ],
}
GATES = [
    ("outside_work_boundaries", {"owner_with_appropriate_private_review"}, []),
    ("account_protections", {"owner_admin_security_reviewer"}, ["outside_work_boundaries"]),
    ("offer_and_capacity", {"owner_operations_reviewer"}, [
        "outside_work_boundaries", "account_protections",
    ]),
    ("final_fee_and_quote_process", {"owner_finance_operations_reviewer"}, ["offer_and_capacity"]),
    ("client_commercial_terms_framework", {"owner_with_qualified_commercial_terms_review"}, [
        "outside_work_boundaries", "offer_and_capacity", "final_fee_and_quote_process",
    ]),
    ("private_evidence_channel", {"owner_security_privacy_reviewer"}, [
        "outside_work_boundaries", "account_protections", "offer_and_capacity",
    ]),
    ("invoice_and_payment_process", {"owner_finance_operations_reviewer"}, [
        "final_fee_and_quote_process", "client_commercial_terms_framework",
    ]),
    ("commercial_inquiry_hosting", {"owner_operations_security_reviewer"}, [
        "outside_work_boundaries", "account_protections", "offer_and_capacity",
        "final_fee_and_quote_process", "client_commercial_terms_framework",
        "private_evidence_channel", "invoice_and_payment_process",
    ]),
]
PENDING_NOTES = {
    "outside_work_boundaries": "Pending private review of applicable employer, confidentiality and conflict boundaries; no permission is claimed.",
    "offer_and_capacity": "Pending owner approval of one evidence-review boundary, deliverables, exclusions, revision allowance and actual capacity.",
    "final_fee_and_quote_process": "Pending owner approval of the quote process based on reviewed effort and costs; no final client fee is approved.",
    "client_commercial_terms_framework": "Pending appropriate review and owner approval of the private commercial-terms framework; no client agreement is executed.",
    "private_evidence_channel": "Pending verification of restricted transfer, storage, readers, tools, incident contact and retention or deletion controls.",
    "invoice_and_payment_process": "Pending private verification of the owner-controlled invoice, payment, payout and refund process; no invoice or payment is claimed.",
    "account_protections": "Pending owner or administrator verification of applicable MFA, secret scanning, push protection and branch rules.",
    "commercial_inquiry_hosting": "Pending authenticated commercial staging, HTTPS and header checks, download checks, and harmless inquiry receipt and reply verification.",
}
VERIFIED_NOTE = (
    "Gate marked verified by the owner; supporting evidence remains private "
    "and must be independently checked before reliance."
)
GATE_FIELDS = {
    "id", "status", "checked_at", "reviewer_role",
    "private_evidence_recorded", "notes",
}
ROOT_FIELDS = {
    "version", "project", "source_repository", "native_source_commit", "source_paths",
    "coordinator_issue", "proposed_offer", "engagement_boundary",
    "per_engagement_authorization_required",
    "p004_global_requirements_complete", "owner_global_approved_at",
    "commercial_launch_ready", "owner_go_live_authorized", "outreach_authorized",
    "client_authority_verified", "client_engagement_authorized",
    "system_access_authorized", "evidence_received", "client_work_started",
    "invoice_issued", "payment_received", "customer_acquired", "revenue_earned",
    "field_manual_released", "kubescan_released", "other_paid_product_released", "gates",
}
PERMANENT_FALSE_FIELDS = (
    "commercial_launch_ready", "owner_go_live_authorized", "outreach_authorized",
    "client_authority_verified", "client_engagement_authorized",
    "system_access_authorized", "evidence_received", "client_work_started",
    "invoice_issued", "payment_received", "customer_acquired", "revenue_earned",
    "field_manual_released", "kubescan_released", "other_paid_product_released",
)
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b(?:tenant|client|customer|employer|invoice|account|routing|transaction|quote)[-_ ]?(?:name|number|id|address)?\s*[:=]\s*[A-Za-z0-9-]{4,}\b", re.I),
    re.compile(r"\b(?:password|secret|api[_ -]?key|token|evidence link|bank|tax id)\s*[:=]", re.I),
)


class ConsultingEvidenceError(ValueError):
    """A SpaceGhostKilla consulting-readiness boundary failed."""


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
            raise ConsultingEvidenceError(f"Unsafe JSON path: {path}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ConsultingEvidenceError(f"Unsafe JSON path: {path}")
        if cursor == absolute:
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65_536:
                raise ConsultingEvidenceError(f"Unsafe JSON file: {path}")
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
    except ConsultingEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ConsultingEvidenceError(f"Cannot read JSON: {path}") from exc


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
        raise ConsultingEvidenceError("Evidence root does not match the reviewed schema")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise ConsultingEvidenceError("Evidence version must be integer 1")
    if (
        value.get("project") != "SpaceGhostKilla consulting readiness"
        or value.get("source_repository") != "jordanistan/spaceghostkilla"
        or value.get("native_source_commit") != NATIVE_SOURCE_COMMIT
        or value.get("source_paths") != SOURCE_PATHS
        or value.get("coordinator_issue") != COORDINATOR_ISSUE
        or type(value.get("coordinator_issue")) is not int
        or value.get("proposed_offer") != PROPOSED_OFFER
        or value.get("engagement_boundary") != ENGAGEMENT_BOUNDARY
        or value.get("per_engagement_authorization_required") is not True
    ):
        raise ConsultingEvidenceError("Evidence source, offer or engagement boundary is invalid")
    if has_sensitive_or_held_text(value):
        raise ConsultingEvidenceError("Evidence contains sensitive-looking data or a held domain")

    gates = value.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise ConsultingEvidenceError("Evidence must contain all eight global gates")
    statuses: dict[str, str] = {}
    gate_times: dict[str, datetime] = {}
    for item, (gate_id, roles, dependencies) in zip(gates, GATES):
        if (
            not isinstance(item, dict)
            or set(item) != GATE_FIELDS
            or item.get("id") != gate_id
        ):
            raise ConsultingEvidenceError("Global gate identity, order or fields are invalid")
        status = item.get("status")
        if status == "pending":
            if (
                item.get("checked_at") != ""
                or item.get("reviewer_role") != ""
                or item.get("private_evidence_recorded") is not False
                or item.get("notes") != PENDING_NOTES[gate_id]
            ):
                raise ConsultingEvidenceError("Pending gate cannot contain completion claims")
        elif status == "verified":
            if any(statuses.get(dependency) != "verified" for dependency in dependencies):
                raise ConsultingEvidenceError("Global gates must be verified in dependency order")
            if item.get("reviewer_role") not in roles:
                raise ConsultingEvidenceError("Global gate lacks the reviewed role label")
            checked_at = parse_timestamp(item.get("checked_at"))
            if item.get("private_evidence_recorded") is not True or checked_at is None:
                raise ConsultingEvidenceError("Verified gate lacks a dated private-evidence attestation")
            if any(checked_at < gate_times[dependency] for dependency in dependencies):
                raise ConsultingEvidenceError("Global gate predates a required dependency")
            if item.get("notes") != VERIFIED_NOTE:
                raise ConsultingEvidenceError("Verified gate must use the fixed public note")
            gate_times[gate_id] = checked_at
        else:
            raise ConsultingEvidenceError("Unknown global gate status")
        statuses[gate_id] = status

    completed = value.get("p004_global_requirements_complete")
    if not isinstance(completed, bool):
        raise ConsultingEvidenceError("p004_global_requirements_complete must be boolean")
    approved_at_value = value.get("owner_global_approved_at")
    if completed:
        if any(status != "verified" for status in statuses.values()):
            raise ConsultingEvidenceError("Global requirements cannot be complete while a gate is pending")
        approved_at = parse_timestamp(approved_at_value)
        if approved_at is None:
            raise ConsultingEvidenceError("Completed global requirements need a current owner approval timestamp")
        if approved_at < max(gate_times.values()):
            raise ConsultingEvidenceError("Owner approval timestamp cannot predate the final gate")
    elif approved_at_value is not None:
        raise ConsultingEvidenceError("Incomplete global requirements cannot contain an approval timestamp")

    for key in PERMANENT_FALSE_FIELDS:
        if value.get(key) is not False:
            raise ConsultingEvidenceError(f"P027 cannot set {key}")
    return {"p004_global_requirements_complete": completed, "statuses": statuses}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--path", type=Path, default=DEFAULT_EVIDENCE)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = validate_evidence(args.path)
    except ConsultingEvidenceError as exc:
        print(f"SpaceGhostKilla consulting evidence validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
