import datetime
import hmac
import os
import re
from pathlib import Path

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def validate_agent_token(configured_token, provided_token):
    if not configured_token or not provided_token:
        return False
    return hmac.compare_digest(str(configured_token), str(provided_token))


def sanitize_agent_host(hostname):
    safe_host = SAFE_FILENAME_RE.sub("_", hostname or "agent").strip("._-")
    return safe_host or "agent"


def save_agent_scan_log(report_dir, hostname, scan_text, timestamp=None):
    ts = timestamp or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_host = sanitize_agent_host(hostname)
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{safe_host}-{ts}-agent-scan.txt"
    path.write_text(scan_text)
    return str(path)
