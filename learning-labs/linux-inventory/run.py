#!/usr/bin/env python3
"""Create a deliberately narrow inventory of the local machine."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED_FIELDS = [
    "environment variables",
    "file contents",
    "host names",
    "IP addresses",
    "process identities",
    "user names",
]


def clean_value(value: str, limit: int = 160) -> str:
    """Remove control characters and cap untrusted local metadata."""
    printable = "".join(char for char in value if char.isprintable())
    return printable[:limit]


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    allowed = {"ID", "VERSION_ID", "PRETTY_NAME"}
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return values
    for line in lines:
        key, separator, raw_value = line.partition("=")
        if separator and key in allowed:
            values[key.lower()] = clean_value(raw_value.strip().strip("\"'"))
    return values


def listening_tcp_ports(proc_root: Path = Path("/proc/net")) -> list[int]:
    ports: set[int] = set()
    for name in ("tcp", "tcp6"):
        try:
            rows = (proc_root / name).read_text(encoding="ascii", errors="replace").splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            fields = row.split()
            if len(fields) < 4 or fields[3] != "0A":
                continue
            try:
                port = int(fields[1].rsplit(":", 1)[1], 16)
            except (IndexError, ValueError):
                continue
            if 0 <= port <= 65535:
                ports.add(port)
    return sorted(ports)


def build_report() -> dict[str, object]:
    disk = shutil.disk_usage(Path(os.path.abspath(os.sep)))
    system = platform.system()
    return {
        "schema_version": 1,
        "exercise_id": "independent-linux-minimum-inventory",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "local machine only",
        "network_activity": "none",
        "platform": {
            "system": clean_value(system),
            "kernel_release": clean_value(platform.release()),
            "architecture": clean_value(platform.machine()),
            "python_version": clean_value(platform.python_version()),
            "os_release": read_os_release() if system == "Linux" else {},
        },
        "root_filesystem": {"total_bytes": disk.total, "free_bytes": disk.free},
        "listening_tcp_ports": listening_tcp_ports() if system == "Linux" else [],
        "excluded_fields": EXCLUDED_FIELDS,
        "limitations": [
            "This inventory is not a security assessment or availability check.",
            "Port numbers do not establish ownership, exposure, or service health.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="JSON report path that does not already exist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(build_report(), stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        print(f"Refusing to replace existing output: {args.output}", file=sys.stderr)
        return 2
    print(f"Wrote local-only inventory to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
