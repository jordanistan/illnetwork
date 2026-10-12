#!/usr/bin/env python3
"""Validate the two cash-site hosting artifacts and their cutover evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import html as html_module
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / ".github/portfolio/hosting/targets.json"
DEFAULT_EVIDENCE = ROOT / ".github/portfolio/hosting/P005_EVIDENCE_TEMPLATE.json"
MAX_HTML_BYTES = 512 * 1024
HELD_DOMAINS = {
    "sxswasted.com",
    "austinfcsoccer.com",
    "austinfcsoccer.net",
    "austinfcjerseys.com",
    "atxsoccerjerseys.com",
}
REQUIRED_HEADERS = {
    "content-security-policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self'; font-src 'self'; connect-src 'none'; "
        "frame-src 'none'; object-src 'none'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "strict-transport-security": "max-age=31536000",
}
PAWS_CSP = REQUIRED_HEADERS["content-security-policy"].replace(
    "img-src 'self';", "img-src 'self'; media-src 'self';"
)
EXPECTED_TARGETS = [
    {
        "domain": "pawsfectwalks.com",
        "repository": "jordanistan/illnetwork",
        "build_command": [
            "python3", "portfolio/build.py", "--mode", "production",
            "--domain", "pawsfectwalks.com", "--output", "<fresh-output>",
        ],
        "output_directory": "<fresh-output>",
        "entrypoint": "index.html",
        "script_source": "assets/site.js",
        "stylesheet_source": "assets/site.css",
        "canonical_url": "https://pawsfectwalks.com/",
        "headers_rule": "/*",
        "inquiry_email": "jordan.robison@gmail.com",
        "inquiry_subject": "Pawsfect Walks availability",
        "identity_text": "Pawsfect Walks",
        "required_notice": "Nothing is submitted by this website",
        "allowed_files": [
            ".nojekyll", "_headers", "assets/favicon.svg", "assets/hero.svg",
            "assets/site.css", "assets/site.js", "index.html", "privacy.html",
            "robots.txt", "sitemap.xml",
        ],
    },
    {
        "domain": "spaceghostkilla.com",
        "repository": "jordanistan/spaceghostkilla",
        "build_command": ["bash", "scripts/build_production.sh", "<fresh-output>"],
        "output_directory": "<fresh-output>",
        "entrypoint": "services.html",
        "script_source": "service-assets/site.js",
        "stylesheet_source": "service-assets/site.css",
        "canonical_url": "https://spaceghostkilla.com/services.html",
        "headers_rule": "/services.html",
        "inquiry_email": "support@spaceghostkilla.com",
        "inquiry_subject": "SpaceGhostKilla security review",
        "identity_text": "SpaceGhostKilla",
        "required_notice": "Nothing is submitted by this website",
        "allowed_files": [
            ".well-known/security.txt", "404.html", "CNAME", "_headers",
            "assets/downloads/SpaceGhostKilla-Cloud-Security-Quick-Audit-v1.2.pdf",
            "assets/downloads/sgk-quick-audit-v1.2.zip", "assets/favicon.png",
            "assets/spaceghostkilla-emblem.png", "assets/spaceghostkilla-wallpaper.png",
            "index.html", "legal.html", "robots.txt", "script.js",
            "service-assets/favicon.svg", "service-assets/hero.svg",
            "service-assets/site.css", "service-assets/site.js", "services.html",
            "site.webmanifest", "sitemap.xml", "styles.css", "thanks.html",
        ],
    },
]


class PreflightError(ValueError):
    """A hosting preflight boundary failure."""


def contains_held_domain(value: str) -> bool:
    """Catch plain and common encoded forms in deployable text assets."""
    decoded = value
    for _ in range(3):
        decoded = html_module.unescape(unquote(decoded))

    def replace_escape(match: re.Match[str]) -> str:
        digits = next(group for group in match.groups() if group is not None)
        try:
            return chr(int(digits, 16))
        except (ValueError, OverflowError):
            return match.group(0)

    decoded = re.sub(
        r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|([0-9a-fA-F]{1,6})\s?)",
        replace_escape,
        decoded,
    )
    return any(domain in decoded.lower() for domain in HELD_DOMAINS)


class InquiryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.script_sources: list[str] = []
        self.stylesheets: list[str] = []
        self.resource_sources: list[str] = []
        self.canonicals: list[str] = []
        self.unapproved_links: list[str] = []
        self.embedded_content: list[str] = []
        self.controls: list[str] = []
        self.submitting_controls: list[str] = []
        self.inline_scripts = 0
        self.event_attributes: list[str] = []
        self.checkout_attributes: list[str] = []
        self.base_elements = 0
        self.meta_refresh = 0
        self.inline_styles = 0
        self.inert_containers: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            raise PreflightError("Inquiry page contains duplicate HTML attributes")
        attributes = dict(attrs)
        self.event_attributes.extend(name for name in names if name.startswith("on"))
        self.checkout_attributes.extend(name for name in names if name == "data-checkout")
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"] or "")
        if tag == "script":
            if attributes.get("src"):
                self.script_sources.append(attributes["src"] or "")
            else:
                self.inline_scripts += 1
        if tag == "link":
            relation = {value.lower() for value in (attributes.get("rel") or "").split()}
            if relation == {"stylesheet"}:
                self.stylesheets.append(attributes.get("href") or "")
            elif relation == {"icon"}:
                self.resource_sources.append(attributes.get("href") or "")
            elif relation == {"canonical"}:
                self.canonicals.append(attributes.get("href") or "")
            else:
                self.unapproved_links.append(attributes.get("rel") or "(missing rel)")
        if tag in {"img", "audio", "source", "track", "video"}:
            self.resource_sources.append(attributes.get("src") or "")
        if tag in {"embed", "iframe", "object"}:
            self.embedded_content.append(tag)
        if tag in {"noscript", "template"}:
            self.inert_containers.append(tag)
        if tag in {"form", "input", "textarea"}:
            self.controls.append(tag)
        if tag in {"select", "button"} and any(
            attributes.get(name) for name in ("name", "form", "action", "formaction")
        ):
            self.submitting_controls.append(tag)
        if tag == "base":
            self.base_elements += 1
        if tag == "style" or "style" in attributes:
            self.inline_styles += 1
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "refresh":
            self.meta_refresh += 1

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"Cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PreflightError("JSON root must be an object")
    return value


def load_manifest(path: Path) -> list[dict]:
    manifest = read_json(path)
    if manifest != {"version": 1, "targets": EXPECTED_TARGETS}:
        raise PreflightError("Hosting manifest does not match the two reviewed targets")
    if any(domain in json.dumps(manifest).lower() for domain in HELD_DOMAINS):
        raise PreflightError("Hosting manifest references a held domain")
    return manifest["targets"]


def parse_headers(path: Path) -> dict[str, dict[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise PreflightError("Cannot read artifact _headers") from exc
    blocks: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace():
            if current is None or ":" not in raw:
                raise PreflightError("Malformed _headers rule")
            name, value = raw.strip().split(":", 1)
            name = name.strip().lower()
            if not name or name in blocks[current]:
                raise PreflightError("Duplicate or empty response header")
            blocks[current][name] = value.strip()
        else:
            current = raw.strip()
            if current in blocks:
                raise PreflightError("Duplicate _headers path rule")
            blocks[current] = {}
    return blocks


def expected_headers(domain: str) -> dict[str, str]:
    values = dict(REQUIRED_HEADERS)
    if domain == "pawsfectwalks.com":
        values["content-security-policy"] = PAWS_CSP
    return values


def validate_artifact(artifact: Path, target: dict) -> dict:
    try:
        root = artifact.resolve(strict=True)
    except OSError as exc:
        raise PreflightError("Artifact directory does not exist") from exc
    if not root.is_dir():
        raise PreflightError("Artifact path is not a directory")
    for candidate in artifact.rglob("*"):
        if candidate.is_symlink():
            raise PreflightError("Artifact contains a symlink")
    actual_files = {
        candidate.relative_to(root).as_posix()
        for candidate in root.rglob("*")
        if candidate.is_file()
    }
    if actual_files != set(target["allowed_files"]):
        raise PreflightError("Artifact file set does not match the reviewed export")
    text_suffixes = {
        ".css", ".html", ".js", ".json", ".svg", ".txt", ".webmanifest", ".xml",
    }
    for name in actual_files:
        candidate = root / name
        if candidate.suffix.lower() in text_suffixes or candidate.name in {
            "CNAME", "_headers", "robots.txt",
        }:
            try:
                deployable_text = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise PreflightError("Artifact text file is not readable UTF-8") from exc
            if contains_held_domain(deployable_text):
                raise PreflightError("Artifact text references a held domain")
    entry = root / target["entrypoint"]
    headers_path = root / "_headers"
    if not entry.is_file() or not headers_path.is_file():
        raise PreflightError("Artifact is missing its inquiry page or _headers")
    data = entry.read_bytes()
    if len(data) > MAX_HTML_BYTES:
        raise PreflightError("Inquiry page exceeds the size limit")
    try:
        html = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError("Inquiry page is not UTF-8") from exc
    parser = InquiryParser()
    parser.feed(html)
    parser.close()
    text = " ".join(" ".join(parser.text).split())
    if target["identity_text"] not in text or target["required_notice"] not in text:
        raise PreflightError("Inquiry page identity or no-submission notice is missing")
    if parser.controls or parser.submitting_controls:
        raise PreflightError("Inquiry page contains form controls")
    if (
        parser.inline_scripts or parser.inline_styles or parser.event_attributes
        or parser.base_elements or parser.meta_refresh
    ):
        raise PreflightError("Inquiry page contains unsafe active HTML")
    if parser.checkout_attributes:
        raise PreflightError("Inquiry page contains a checkout trigger")
    if parser.unapproved_links or parser.embedded_content or parser.inert_containers:
        raise PreflightError("Inquiry page contains an unapproved resource element")
    references = parser.script_sources + parser.stylesheets + parser.resource_sources
    for source in references:
        if not source or any(ord(char) <= 32 or char == "\\" for char in source):
            raise PreflightError("Inquiry page contains an unsafe resource reference")
        parsed = urlparse(source)
        if parsed.scheme or parsed.netloc or source.startswith("//"):
            raise PreflightError("Inquiry page contains an external resource")
    if parser.script_sources != [target["script_source"]]:
        raise PreflightError("Inquiry page scripts do not match the reviewed source")
    if parser.stylesheets != [target["stylesheet_source"]]:
        raise PreflightError("Inquiry page stylesheet does not match the reviewed source")
    if parser.canonicals != [target["canonical_url"]]:
        raise PreflightError("Inquiry page canonical does not match the reviewed domain")
    mailtos = [href for href in parser.hrefs if href.lower().startswith("mailto:")]
    if any(
        not href or any(ord(char) <= 32 or char == "\\" for char in href)
        or href.lower().startswith(("data:", "javascript:"))
        for href in parser.hrefs
    ):
        raise PreflightError("Inquiry page contains an unsafe link reference")
    if not mailtos:
        raise PreflightError("Inquiry page has no email inquiry link")
    for href in mailtos:
        parsed_mailto = urlparse(href)
        recipient = parsed_mailto.path.lower()
        if recipient != target["inquiry_email"].lower():
            raise PreflightError("Inquiry page email does not match the reviewed target")
        try:
            query = parse_qsl(
                parsed_mailto.query, keep_blank_values=True, strict_parsing=True
            )
        except ValueError as exc:
            raise PreflightError("Inquiry page email query is malformed") from exc
        keys = [key.lower() for key, _ in query]
        if len(keys) != len(set(keys)) or any(key != "subject" for key in keys):
            raise PreflightError("Inquiry page email query contains an unapproved field")
        if query:
            subject = query[0][1]
            if (
                subject != target["inquiry_subject"] or len(subject) > 160
                or any(ord(char) < 32 or ord(char) == 127 for char in subject)
            ):
                raise PreflightError("Inquiry page email subject is not reviewed")
    if any(
        marker in href.lower()
        for href in parser.hrefs
        for marker in ("checkout", "paypal", "squareup", "stripe", "lemonsqueezy")
    ):
        raise PreflightError("Inquiry page links to a checkout or payment provider")
    blocks = parse_headers(headers_path)
    if set(blocks) != {target["headers_rule"]}:
        raise PreflightError("Artifact contains an unreviewed _headers path rule")
    actual = blocks.get(target["headers_rule"])
    if actual is None:
        raise PreflightError("Artifact lacks the reviewed _headers path rule")
    required = expected_headers(target["domain"])
    for name, value in required.items():
        if actual.get(name) != value:
            raise PreflightError(f"Artifact header mismatch: {name}")
    return {
        "domain": target["domain"],
        "entrypoint": target["entrypoint"],
        "mailto_links": len(mailtos),
        "required_headers": len(required),
        "status": "artifact_ready_for_staging_review",
    }


def valid_https_url(value: str, *, production_domain: str | None = None) -> bool:
    if not isinstance(value, str) or not value or any(ord(char) <= 32 for char in value):
        return False
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.username
        or parsed.password or parsed.fragment or parsed.query or port not in {None, 443}
    ):
        return False
    if production_domain is None:
        return parsed.hostname.endswith(".pages.dev") and parsed.path in {"", "/"}
    return parsed.hostname == production_domain and parsed.path in {"", "/"}


def validate_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return False
    if parsed.tzinfo is None:
        return False
    return parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc) + timedelta(minutes=5)


def validate_evidence(path: Path) -> dict:
    evidence = read_json(path)
    required_root = {"version", "cutover_approved", "owner_approval_date", "targets"}
    if set(evidence) != required_root or evidence.get("version") != 1:
        raise PreflightError("Evidence root does not match the reviewed schema")
    targets = evidence.get("targets")
    if not isinstance(targets, list) or len(targets) != 2:
        raise PreflightError("Evidence must contain exactly two targets")
    expected_domains = [item["domain"] for item in EXPECTED_TARGETS]
    fields = {
        "domain", "status", "staging_url", "production_url", "deployment_sha",
        "checked_at", "http_200", "headers_verified", "inquiry_link_verified",
        "inbox_receipt_verified", "dns_snapshot_reviewed", "rollback_recorded", "notes",
    }
    verified_staging_hosts: list[str] = []
    for expected_domain, item in zip(expected_domains, targets):
        if not isinstance(item, dict) or set(item) != fields or item.get("domain") != expected_domain:
            raise PreflightError("Evidence target identity or fields are invalid")
        if any(domain in json.dumps(item).lower() for domain in HELD_DOMAINS):
            raise PreflightError("Evidence references a held domain")
        status = item.get("status")
        checks = [
            item.get("http_200"), item.get("headers_verified"),
            item.get("inquiry_link_verified"), item.get("inbox_receipt_verified"),
            item.get("dns_snapshot_reviewed"), item.get("rollback_recorded"),
        ]
        if not all(isinstance(value, bool) for value in checks):
            raise PreflightError("Evidence checks must be booleans")
        if status == "pending":
            if any(checks) or any(item.get(key) for key in ("staging_url", "production_url", "deployment_sha", "checked_at")):
                raise PreflightError("Pending evidence cannot contain completion claims")
        elif status in {"staging_verified", "cutover_verified"}:
            if not valid_https_url(item.get("staging_url", "")):
                raise PreflightError("Verified staging URL must use an HTTPS pages.dev host")
            verified_staging_hosts.append(urlparse(item["staging_url"]).hostname or "")
            if not re.fullmatch(r"[0-9a-f]{40}", item.get("deployment_sha", "")):
                raise PreflightError("Verified evidence requires a full commit SHA")
            if not validate_timestamp(item.get("checked_at", "")) or not all(checks):
                raise PreflightError("Verified evidence is missing a dated required check")
            if status == "staging_verified" and item.get("production_url"):
                raise PreflightError("Staging-only evidence cannot claim a production URL")
            if status == "cutover_verified" and not valid_https_url(
                item.get("production_url", ""), production_domain=expected_domain
            ):
                raise PreflightError("Cutover evidence requires the exact HTTPS production URL")
        else:
            raise PreflightError("Unknown evidence status")
        if not isinstance(item.get("notes"), str):
            raise PreflightError("Evidence notes must be text")
    if len(verified_staging_hosts) != len(set(verified_staging_hosts)):
        raise PreflightError("Verified targets must use distinct staging hosts")
    approved = evidence.get("cutover_approved")
    if not isinstance(approved, bool):
        raise PreflightError("cutover_approved must be a boolean")
    if approved:
        if any(item["status"] != "cutover_verified" for item in targets):
            raise PreflightError("Cutover cannot be approved before both targets are verified")
        try:
            approval_date = datetime.strptime(
                evidence.get("owner_approval_date", ""), "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError) as exc:
            raise PreflightError("Approved cutover requires an owner approval date") from exc
        if approval_date > datetime.now(timezone.utc).date():
            raise PreflightError("Owner approval date cannot be in the future")
    elif evidence.get("owner_approval_date") is not None:
        raise PreflightError("Unapproved evidence cannot contain an owner approval date")
    return {
        "targets": len(targets),
        "cutover_approved": approved,
        "statuses": {item["domain"]: item["status"] for item in targets},
    }


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("manifest")
    artifact = subcommands.add_parser("artifact")
    artifact.add_argument("--domain", required=True)
    artifact.add_argument("--artifact", type=Path, required=True)
    evidence = subcommands.add_parser("evidence")
    evidence.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    return parser


def main() -> int:
    args = command_parser().parse_args()
    try:
        targets = load_manifest(args.manifest)
        if args.command == "manifest":
            result = {"targets": [item["domain"] for item in targets], "status": "reviewed"}
        elif args.command == "artifact":
            matches = [item for item in targets if item["domain"] == args.domain]
            if len(matches) != 1:
                raise PreflightError("Domain is not an approved P005 target")
            result = validate_artifact(args.artifact, matches[0])
        else:
            result = validate_evidence(args.evidence)
    except PreflightError as exc:
        print(f"Hosting preflight failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
