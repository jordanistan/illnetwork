#!/usr/bin/env python3
"""Validate health-review sources, current content and non-sensitive evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / ".github/portfolio/health"
DEFAULT_SOURCES = PACKET / "official_sources.json"
DEFAULT_EVIDENCE = PACKET / "P012_REVIEW_EVIDENCE_TEMPLATE.json"
DEFAULT_SITES = ROOT / "portfolio/sites.json"
EXPECTED_SOURCES = [
    {
        "id": "ftc-health-products-compliance",
        "url": "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance",
        "purpose": "Official guidance on express and implied health claims, net impression and substantiation; not an approval of this content.",
    },
    {
        "id": "fda-general-wellness",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices",
        "purpose": "Official general-wellness starting point; changed functions or intended uses require project-specific review.",
    },
    {
        "id": "hhs-health-literacy-online",
        "url": "https://odphp.health.gov/healthliteracyonline/",
        "purpose": "Official people-first, understandable, accessible content and governance guidance.",
    },
    {
        "id": "hhs-hipaa-privacy-rule",
        "url": "https://www.hhs.gov/hipaa/for-professionals/privacy/index.html",
        "purpose": "Official Privacy Rule scope reference; does not establish covered-entity status or authorize health-data collection.",
    },
]
HEALTH_DOMAINS = ("hearty.fit", "healthyheart.clinic")
MODES = ("preview", "production")
ARTIFACT_FIELDS = {"domain", "mode", "sha256"}
EXPECTED_ARTIFACT_FILES = {
    ".nojekyll", "_headers", "index.html", "privacy.html", "robots.txt", "sitemap.xml",
    "assets/favicon.svg", "assets/hero.svg", "assets/site.css", "assets/site.js",
}
EXPECTED_ARTIFACT_DIRS = {"assets"}
GATES = [
    ("content_inventory", {"owner_editorial"}, []),
    ("healthyheart_qualified_review", {"qualified_licensed_health_content_reviewer"}, ["content_inventory"]),
    ("hearty_qualified_review", {"qualified_licensed_health_content_reviewer"}, ["content_inventory"]),
    (
        "claims_net_impression",
        {"qualified_licensed_health_content_reviewer"},
        ["healthyheart_qualified_review", "hearty_qualified_review"],
    ),
    ("data_flow_review", {"owner_technical_reviewer"}, ["content_inventory"]),
    ("owner_publication", {"owner"}, ["claims_net_impression", "data_flow_review"]),
]
PENDING_NOTES = {
    "content_inventory": "Pending exact two-site content inventory.",
    "healthyheart_qualified_review": "Pending qualified review; no clinical-content approval is claimed.",
    "hearty_qualified_review": "Pending qualified review; no health-outcome approval is claimed.",
    "claims_net_impression": "Pending express, implied and whole-impression claims review.",
    "data_flow_review": "Pending verification of no site-operated health-data capture, storage, upload, intake, appointment or analytics path; production email remains user initiated.",
    "owner_publication": "Pending owner approval of the exact reviewed educational content.",
}
VERIFIED_NOTE = "Gate verified; supporting details remain in the private owner review record."
GATE_FIELDS = {
    "id", "status", "checked_at", "reviewer_role", "private_evidence_recorded", "notes"
}
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\b(?:patient|member|medical record|mrn|date of birth|dob)[-_ :#]+[A-Za-z0-9/-]{3,}\b", re.I),
    re.compile(r"\b(?:password|secret|api[_ -]?key|license number|npi)\s*[:=]", re.I),
)


class ReviewError(ValueError):
    """A health-review boundary failed."""


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
            raise ReviewError(f"Unsafe JSON file: {path}")
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except ReviewError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReviewError(f"Cannot read JSON: {path}") from exc


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


def has_sensitive_text(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=True)
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def health_content(path: Path = DEFAULT_SITES) -> list[dict]:
    value = read_json(path)
    if not isinstance(value, dict) or not isinstance(value.get("sites"), list):
        raise ReviewError("Sites catalog must contain a sites list")
    matches = [item for item in value["sites"] if isinstance(item, dict) and item.get("domain") in HEALTH_DOMAINS]
    by_domain = {item["domain"]: item for item in matches}
    if len(matches) != len(HEALTH_DOMAINS) or set(by_domain) != set(HEALTH_DOMAINS):
        raise ReviewError("Sites catalog must contain each health domain exactly once")
    return [by_domain[domain] for domain in HEALTH_DOMAINS]


def tree_digest(path: Path) -> str:
    files = []
    for item in path.rglob("*"):
        info = item.lstat()
        relative = item.relative_to(path).as_posix()
        if stat.S_ISLNK(info.st_mode):
            raise ReviewError("Generated artifact contains a symlink")
        if stat.S_ISDIR(info.st_mode):
            if relative not in EXPECTED_ARTIFACT_DIRS:
                raise ReviewError("Generated artifact contains an unexpected directory")
        elif stat.S_ISREG(info.st_mode):
            files.append(item)
        else:
            raise ReviewError("Generated artifact contains a special filesystem entry")
    relative = {item.relative_to(path).as_posix() for item in files}
    if relative != EXPECTED_ARTIFACT_FILES:
        raise ReviewError("Generated artifact file set is not approved")
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda value: value.relative_to(path).as_posix()):
        name = item.relative_to(path).as_posix().encode("utf-8")
        content = item.read_bytes()
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def build_artifact_records() -> list[dict]:
    records = []
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for domain in HEALTH_DOMAINS:
            for mode in MODES:
                output = base / f"{domain}-{mode}"
                build = subprocess.run(
                    [sys.executable, str(ROOT / "portfolio/build.py"), "--mode", mode,
                     "--domain", domain, "--output", str(output)],
                    cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
                )
                if build.returncode:
                    raise ReviewError("Health artifact build failed")
                check = subprocess.run(
                    [sys.executable, str(ROOT / "portfolio/check.py"), str(output), "--domain", domain],
                    cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
                )
                if check.returncode:
                    raise ReviewError("Health artifact check failed")
                records.append({"domain": domain, "mode": mode, "sha256": tree_digest(output)})
    return records


def validate_sources(path: Path = DEFAULT_SOURCES) -> dict:
    value = read_json(path)
    expected = {"version": 1, "checked_on": "2026-10-14", "sources": EXPECTED_SOURCES}
    if not isinstance(value, dict) or type(value.get("version")) is not int:
        raise ReviewError("Official-source register has an invalid version")
    if value != expected:
        raise ReviewError("Official-source register does not match the reviewed sources")
    for source in EXPECTED_SOURCES:
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ReviewError("Official-source URL is not safe HTTPS")
    return {"sources": len(EXPECTED_SOURCES), "status": "reviewed_starting_points"}


def validate_evidence(path: Path = DEFAULT_EVIDENCE, current_artifacts: list[dict] | None = None) -> dict:
    value = read_json(path)
    if not isinstance(value, dict):
        raise ReviewError("Evidence root must be an object")
    root_fields = {
        "version", "project", "source_repository", "publication_approved",
        "owner_approval_date", "owner_attested_reviewed_source_sha", "reviewed_artifacts", "gates",
    }
    if (
        set(value) != root_fields or type(value.get("version")) is not int
        or value.get("version") != 1 or value.get("project") != "Health education portfolio"
        or value.get("source_repository") != "jordanistan/illnetwork"
    ):
        raise ReviewError("Evidence root does not match the reviewed schema")
    if has_sensitive_text(value):
        raise ReviewError("Evidence contains sensitive-looking data")
    artifacts = value.get("reviewed_artifacts")
    expected_pairs = [(domain, mode) for domain in HEALTH_DOMAINS for mode in MODES]
    if not isinstance(artifacts, list) or len(artifacts) != len(expected_pairs):
        raise ReviewError("Evidence must contain the fixed artifact inventory")
    for item, (domain, mode) in zip(artifacts, expected_pairs):
        if (
            not isinstance(item, dict) or set(item) != ARTIFACT_FIELDS
            or item.get("domain") != domain or item.get("mode") != mode
            or not isinstance(item.get("sha256"), str)
        ):
            raise ReviewError("Artifact identity, order or fields are invalid")
    gates = value.get("gates")
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise ReviewError("Evidence must contain every review gate exactly once")
    statuses: dict[str, str] = {}
    gate_times: dict[str, datetime] = {}
    for item, (gate_id, roles, dependencies) in zip(gates, GATES):
        if not isinstance(item, dict) or set(item) != GATE_FIELDS or item.get("id") != gate_id:
            raise ReviewError("Review gate identity, order or fields are invalid")
        status = item.get("status")
        if status == "pending":
            if (
                item.get("checked_at") != "" or item.get("reviewer_role") != ""
                or item.get("private_evidence_recorded") is not False
                or item.get("notes") != PENDING_NOTES[gate_id]
            ):
                raise ReviewError("Pending gate cannot contain review claims")
        elif status == "verified":
            if any(statuses.get(dependency) != "verified" for dependency in dependencies):
                raise ReviewError("Review gates must be verified in dependency order")
            if item.get("reviewer_role") not in roles:
                raise ReviewError("Review gate lacks the reviewed role")
            checked_at = parse_timestamp(item.get("checked_at"))
            if item.get("private_evidence_recorded") is not True or checked_at is None:
                raise ReviewError("Verified gate lacks dated private evidence")
            if any(checked_at < gate_times[dependency] for dependency in dependencies):
                raise ReviewError("Review gate predates a required dependency")
            if item.get("notes") != VERIFIED_NOTE:
                raise ReviewError("Verified gate must use the fixed public note")
            gate_times[gate_id] = checked_at
        else:
            raise ReviewError("Unknown review gate status")
        statuses[gate_id] = status

    inventory_verified = statuses["content_inventory"] == "verified"
    source_sha = value.get("owner_attested_reviewed_source_sha")
    if inventory_verified:
        if not re.fullmatch(r"[0-9a-f]{40}", str(source_sha)):
            raise ReviewError("Verified inventory requires a full reviewed source SHA")
        actual_artifacts = current_artifacts if current_artifacts is not None else build_artifact_records()
        if artifacts != actual_artifacts:
            raise ReviewError("Reviewed artifact digests do not match the current health builds")
    elif source_sha != "" or any(item["sha256"] for item in artifacts):
        raise ReviewError("Pending inventory cannot contain source or artifact completion claims")

    approved = value.get("publication_approved")
    if not isinstance(approved, bool):
        raise ReviewError("publication_approved must be boolean")
    if not approved:
        if value.get("owner_approval_date") is not None:
            raise ReviewError("Unapproved publication cannot contain owner approval")
    else:
        if any(status != "verified" for status in statuses.values()):
            raise ReviewError("Publication cannot be approved while a gate is pending")
        try:
            approval_date = datetime.strptime(str(value.get("owner_approval_date")), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ReviewError("Approved publication requires an owner approval date") from exc
        if approval_date > datetime.now(timezone.utc).date():
            raise ReviewError("Owner approval date cannot be in the future")
        if approval_date < max(gate_times.values()).date():
            raise ReviewError("Owner approval date cannot predate the final gate")
    return {
        "publication_approved": approved,
        "statuses": statuses,
        "owner_attested_reviewed_source_sha": source_sha,
        "artifacts": artifacts if inventory_verified else (
            current_artifacts if current_artifacts is not None else build_artifact_records()
        ),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    sources = sub.add_parser("sources")
    sources.add_argument("--path", type=Path, default=DEFAULT_SOURCES)
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--path", type=Path, default=DEFAULT_EVIDENCE)
    content = sub.add_parser("content")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "sources":
            result = validate_sources(args.path)
        elif args.command == "evidence":
            result = validate_evidence(args.path)
        else:
            result = {"artifacts": build_artifact_records()}
    except ReviewError as exc:
        print(f"Health review validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
