#!/usr/bin/env python3
"""Validate Pawsfect recruiting sources and non-sensitive readiness evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / ".github/portfolio/pawsfect-recruiting"
DEFAULT_SOURCES = PACKET / "official_sources.json"
DEFAULT_EVIDENCE = PACKET / "P015_RECRUITING_EVIDENCE_TEMPLATE.json"
HELD_DOMAINS = {
    "sxswasted.com", "austinfcsoccer.com", "austinfcsoccer.net",
    "austinfcjerseys.com", "atxsoccerjerseys.com",
}
EXPECTED_SOURCES = [
    {
        "id": "twc-worker-classification",
        "url": "https://www.twc.texas.gov/programs/unemployment-tax/classifying-employees-independent-contractors",
        "purpose": "Texas worker-classification starting point; not a project-specific classification decision.",
    },
    {
        "id": "irs-worker-classification",
        "url": "https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee",
        "purpose": "Federal tax classification and control-factor starting point; document the complete actual relationship.",
    },
    {
        "id": "ftc-employer-background-checks",
        "url": "https://www.ftc.gov/business-guidance/resources/background-checks-what-employers-need-know",
        "purpose": "FCRA disclosure, authorization and notice starting point when a reporting company is used.",
    },
    {
        "id": "eeoc-employer-background-checks",
        "url": "https://www.eeoc.gov/laws/guidance/background-checks-what-employers-need-know",
        "purpose": "Equal-treatment and nondiscrimination starting point for background information and employment decisions.",
    },
]
EXPECTED_PILOT = {
    "target_walkers": "2-3",
    "included_services": ["individual household dog walks", "simple drop-ins"],
    "excluded_services": [
        "routine dog transportation", "boarding", "group or off-leash walks",
        "medication administration",
    ],
}
GATES = [
    ("pilot_role_scope", {"owner_operations_reviewer"}, []),
    ("classification_model_review", {"owner_with_qualified_classification_review"}, ["pilot_role_scope"]),
    ("pay_control_terms_reviewed", {"owner_with_qualified_employment_tax_review"}, ["pilot_role_scope", "classification_model_review"]),
    ("insurance_worker_coverage", {"owner_with_insurer_confirmation"}, ["classification_model_review", "pay_control_terms_reviewed"]),
    ("screening_consent_process", {"owner_with_qualified_employment_review"}, ["classification_model_review", "pay_control_terms_reviewed"]),
    ("private_candidate_data_controls", {"owner_security_reviewer"}, ["screening_consent_process"]),
    ("structured_interview_process", {"owner_operations_reviewer"}, ["pilot_role_scope", "screening_consent_process", "private_candidate_data_controls"]),
    ("recruiting_authorization", {"owner"}, [
        "pilot_role_scope", "classification_model_review", "pay_control_terms_reviewed",
        "insurance_worker_coverage", "screening_consent_process",
        "private_candidate_data_controls", "structured_interview_process",
    ]),
]
PENDING_NOTES = {
    "pilot_role_scope": "Pending owner confirmation of the proposed pilot duties, exclusions, pay and control facts.",
    "classification_model_review": "Pending qualified worker-classification review of the frozen facts; no classification is claimed.",
    "pay_control_terms_reviewed": "Pending approved pay, expenses, scheduling, control, training, recordkeeping and termination terms.",
    "insurance_worker_coverage": "Pending insurer confirmation for the actual worker model and approved duties; no coverage is claimed.",
    "screening_consent_process": "Pending qualified review of consistent screening, consent, notice, dispute, access and retention controls.",
    "private_candidate_data_controls": "Pending verification of restricted storage, access, authentication, retention, deletion and incident controls.",
    "structured_interview_process": "Pending owner approval of structured interviews, decision rules and interviewer guidance.",
    "recruiting_authorization": "Pending owner authorization; no posting, outreach, screening, interview or offer is approved.",
}
VERIFIED_NOTE = "Gate verified; supporting details remain in the private owner review record."
GATE_FIELDS = {
    "id", "status", "checked_at", "reviewer_role", "private_evidence_recorded", "notes",
}
ROOT_FIELDS = {
    "version", "project", "source_repository", "owner_attested_packet_sha",
    "role_policy_version", "recruiting_approved", "hire_authorized",
    "dispatch_authorized", "paid_care_launch_ready", "owner_approval_date",
    "pilot", "gates",
}
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b\d{1,6}\s+[A-Za-z0-9.' -]+\s(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|boulevard|blvd)\b", re.I),
    re.compile(r"\b(?:candidate|applicant|worker|reference)[-_ ]?(?:name|id|score|decision|result)\s*[:=]", re.I),
    re.compile(r"\b(?:date of birth|dob|driver'?s? license|passport|background result|criminal record|motor vehicle record)\s*[:=]", re.I),
    re.compile(r"\b(?:password|secret|api[_ -]?key|bank|routing|tax id|door code)\s*[:=]", re.I),
)


class RecruitingError(ValueError):
    """A recruiting-readiness boundary failed."""


def reject_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def read_json(path: Path) -> object:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > 65_536:
            raise RecruitingError(f"Unsafe JSON file: {path}")
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except RecruitingError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RecruitingError(f"Cannot read JSON: {path}") from exc


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


def validate_sources(path: Path = DEFAULT_SOURCES) -> dict:
    value = read_json(path)
    expected = {"version": 1, "checked_on": "2026-10-15", "sources": EXPECTED_SOURCES}
    if value != expected:
        raise RecruitingError("Official-source register does not match the reviewed sources")
    for source in value["sources"]:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise RecruitingError("Official-source URL is not safe HTTPS")
    return {"sources": len(value["sources"]), "status": "reviewed_starting_points"}


def validate_evidence(path: Path = DEFAULT_EVIDENCE) -> dict:
    value = read_json(path)
    if not isinstance(value, dict) or set(value) != ROOT_FIELDS:
        raise RecruitingError("Evidence root does not match the reviewed schema")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise RecruitingError("Evidence version must be integer 1")
    if (
        value.get("project") != "Pawsfect Walks pilot recruiting"
        or value.get("source_repository") != "jordanistan/illnetwork"
        or value.get("pilot") != EXPECTED_PILOT
    ):
        raise RecruitingError("Evidence project or pilot boundary is invalid")
    if has_sensitive_or_held_text(value):
        raise RecruitingError("Evidence contains sensitive-looking data or a held domain")

    gates = value.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise RecruitingError("Evidence must contain every recruiting gate exactly once")
    statuses: dict[str, str] = {}
    gate_times: dict[str, datetime] = {}
    for item, (gate_id, roles, dependencies) in zip(gates, GATES):
        if not isinstance(item, dict) or set(item) != GATE_FIELDS or item.get("id") != gate_id:
            raise RecruitingError("Recruiting gate identity, order or fields are invalid")
        status = item.get("status")
        if status == "pending":
            if (
                item.get("checked_at") != "" or item.get("reviewer_role") != ""
                or item.get("private_evidence_recorded") is not False
                or item.get("notes") != PENDING_NOTES[gate_id]
            ):
                raise RecruitingError("Pending gate cannot contain review claims")
        elif status == "verified":
            if any(statuses.get(dependency) != "verified" for dependency in dependencies):
                raise RecruitingError("Recruiting gates must be verified in dependency order")
            if item.get("reviewer_role") not in roles:
                raise RecruitingError("Recruiting gate lacks the reviewed role")
            checked_at = parse_timestamp(item.get("checked_at"))
            if item.get("private_evidence_recorded") is not True or checked_at is None:
                raise RecruitingError("Verified gate lacks dated private evidence")
            if any(checked_at < gate_times[dependency] for dependency in dependencies):
                raise RecruitingError("Recruiting gate predates a required dependency")
            if item.get("notes") != VERIFIED_NOTE:
                raise RecruitingError("Verified gate must use the fixed public note")
            gate_times[gate_id] = checked_at
        else:
            raise RecruitingError("Unknown recruiting gate status")
        statuses[gate_id] = status

    packet_sha = value.get("owner_attested_packet_sha")
    scope_verified = statuses["pilot_role_scope"] == "verified"
    if scope_verified:
        if not re.fullmatch(r"[0-9a-f]{40}", str(packet_sha)):
            raise RecruitingError("Verified pilot scope requires the frozen packet commit SHA")
    elif packet_sha != "":
        raise RecruitingError("Pending pilot scope cannot claim a packet commit SHA")

    role_policy = value.get("role_policy_version")
    role_verified = statuses["pay_control_terms_reviewed"] == "verified"
    if role_verified:
        if not re.fullmatch(r"pawsfect-role-v[1-9][0-9]*", str(role_policy)):
            raise RecruitingError("Verified role scope requires a fixed policy version")
    elif role_policy != "":
        raise RecruitingError("Pending role scope cannot claim a policy version")

    approved = value.get("recruiting_approved")
    if not isinstance(approved, bool):
        raise RecruitingError("recruiting_approved must be boolean")
    for key in ("hire_authorized", "dispatch_authorized", "paid_care_launch_ready"):
        if value.get(key) is not False:
            raise RecruitingError(f"P015 cannot set {key}")
    approval_date = value.get("owner_approval_date")
    if not approved:
        if approval_date is not None:
            raise RecruitingError("Unapproved recruiting cannot contain completion claims")
    else:
        if any(status != "verified" for status in statuses.values()):
            raise RecruitingError("Recruiting cannot be approved while a gate is pending")
        try:
            parsed_date = datetime.strptime(str(approval_date), "%Y-%m-%d").date()
        except ValueError as exc:
            raise RecruitingError("Approved recruiting requires an owner approval date") from exc
        if parsed_date > datetime.now(timezone.utc).date():
            raise RecruitingError("Owner approval date cannot be in the future")
        if parsed_date < max(gate_times.values()).date():
            raise RecruitingError("Owner approval date cannot predate the final gate")
    return {
        "recruiting_approved": approved,
        "statuses": statuses,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    sources = sub.add_parser("sources")
    sources.add_argument("--path", type=Path, default=DEFAULT_SOURCES)
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--path", type=Path, default=DEFAULT_EVIDENCE)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = validate_sources(args.path) if args.command == "sources" else validate_evidence(args.path)
    except RecruitingError as exc:
        print(f"Pawsfect recruiting validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
