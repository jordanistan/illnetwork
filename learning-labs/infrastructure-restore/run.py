#!/usr/bin/env python3
"""Create and verify a restore drill using only synthetic local data."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


SYNTHETIC_FILES = {
    "customers/example.txt": "synthetic customer record: C-100\n",
    "orders/example.txt": "synthetic order record: O-200\n",
    "settings/example.txt": "synthetic setting: training=true\n",
}


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def safe_member(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        return False
    raw_parts = name.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        return False
    if re.match(r"^[A-Za-z]:", raw_parts[0]):
        return False
    candidate = PurePosixPath(name)
    return not candidate.is_absolute() and candidate.parts == tuple(raw_parts)


def run_drill(workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=workspace))
    source = run_dir / "source"
    restored = run_dir / "restored"
    archive = run_dir / "synthetic-backup.zip"

    for relative, content in SYNTHETIC_FILES.items():
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    source_hashes = {name: digest(source / name) for name in sorted(SYNTHETIC_FILES)}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in sorted(SYNTHETIC_FILES):
            bundle.write(source / name, arcname=name)

    with zipfile.ZipFile(archive, "r") as bundle:
        members = bundle.namelist()
        members_safe = all(safe_member(name) for name in members)
        if not members_safe:
            raise ValueError("archive contains an unsafe member path")
        restored.mkdir(parents=True, exist_ok=False)
        restore_root = restored.resolve()
        for name in members:
            destination = (restored / PurePosixPath(name)).resolve()
            if not destination.is_relative_to(restore_root):
                raise ValueError("archive member escapes the restore directory")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.read(name))

    restored_hashes = {name: digest(restored / name) for name in sorted(SYNTHETIC_FILES)}
    files = [
        {
            "path": name,
            "source_sha256": source_hashes[name],
            "restored_sha256": restored_hashes[name],
            "match": source_hashes[name] == restored_hashes[name],
        }
        for name in sorted(SYNTHETIC_FILES)
    ]
    result = "PASS" if members_safe and all(item["match"] for item in files) else "FAIL"
    outcome = {
        "schema_version": 1,
        "exercise_id": "infrastructure-synthetic-restore",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_classification": "synthetic",
        "network_activity": "none",
        "archive_members_safe": members_safe,
        "files": files,
        "result": result,
        "limitations": [
            "This local drill does not establish production recoverability.",
            "Recovery time, permissions, encryption, retention, and application consistency are not tested.",
        ],
    }
    report = run_dir / "outcome.json"
    report.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path, help="Disposable parent directory for a new run")
    return parser.parse_args()


def main() -> int:
    report = run_drill(parse_args().workspace)
    result = json.loads(report.read_text(encoding="utf-8"))["result"]
    print(f"{result}: evidence written to {report}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
