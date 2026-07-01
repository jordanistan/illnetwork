import html
import re
import secrets
from pathlib import Path


SECRET_SETTING_KEYS = {"OPENAI_API_KEY", "SMTP_PASS", "AGENT_TOKEN", "ADMIN_PASSWORD"}
DEFAULT_ADMIN_PASSWORDS = {"", "password", "admin", "changeme", "change-me"}
_HOST_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_USER_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_report_path(report_dir, filename, allowed_suffixes=None):
    if not filename or Path(filename).is_absolute():
        raise ValueError("Invalid report path.")

    candidate = (Path(report_dir) / filename).resolve()
    base = Path(report_dir).resolve()
    if not _is_relative_to(candidate, base):
        raise ValueError("Report path escapes the report directory.")

    if allowed_suffixes is not None and candidate.suffix not in allowed_suffixes:
        raise ValueError("Invalid report format.")

    return candidate


def ensure_child_path(parent_dir, child_path):
    candidate = Path(child_path).resolve()
    parent = Path(parent_dir).resolve()
    if not _is_relative_to(candidate, parent):
        raise ValueError("Path escapes the allowed directory.")
    return candidate


def mask_secret_settings(settings):
    masked = dict(settings)
    for key in SECRET_SETTING_KEYS:
        if key in masked:
            masked[key] = ""
    return masked


def get_csrf_token(session_obj):
    token = session_obj.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session_obj["csrf_token"] = token
    return token


def validate_csrf_token(session_obj, submitted_token):
    expected = session_obj.get("csrf_token")
    if not expected or not submitted_token:
        return False
    return secrets.compare_digest(str(expected), str(submitted_token))


def require_secure_admin_password(password):
    value = (password or "").strip()
    if value.lower() in DEFAULT_ADMIN_PASSWORDS or len(value) < 12:
        raise ValueError("ADMIN_PASSWORD must be set to a non-default value with at least 12 characters.")
    return password


def _validate_remote_identity(remote_user, remote_host):
    if not remote_user or not _USER_RE.fullmatch(remote_user):
        raise ValueError("Invalid remote user.")
    if not remote_host or not _HOST_RE.fullmatch(remote_host) or remote_host.startswith("-"):
        raise ValueError("Invalid remote host.")


def build_remediation_command(target_host, configured_remote_host, configured_remote_user):
    if target_host == "localhost":
        return ["bash", "-s"]

    if configured_remote_host and target_host == configured_remote_host:
        _validate_remote_identity(configured_remote_user, target_host)
        return [
            "ssh",
            "-o",
            "StrictHostKeyChecking=accept-new",
            f"{configured_remote_user}@{target_host}",
            "bash",
            "-s",
        ]

    raise ValueError(f"Target host '{target_host}' is not configured for remediation.")


def safe_report_base_filename(hostname, timestamp, severity):
    safe_host = _SAFE_FILENAME_RE.sub("_", hostname or "localhost").strip("._-")
    if not safe_host:
        safe_host = "localhost"

    safe_timestamp = _SAFE_FILENAME_RE.sub("_", timestamp)
    safe_severity = _SAFE_FILENAME_RE.sub("_", severity or "low").lower()
    return f"{safe_host}-{safe_timestamp}-Summary-Report-{safe_severity}"


def markdown_to_safe_html(markdown_text):
    try:
        import mistune

        markdown = mistune.create_markdown(escape=True)
        return markdown(markdown_text)
    except Exception:
        return f"<pre>{html.escape(markdown_text)}</pre>"
