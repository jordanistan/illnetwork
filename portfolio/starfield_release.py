#!/usr/bin/env python3
"""Validate Starfield's public release-gate sources and non-sensitive evidence state."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / ".github/portfolio/starfield"
DEFAULT_SOURCES = PACKET / "official_sources.json"
DEFAULT_EVIDENCE = PACKET / "P011_RELEASE_EVIDENCE_TEMPLATE.json"
HELD_DOMAINS = {
    "sxswasted.com", "austinfcsoccer.com", "austinfcsoccer.net",
    "austinfcjerseys.com", "atxsoccerjerseys.com",
}
EXPECTED_SOURCES = [
    {
        "id": "uspto-trademark-search",
        "url": "https://www.uspto.gov/trademarks/search",
        "purpose": "Search guidance only; a search result is not a clearance conclusion.",
    },
    {
        "id": "copyright-visual-arts",
        "url": "https://www.copyright.gov/registration/visual-arts/",
        "purpose": "Official visual-art registration information; ownership and licensing still require project-specific evidence.",
    },
    {
        "id": "ftc-mail-internet-order-rule",
        "url": "https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule",
        "purpose": "Official shipping-promise, delay-consent and refund rule reference.",
    },
    {
        "id": "texas-online-orders",
        "url": "https://comptroller.texas.gov/taxes/publications/94-171.php",
        "purpose": "Official Texas online-order sales-tax starting point; obtain qualified advice for the actual sales model.",
    },
]
GATES = [
    ("brand_clearance", {"qualified_trademark_reviewer"}, []),
    ("artwork_rights", {"owner_with_qualified_ip_review"}, ["brand_clearance"]),
    ("samples_quality", {"owner"}, ["artwork_rights"]),
    ("catalog", {"owner"}, ["samples_quality"]),
    ("fulfillment_shipping", {"owner_operations_reviewer"}, ["catalog"]),
    ("pricing_tax", {"owner_with_qualified_tax_review"}, ["catalog", "fulfillment_shipping"]),
    ("customer_terms", {"owner_with_qualified_legal_review"}, ["catalog", "fulfillment_shipping", "pricing_tax"]),
    ("commercial_hosting", {"owner_technical_reviewer"}, ["customer_terms"]),
    ("checkout", {"owner"}, ["commercial_hosting"]),
]
PENDING_NOTES = {
    "brand_clearance": "Pending qualified review; no clearance is claimed.",
    "artwork_rights": "Pending ownership and license inventory.",
    "samples_quality": "Pending physical sample and quality review.",
    "catalog": "Pending exact product and SKU approval.",
    "fulfillment_shipping": "Pending provider, packaging, delivery and rollback review.",
    "pricing_tax": "Pending landed-cost, pricing and tax review.",
    "customer_terms": "Pending terms, privacy, returns, refunds and support review.",
    "commercial_hosting": "Pending reviewed commercial staging and cutover evidence.",
    "checkout": "Pending owner-controlled end-to-end checkout and refund test.",
}
VERIFIED_NOTE = "Gate verified; supporting details remain in the private owner ledger."
GATE_FIELDS = {"id", "status", "checked_at", "reviewer_role", "evidence_recorded", "notes"}
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b(?:ORDER|CUSTOMER|CLIENT)[-_ ][A-Z0-9]{4,}\b"),
    re.compile(r"\b(?:password|secret|api[_ -]?key|door code|tax id)\s*[:=]", re.I),
)


class ReleaseError(ValueError):
    """A Starfield release boundary failed."""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ReleaseError("JSON root must be an object")
    return value


def has_sensitive_or_held_text(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=True)
    lowered = text.lower()
    return any(domain in lowered for domain in HELD_DOMAINS) or any(
        pattern.search(text) for pattern in SENSITIVE_PATTERNS
    )


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


def validate_sources(path: Path) -> dict:
    value = read_json(path)
    expected = {"version": 1, "checked_on": "2026-10-13", "sources": EXPECTED_SOURCES}
    if value != expected:
        raise ReleaseError("Official-source register does not match the reviewed sources")
    for source in value["sources"]:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ReleaseError("Official-source URL is not safe HTTPS")
    return {"sources": len(value["sources"]), "status": "reviewed_starting_points"}


def validate_evidence(path: Path) -> dict:
    value = read_json(path)
    root_fields = {
        "version", "project", "release_approved", "owner_approval_date",
        "catalog_version", "owner_attested_release_repository",
        "owner_attested_release_sha", "owner_attested_checkout_record", "gates",
    }
    if set(value) != root_fields or value.get("version") != 1 or value.get("project") != "Starfield Studio":
        raise ReleaseError("Evidence root does not match the reviewed schema")
    if has_sensitive_or_held_text(value):
        raise ReleaseError("Evidence contains sensitive-looking data or a held domain")
    gates = value.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise ReleaseError("Evidence must contain every release gate exactly once")
    statuses: dict[str, str] = {}
    gate_times: dict[str, datetime] = {}
    for item, (gate_id, roles, dependencies) in zip(gates, GATES):
        if not isinstance(item, dict) or set(item) != GATE_FIELDS or item.get("id") != gate_id:
            raise ReleaseError("Release gate identity, order or fields are invalid")
        status = item.get("status")
        notes = item.get("notes")
        if status == "pending":
            if (
                item.get("checked_at") != "" or item.get("reviewer_role") != ""
                or item.get("evidence_recorded") is not False
            ):
                raise ReleaseError("Pending gate cannot contain verification claims")
            if notes != PENDING_NOTES[gate_id]:
                raise ReleaseError("Pending gate must use its fixed public note")
        elif status == "verified":
            if any(statuses.get(dependency) != "verified" for dependency in dependencies):
                raise ReleaseError("Release gates must be verified in dependency order")
            if item.get("reviewer_role") not in roles:
                raise ReleaseError("Release gate lacks the reviewed role")
            checked_at = parse_timestamp(item.get("checked_at"))
            if item.get("evidence_recorded") is not True or checked_at is None:
                raise ReleaseError("Verified gate lacks dated private evidence")
            if any(checked_at < gate_times[dependency] for dependency in dependencies):
                raise ReleaseError("Release gate predates a required dependency")
            if notes != VERIFIED_NOTE:
                raise ReleaseError("Verified gate must use the fixed public note")
            gate_times[gate_id] = checked_at
        else:
            raise ReleaseError("Unknown release gate status")
        statuses[gate_id] = status
    approved = value.get("release_approved")
    if not isinstance(approved, bool):
        raise ReleaseError("release_approved must be boolean")
    completion_fields = (
        value.get("owner_approval_date"), value.get("catalog_version"),
        value.get("owner_attested_release_repository"),
        value.get("owner_attested_release_sha"), value.get("owner_attested_checkout_record"),
    )
    if not approved:
        if value.get("owner_approval_date") is not None or any(completion_fields[1:]):
            raise ReleaseError("Unapproved release cannot contain completion claims")
    else:
        if any(status != "verified" for status in statuses.values()):
            raise ReleaseError("Release cannot be approved while a gate is pending")
        try:
            approval_date = datetime.strptime(str(value.get("owner_approval_date")), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ReleaseError("Approved release requires an owner approval date") from exc
        if approval_date > datetime.now(timezone.utc).date():
            raise ReleaseError("Owner approval date cannot be in the future")
        if approval_date < max(gate_times.values()).date():
            raise ReleaseError("Owner approval date cannot predate the final gate")
        if not re.fullmatch(r"catalog-v[1-9][0-9]*", str(value.get("catalog_version"))):
            raise ReleaseError("Approved release requires a fixed catalog version")
        if value.get("owner_attested_release_repository") != "jordanistan/starfieldstudio":
            raise ReleaseError("Approved release requires the fixed native repository attestation")
        if not re.fullmatch(r"[0-9a-f]{40}", str(value.get("owner_attested_release_sha"))):
            raise ReleaseError("Approved release requires an owner-attested full commit SHA")
        if not re.fullmatch(r"private-ledger:[A-Z0-9][A-Z0-9-]{5,63}", str(value.get("owner_attested_checkout_record"))):
            raise ReleaseError("Approved release requires an owner-attested private-ledger marker")
    return {"release_approved": approved, "statuses": statuses}


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
    except ReleaseError as exc:
        print(f"Starfield release validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
