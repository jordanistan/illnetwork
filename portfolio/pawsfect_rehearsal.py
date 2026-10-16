#!/usr/bin/env python3
"""Create, review and verify a synthetic-only Pawsfect launch rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


MAX_JSON_BYTES = 65_536
PROJECT = "Pawsfect Walks offline synthetic rehearsal"
SOURCE_PATH = "docs/launch/09_Launch_Test_and_Agent_Handoff.md"
SOURCE_BLOB_SHA = "b62e010eedbc42f7d110ff3e903efae15a670e76"
PREREQUISITES = (
    "p003_insurance_coverage",
    "p003_service_area_capacity",
    "p003_intake_meet_greet",
    "p003_handling_transport",
    "p003_service_agreement",
    "p003_cancellation_refunds",
    "p003_payment_booking",
    "p015_recruiting_authorization",
)
NOT_EVALUATED = "not_evaluated_by_p016"
SCENARIO_REGISTRY = (
    ("p016-s01-qualified-inquiry", {"controlled-inquiry": "hold_for_human_fit_review"}),
    ("p016-s02-outside-area-no-capacity", {
        "outside-zone": "decline_or_waitlist_without_charge",
        "capacity-full": "decline_or_waitlist_without_charge",
    }),
    ("p016-s03-meet-greet-safety-fail", {"unsafe-fit": "decline_care_without_charge"}),
    ("p016-s04-ready-client", {"all-ready": "hold_for_human_booking_confirmation"}),
    ("p016-s05-payment-failed-pending", {
        "failed-payment": "keep_visit_unconfirmed",
        "pending-payment": "keep_visit_unconfirmed",
    }),
    ("p016-s06-worker-unavailable", {
        "ready-backup": "hold_backup_for_human_confirmation",
        "no-ready-backup": "notify_and_record_full_refund_due",
    }),
    ("p016-s07-unsafe-weather-no-access", {
        "unsafe-weather": "use_preapproved_safe_alternative_or_stop_and_record_full_refund_due",
        "no-access": "stop_without_forced_entry_and_apply_policy",
    }),
    ("p016-s08-injury-escape", {
        "injury": "contain_contact_escalate_and_keep_report_private",
        "escape": "contain_contact_escalate_and_keep_report_private",
    }),
    ("p016-s09-late-cancellation-refund-failure", {
        "late-cancellation": "apply_signed_policy_for_human_review",
        "refund-failure": "escalate_refund_failure_for_reconciliation",
    }),
    ("p016-s10-complete-visit", {"completed-visit": "record_synthetic_completion_and_reconcile"}),
    ("p016-s11-client-worker-offboarding", {
        "client-offboarding": "revoke_synthetic_access_and_permissions",
        "worker-offboarding": "revoke_synthetic_access_and_permissions",
    }),
)
REQUEST_FIELDS = (
    "version", "project", "request_id", "data_classification", "offline_only",
    "live_execution_authorized", "source_path", "source_blob_sha",
    "prerequisites", "scenarios",
)
REPORT_FIELDS = (
    "version", "project", "request_id", "source_path", "source_blob_sha",
    "request_file_sha256", "normalized_request_sha256", "status", "offline_only",
    "scenario_results", "capabilities", "authorizations",
)
CAPABILITIES = {
    "synthetic_data_only": True,
    "real_readiness_evaluated": False,
    "insurance_verified": False,
    "recruiting_authorized": False,
    "customer_data_used": False,
    "worker_data_used": False,
    "network_used": False,
}
AUTHORIZATIONS = {
    "launch_authorized": False,
    "booking_authorized": False,
    "dispatch_authorized": False,
    "payment_authorized": False,
    "refund_executed": False,
    "external_actions_authorized": False,
}
REVIEW_DECISIONS = {"accept_offline_result", "reject_offline_result"}
ACCEPT_REASON = "synthetic_controls_match"
REJECT_REASONS = {
    "synthetic_control_mismatch", "fixture_needs_revision",
    "prerequisites_require_owner_work",
}
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
HELD_DOMAINS = {
    "sxswasted.com", "austinfcsoccer.com", "austinfcsoccer.net",
    "austinfcjerseys.com", "atxsoccerjerseys.com",
}
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b\d{1,6}\s+[A-Za-z0-9.' -]+\s(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|boulevard|blvd)\b", re.I),
    re.compile(r"\b(?:password|secret|api[_ -]?key|token|door code|access code|bank|routing|tax id|driver'?s? license|date of birth|dob)\s*[:=]", re.I),
)


class RehearsalError(ValueError):
    """A rehearsal safety or integrity boundary failed."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                raise RehearsalError(f"Symlink path components are not accepted: {path}")
        except OSError as exc:
            raise RehearsalError(f"Cannot inspect path safely: {path}") from exc


def _validate_path_syntax(path: Path) -> None:
    if ".." in path.parts:
        raise RehearsalError(f"Parent traversal is not accepted: {path}")


def read_json_document(path: Path) -> tuple[dict, bytes]:
    path = Path(path)
    _validate_path_syntax(path)
    _reject_symlink_components(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = None
    try:
        descriptor = os.open(path, flags)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise RehearsalError(f"JSON input must be a regular file: {path}")
        if info.st_size > MAX_JSON_BYTES:
            raise RehearsalError(f"JSON input exceeds {MAX_JSON_BYTES} bytes: {path}")
        chunks = []
        remaining = MAX_JSON_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_JSON_BYTES:
            raise RehearsalError(f"JSON input exceeds {MAX_JSON_BYTES} bytes: {path}")
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except RehearsalError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise RehearsalError(f"Cannot read strict UTF-8 JSON: {path}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise RehearsalError("JSON root must be an object")
    return value, raw


def read_json(path: Path) -> dict:
    return read_json_document(path)[0]


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: object) -> str:
    return sha256_bytes(canonical_json(value))


def _contains_sensitive_or_held(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=True)
    lowered = text.lower()
    return any(domain in lowered for domain in HELD_DOMAINS) or any(
        pattern.search(text) for pattern in SENSITIVE_PATTERNS
    )


def _exact_fields(value: dict, fields: tuple[str, ...], label: str) -> None:
    if type(value) is not dict or tuple(value) != fields:
        raise RehearsalError(f"{label} fields and order must match the reviewed schema")


def _fixed_false_mapping(value: object, expected: dict, label: str) -> None:
    if type(value) is not dict or tuple(value) != tuple(expected):
        raise RehearsalError(f"{label} fields and order are invalid")
    for key, expected_value in expected.items():
        if value[key] is not expected_value:
            raise RehearsalError(f"{label}.{key} must be {str(expected_value).lower()}")


def validate_request(value: dict) -> dict:
    if _contains_sensitive_or_held(value):
        raise RehearsalError("Request contains sensitive-looking data or a held domain")
    _exact_fields(value, REQUEST_FIELDS, "Request")
    if type(value["version"]) is not int or value["version"] != 1:
        raise RehearsalError("version must be integer 1")
    if value["project"] != PROJECT:
        raise RehearsalError("project is invalid")
    if type(value["request_id"]) is not str or not ID_PATTERN.fullmatch(value["request_id"]):
        raise RehearsalError("request_id must be a short lowercase synthetic identifier")
    if value["data_classification"] != "synthetic":
        raise RehearsalError("Only synthetic data is accepted")
    if value["offline_only"] is not True or value["live_execution_authorized"] is not False:
        raise RehearsalError("Request must remain offline and unauthorised for live execution")
    if value["source_path"] != SOURCE_PATH or value["source_blob_sha"] != SOURCE_BLOB_SHA:
        raise RehearsalError("Source path and blob must match the frozen reviewed source")
    prerequisites = value["prerequisites"]
    if type(prerequisites) is not list or len(prerequisites) != len(PREREQUISITES):
        raise RehearsalError("Prerequisites must contain the fixed ordered set")
    for item, prerequisite_id in zip(prerequisites, PREREQUISITES):
        if type(item) is not dict or tuple(item) != ("id", "status"):
            raise RehearsalError("Prerequisite fields and order are invalid")
        if item["id"] != prerequisite_id or item["status"] != NOT_EVALUATED:
            raise RehearsalError("P016 does not evaluate or verify real prerequisites")
    scenarios = value["scenarios"]
    if type(scenarios) is not list or len(scenarios) != len(SCENARIO_REGISTRY):
        raise RehearsalError("Scenarios must contain the fixed ordered set")
    normalized_scenarios = []
    for item, (scenario_id, variants) in zip(scenarios, SCENARIO_REGISTRY):
        if type(item) is not dict or tuple(item) != ("id", "variant", "observed_control"):
            raise RehearsalError("Scenario fields and order are invalid")
        variant = item["variant"]
        control = item["observed_control"]
        if item["id"] != scenario_id or type(variant) is not str or variant not in variants:
            raise RehearsalError("Scenario identity or variant is invalid")
        if type(control) is not str or control not in set(variants.values()):
            raise RehearsalError("Observed control is outside the reviewed enum")
        normalized_scenarios.append({"id": scenario_id, "variant": variant, "observed_control": control})
    return {
        "version": 1,
        "project": PROJECT,
        "request_id": value["request_id"],
        "data_classification": "synthetic",
        "offline_only": True,
        "live_execution_authorized": False,
        "source_path": SOURCE_PATH,
        "source_blob_sha": SOURCE_BLOB_SHA,
        "prerequisites": [{"id": item, "status": NOT_EVALUATED} for item in PREREQUISITES],
        "scenarios": normalized_scenarios,
    }


def expected_report(request: dict, raw_request_sha256: str) -> dict:
    request = validate_request(request)
    results = []
    for item, (scenario_id, variants) in zip(request["scenarios"], SCENARIO_REGISTRY):
        expected_control = variants[item["variant"]]
        results.append({
            "id": scenario_id,
            "variant": item["variant"],
            "expected_control": expected_control,
            "observed_control": item["observed_control"],
            "comparison": (
                "matches_expected_synthetic_branch"
                if item["observed_control"] == expected_control
                else "needs_offline_review"
            ),
        })
    return {
        "version": 1,
        "project": PROJECT,
        "request_id": request["request_id"],
        "source_path": SOURCE_PATH,
        "source_blob_sha": SOURCE_BLOB_SHA,
        "request_file_sha256": raw_request_sha256,
        "normalized_request_sha256": digest(request),
        "status": "offline_result_generated",
        "offline_only": True,
        "scenario_results": results,
        "capabilities": dict(CAPABILITIES),
        "authorizations": dict(AUTHORIZATIONS),
    }


def validate_report(value: dict, request: dict, raw_request_sha256: str) -> dict:
    _exact_fields(value, REPORT_FIELDS, "Report")
    expected = expected_report(request, raw_request_sha256)
    if value != expected:
        raise RehearsalError("Report does not exactly match the request and reviewed controls")
    _fixed_false_mapping(value["capabilities"], CAPABILITIES, "capabilities")
    _fixed_false_mapping(value["authorizations"], AUTHORIZATIONS, "authorizations")
    return value


def expected_review(request: dict, report: dict, decision: str, reason: str) -> dict:
    if decision not in REVIEW_DECISIONS:
        raise RehearsalError("Review decision is invalid")
    comparisons_match = all(
        item["comparison"] == "matches_expected_synthetic_branch"
        for item in report["scenario_results"]
    )
    if decision == "accept_offline_result":
        if reason != ACCEPT_REASON or not comparisons_match:
            raise RehearsalError("Only a matching synthetic result may use the accept decision")
    elif reason not in REJECT_REASONS:
        raise RehearsalError("Reject reason is invalid")
    return {
        "version": 1,
        "project": PROJECT,
        "request_id": request["request_id"],
        "reviewer_role": "synthetic-reviewer",
        "decision": decision,
        "reason": reason,
        "status": "reviewed_offline_only",
        "offline_only": True,
        "request_file_sha256": report["request_file_sha256"],
        "normalized_request_sha256": report["normalized_request_sha256"],
        "report_sha256": digest(report),
        "authorizations": dict(AUTHORIZATIONS),
    }


def validate_review(value: dict, request: dict, report: dict) -> dict:
    fields = (
        "version", "project", "request_id", "reviewer_role", "decision", "reason",
        "status", "offline_only", "request_file_sha256",
        "normalized_request_sha256", "report_sha256", "authorizations",
    )
    _exact_fields(value, fields, "Review")
    expected = expected_review(request, report, value["decision"], value["reason"])
    if value != expected:
        raise RehearsalError("Review does not exactly bind to the request and report")
    _fixed_false_mapping(value["authorizations"], AUTHORIZATIONS, "authorizations")
    return value


def _write_new_json(path: Path, value: dict) -> None:
    path = Path(path)
    _validate_path_syntax(path)
    _reject_symlink_components(path)
    if path.name.startswith(".") or path.suffix != ".json":
        raise RehearsalError("Output must be a visible .json file")
    if not path.parent.is_dir():
        raise RehearsalError("Output parent must already be a directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = None
    created = False
    try:
        descriptor = os.open(path, flags, 0o600)
        created = True
        payload = json.dumps(value, ensure_ascii=True, indent=2) + "\n"
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise RehearsalError(f"Refusing to overwrite output: {path}") from exc
    except (OSError, UnicodeError) as exc:
        if created:
            try:
                path.unlink()
            except OSError:
                pass
        raise RehearsalError(f"Cannot safely create output: {path}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def run(request_path: Path, report_path: Path) -> dict:
    request, raw = read_json_document(request_path)
    report = expected_report(request, sha256_bytes(raw))
    _write_new_json(report_path, report)
    return report


def record_review(request_path: Path, report_path: Path, review_path: Path, decision: str, reason: str) -> dict:
    request, raw = read_json_document(request_path)
    request = validate_request(request)
    report = read_json(report_path)
    validate_report(report, request, sha256_bytes(raw))
    review = expected_review(request, report, decision, reason)
    _write_new_json(review_path, review)
    return review


def verify(request_path: Path, report_path: Path, review_path: Path) -> dict:
    request, raw = read_json_document(request_path)
    request = validate_request(request)
    report = read_json(report_path)
    validate_report(report, request, sha256_bytes(raw))
    review = read_json(review_path)
    validate_review(review, request, report)
    return review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("request", type=Path)
    run_parser.add_argument("report", type=Path)
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("request", type=Path)
    review_parser.add_argument("report", type=Path)
    review_parser.add_argument("review", type=Path)
    review_parser.add_argument("--decision", required=True, choices=sorted(REVIEW_DECISIONS))
    review_parser.add_argument("--reason", required=True, choices=sorted({ACCEPT_REASON} | REJECT_REASONS))
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("request", type=Path)
    verify_parser.add_argument("report", type=Path)
    verify_parser.add_argument("review", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "run":
            run(args.request, args.report)
        elif args.command == "review":
            record_review(args.request, args.report, args.review, args.decision, args.reason)
        else:
            verify(args.request, args.report, args.review)
    except RehearsalError as exc:
        print(f"pawsfect-rehearsal: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
