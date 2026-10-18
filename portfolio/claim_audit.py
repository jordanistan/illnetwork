#!/usr/bin/env python3
"""Audit portfolio task leases without creating, moving, or deleting Git refs."""

import argparse
import json
import re
import sys
from pathlib import Path


TASK_RE = re.compile(r"P[0-9]{3}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
CLAIM_REF_RE = re.compile(r"refs/heads/claims/(P[0-9]{3})")
STATUSES = {"active", "retain_owner_blocked", "release_ready", "released"}
ENTRY_KEYS = {"task", "status", "expected_sha", "issue", "reason"}
ROOT_KEYS = {"schema_version", "repository", "claims"}


class ClaimAuditError(ValueError):
    """A claim ledger or remote-ref snapshot is unsafe or inconsistent."""


def load_ledger(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClaimAuditError(f"Cannot read claim ledger: {path}") from exc
    if not isinstance(value, dict) or set(value) != ROOT_KEYS:
        raise ClaimAuditError("Claim ledger root fields are invalid")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ClaimAuditError("Unsupported claim ledger schema")
    if value["repository"] != "jordanistan/illnetwork":
        raise ClaimAuditError("Claim ledger repository is invalid")
    if not isinstance(value["claims"], list) or not value["claims"]:
        raise ClaimAuditError("Claim ledger must contain entries")

    claims = {}
    for entry in value["claims"]:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise ClaimAuditError("Claim entry fields are invalid")
        task = entry["task"]
        if not isinstance(task, str) or not TASK_RE.fullmatch(task):
            raise ClaimAuditError("Claim task is invalid")
        if task in claims:
            raise ClaimAuditError(f"Duplicate claim task: {task}")
        if entry["status"] not in STATUSES:
            raise ClaimAuditError(f"Invalid claim status for {task}")
        sha = entry["expected_sha"]
        if entry["status"] == "released":
            if sha != "":
                raise ClaimAuditError(f"Released task {task} cannot retain a SHA")
        elif not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise ClaimAuditError(f"Claim SHA is invalid for {task}")
        if type(entry["issue"]) is not int or entry["issue"] < 1:
            raise ClaimAuditError(f"Issue number is invalid for {task}")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ClaimAuditError(f"Claim reason is missing for {task}")
        claims[task] = entry
    return claims


def parse_remote_refs(text):
    refs = {}
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        fields = raw.split()
        if len(fields) != 2 or not SHA_RE.fullmatch(fields[0]):
            raise ClaimAuditError(f"Malformed remote-ref line {line_number}")
        match = CLAIM_REF_RE.fullmatch(fields[1])
        if not match:
            raise ClaimAuditError(f"Unexpected remote ref on line {line_number}")
        task = match.group(1)
        if task in refs:
            raise ClaimAuditError(f"Duplicate remote claim: {task}")
        refs[task] = fields[0]
    return refs


def release_command(task, sha):
    if not TASK_RE.fullmatch(task) or not SHA_RE.fullmatch(sha):
        raise ClaimAuditError("Unsafe release command input")
    ref = f"refs/heads/claims/{task}"
    return f"git push --force-with-lease={ref}:{sha} origin :{ref}"


def audit(claims, refs):
    findings = []
    commands = []
    errors = []

    for task in sorted(set(refs) - set(claims)):
        errors.append({"task": task, "code": "unknown_remote_claim"})

    for task, entry in sorted(claims.items()):
        remote_sha = refs.get(task)
        status = entry["status"]
        expected = entry["expected_sha"]
        if status == "released":
            if remote_sha is None:
                findings.append({"task": task, "state": "released"})
            else:
                errors.append({"task": task, "code": "released_ref_present"})
            continue
        if remote_sha is None:
            if status == "release_ready":
                findings.append({"task": task, "state": "already_released"})
            else:
                errors.append({"task": task, "code": "required_ref_missing"})
            continue
        if remote_sha != expected:
            errors.append({"task": task, "code": "sha_mismatch"})
            continue
        findings.append({"task": task, "state": status})
        if status == "release_ready":
            commands.append({"task": task, "command": release_command(task, expected)})

    # A release list is useful only when the complete snapshot is internally
    # consistent. One unrelated unknown, missing, or changed lease suppresses
    # every command so an operator cannot act on a partially trusted audit.
    if errors:
        commands = []
    return {"ok": not errors, "findings": findings, "release_commands": commands, "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=".github/portfolio/CLAIMS.json")
    parser.add_argument("--refs", required=True, help="Saved output from git ls-remote for claims/*")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        claims = load_ledger(args.ledger)
        refs = parse_remote_refs(Path(args.refs).read_text(encoding="utf-8"))
        result = audit(claims, refs)
    except (OSError, ClaimAuditError) as exc:
        print(f"Claim audit failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["findings"]:
            print(f"{item['task']}: {item['state']}")
        for item in result["release_commands"]:
            print(f"RELEASE {item['task']}: {item['command']}")
        for item in result["errors"]:
            print(f"ERROR {item['task']}: {item['code']}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
