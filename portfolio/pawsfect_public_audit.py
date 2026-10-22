#!/usr/bin/env python3
"""Audit the fixed public Pawsfect prelaunch surface without credentials."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT_URL = "https://pawsfectwalks.com/"
EXPECTED_TITLE = "Pawsfect Walks | Austin Pre-launch Waitlist"
EXPECTED_DESCRIPTION = (
    "Pawsfect Walks is a pre-launch Austin dog-care concept. Join the waitlist; "
    "no booking, paid care, or recruiting is available."
)
MODULE_PATH = re.compile(r"/assets/index-[A-Za-z0-9_-]+\.js\Z")
STYLESHEET_PATH = re.compile(r"/assets/index-[A-Za-z0-9_-]+\.css\Z")
ROOT_LIMIT = 256 * 1024
BUNDLE_LIMIT = 2 * 1024 * 1024
TIMEOUT_SECONDS = 10
P015_GATE_IDS = (
    "pilot_role_scope",
    "classification_model_review",
    "pay_control_terms_reviewed",
    "insurance_worker_coverage",
    "screening_consent_process",
    "private_candidate_data_controls",
    "structured_interview_process",
    "recruiting_authorization",
)

REQUIRED_BOUNDARIES = (
    "Join the Waitlist",
    "Pre-launch",
    "Submitting this waitlist request does not create a booking.",
    "Paid care is not available yet.",
    "Recruiting is not open.",
    "Do not send addresses, access codes, payment details, IDs, or medical records.",
)

PROHIBITED_MARKERS = (
    "Hiring now",
    "Apply in minutes",
    "Walk dogs, get paid",
    "Get paid to walk dogs",
    "We bring the bookings",
    "Apply by email",
    "Apply now",
    "Send your resume",
    "Upload your resume",
    "Join our team",
    "Job application",
    "Walker application",
    "Candidate application",
    "careers@",
    "application@",
    "recruiting candidates",
    "Tell us about yourself",
    "No hustling for clients",
    "We're onboarding our first local walkers now",
    "government-issued state ID",
    "Local team members assigned by service area",
    "same familiar faces",
    "Dog Sitting",
    "Dog boarding",
    "sitting services",
    "Now accepting bookings",
    "Now booking",
    "Book a walk",
    "Schedule a walk",
    "Reserve a walk",
    "Accepting clients",
    "available today",
    "any special needs",
    "Austin, TX and surrounding areas",
    "Project manager oversight from pickup to return",
    "Central & Downtown",
    "South Austin",
    "East Austin",
    "North Austin",
)

PROHIBITED_COMMERCE = re.compile(
    # A one-digit ``$1``-style token is common in minified JavaScript captures;
    # match displayed two-or-more-digit rates and explicit commerce language.
    r"(?:\$[1-9]\d{1,3}(?:\.\d{2})?|\bper (?:hour|walk)\b|Book now|Booking confirmed|Checkout|Stripe|coverage active|care is available now)",
    re.IGNORECASE,
)
PROHIBITED_RECRUITING = re.compile(
    r"(?:\bapply\b|application|\bcareers?\b|\bresume\b|\bcandidates?\b|\bhiring\b|\brecruiting\b|become a walker)",
    re.IGNORECASE,
)


class AuditError(RuntimeError):
    """The public surface crossed a reviewed prelaunch boundary."""


def _reject_ambiguous_url(value: str) -> None:
    if not value or "\\" in value or any(ord(char) < 0x21 for char in value):
        raise AuditError("URL contains empty, control, whitespace, or backslash data")
    if "%" in value:
        raise AuditError("percent-encoded URL data is not allowed")


def validate_root_url(actual: str) -> None:
    _reject_ambiguous_url(actual)
    parsed = urlsplit(actual)
    try:
        port = parsed.port
    except ValueError as exc:
        raise AuditError(f"invalid endpoint port: {exc}") from exc
    if actual != ROOT_URL or parsed.scheme != "https":
        raise AuditError("root endpoint changed")
    if parsed.username is not None or parsed.password is not None or port is not None:
        raise AuditError("root endpoint contains credentials or an explicit port")
    if parsed.query or parsed.fragment:
        raise AuditError("root endpoint contains a query or fragment")


def validate_asset_url(actual: str, expected: str) -> None:
    _reject_ambiguous_url(actual)
    parsed = urlsplit(actual)
    wanted = urlsplit(expected)
    try:
        port = parsed.port
    except ValueError as exc:
        raise AuditError(f"invalid asset port: {exc}") from exc
    if actual != expected or parsed.scheme != "https":
        raise AuditError("asset endpoint changed")
    if parsed.hostname != "pawsfectwalks.com":
        raise AuditError("asset hostname changed")
    if parsed.username is not None or parsed.password is not None or port is not None:
        raise AuditError("asset endpoint contains credentials or an explicit port")
    if parsed.query or parsed.fragment or not MODULE_PATH.fullmatch(parsed.path):
        raise AuditError("asset path crossed the reviewed module boundary")
    if "/../" in parsed.path or "/./" in parsed.path or "//" in parsed.path:
        raise AuditError("asset path contains an ambiguous segment")
    if parsed != wanted:
        raise AuditError("asset endpoint changed")


class ExactRedirectHandler(HTTPRedirectHandler):
    """Limit redirects and validate every destination before following it."""

    max_redirections = 3
    max_repeats = 1

    def __init__(self, expected: str, kind: str) -> None:
        super().__init__()
        self.expected = expected
        self.kind = kind

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        if self.kind == "root":
            validate_root_url(newurl)
        else:
            validate_asset_url(newurl, self.expected)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_bounded(response, limit: int) -> bytes:  # noqa: ANN001
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            declared = int(length)
        except ValueError as exc:
            raise AuditError("invalid Content-Length") from exc
        if declared < 0 or declared > limit:
            raise AuditError("declared response exceeds byte limit")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(64 * 1024, limit + 1 - total))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise AuditError("streamed response exceeds byte limit")
        chunks.append(chunk)


def fetch_url(
    url: str,
    *,
    expected_types: set[str],
    limit: int,
    kind: str,
    opener=None,
) -> bytes:
    if kind == "root":
        validate_root_url(url)
    else:
        validate_asset_url(url, url)
    if opener is None:
        opener = build_opener(ExactRedirectHandler(url, kind))
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": ", ".join(sorted(expected_types)),
            "Accept-Encoding": "identity",
            "User-Agent": "pawsfect-public-audit/1.0",
        },
    )
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        status = getattr(response, "status", None)
        if status is None:
            status = response.getcode()
        if status != 200:
            raise AuditError(f"unexpected HTTP status {status}")
        final_url = response.geturl()
        if kind == "root":
            validate_root_url(final_url)
        else:
            validate_asset_url(final_url, url)
        content_type = response.headers.get_content_type()
        if content_type not in expected_types:
            raise AuditError(f"unexpected content type {content_type}")
        return _read_bounded(response, limit)


def _safe_local_asset(value: str, pattern: re.Pattern[str]) -> bool:
    if not value or "%" in value or "\\" in value or value.startswith("//"):
        return False
    parsed = urlsplit(value)
    return bool(
        not parsed.scheme
        and not parsed.netloc
        and not parsed.query
        and not parsed.fragment
        and pattern.fullmatch(parsed.path)
        and "/../" not in parsed.path
        and "/./" not in parsed.path
        and "//" not in parsed.path
    )


class RootDocument(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_title = False
        self._title_parts: list[str] = []
        self.titles: list[str] = []
        self.canonicals: list[str] = []
        self.modules: list[str] = []
        self.stylesheets: list[str] = []
        self.metas: dict[str, str] = {}
        self.public_text: list[str] = []
        self.declarations: list[str] = []
        self.counts: dict[str, int] = {}
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        self.counts[tag] = self.counts.get(tag, 0) + 1
        names = [name.lower() for name, _ in attrs]
        if len(names) != len(set(names)):
            self.errors.append(f"duplicate attribute on {tag}")
            return
        if any(name.startswith("on") for name in names):
            self.errors.append(f"unexpected event handler on {tag}")
        attributes = dict(attrs)
        if tag not in {"html", "head", "meta", "link", "title", "script", "body", "div"}:
            self.errors.append(f"unexpected element: {tag}")
            return
        if tag == "html":
            if attributes != {"lang": "en"}:
                self.errors.append("html attributes changed")
        elif tag in {"head", "body"}:
            if attributes:
                self.errors.append(f"unexpected attributes on {tag}")
        elif tag == "title":
            if attributes:
                self.errors.append("unexpected attributes on title")
            self._capture_title = True
            self._title_parts = []
        elif tag == "meta":
            self._handle_meta(attributes)
        elif tag == "link":
            rel = {item.lower() for item in attributes.get("rel", "").split()}
            href = attributes.get("href", "")
            if rel == {"canonical"} and set(attributes) == {"rel", "href"}:
                self.canonicals.append(href)
            elif rel == {"stylesheet"} and set(attributes) == {
                "rel",
                "crossorigin",
                "href",
            }:
                if attributes.get("crossorigin") not in {None, ""}:
                    self.errors.append("stylesheet crossorigin value changed")
                if not _safe_local_asset(href, STYLESHEET_PATH):
                    self.errors.append(f"unexpected stylesheet: {href}")
                self.stylesheets.append(href)
            else:
                self.errors.append("unexpected link relation or attributes")
        elif tag == "script":
            source = attributes.get("src")
            if set(attributes) != {"type", "crossorigin", "src"}:
                self.errors.append("unexpected script attributes")
            if attributes.get("crossorigin") not in {None, ""}:
                self.errors.append("script crossorigin value changed")
            if source is None:
                self.errors.append("unexpected inline script")
            elif attributes.get("type", "").lower() != "module":
                self.errors.append("unexpected non-module script")
            elif not _safe_local_asset(source, MODULE_PATH):
                self.errors.append(f"unexpected module source: {source}")
            else:
                self.modules.append(source)
        elif tag == "div":
            if attributes != {"id": "root"}:
                self.errors.append("unexpected div or div attributes")

        if tag not in {"meta", "link"}:
            self.stack.append(tag)

    def _handle_meta(self, attributes: dict[str, str | None]) -> None:
        key = ""
        value = ""
        if set(attributes) == {"charset"} and str(attributes.get("charset", "")).lower() == "utf-8":
            key, value = "charset", "utf-8"
        elif set(attributes) == {"name", "content"}:
            name = str(attributes.get("name", "")).lower()
            if name in {"viewport", "description"}:
                key, value = name, str(attributes.get("content", ""))
        elif set(attributes) == {"property", "content"}:
            prop = str(attributes.get("property", "")).lower()
            if prop in {"og:title", "og:description", "og:url", "og:type"}:
                key, value = prop, str(attributes.get("content", ""))
        if not key:
            self.errors.append("unexpected meta element or attributes")
            return
        if key in self.metas:
            self.errors.append(f"duplicate meta element: {key}")
            return
        self.metas[key] = value
        if key not in {"charset", "viewport", "og:url", "og:type"}:
            self.public_text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._capture_title:
            title = " ".join("".join(self._title_parts).split())
            self.titles.append(title)
            self.public_text.append(title)
            self._capture_title = False
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected closing element: {tag}")
        else:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
        elif data.strip():
            self.public_text.append(data)

    def handle_decl(self, decl: str) -> None:
        self.declarations.append(decl)

    def handle_comment(self, data: str) -> None:
        self.errors.append("unexpected HTML comment")

    def handle_startendtag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag not in {"meta", "link"}:
            self.errors.append(f"unexpected self-closing element: {tag}")
            return
        self.handle_starttag(tag, attrs)


def _policy_errors(text: str, *, require_boundaries: bool) -> list[str]:
    normalized = " ".join(text.split()).casefold()
    errors: list[str] = []
    if require_boundaries:
        for marker in REQUIRED_BOUNDARIES:
            if " ".join(marker.split()).casefold() not in normalized:
                errors.append(f"missing boundary: {marker}")
    for marker in PROHIBITED_MARKERS:
        if " ".join(marker.split()).casefold() in normalized:
            errors.append(f"prohibited marker: {marker}")
    commerce = PROHIBITED_COMMERCE.search(normalized)
    if commerce:
        errors.append(f"review-required commerce marker: {commerce.group(0)}")
    # The required negative recruiting statement is the sole approved use of
    # that token while P015 is pending. Candidate/application paths remain
    # prohibited even when their mailto subject is encoded or built at runtime.
    recruiting_text = normalized
    for approved_negative in (
        "recruiting is not open.",
        "no booking, paid care, or recruiting is available.",
    ):
        recruiting_text = recruiting_text.replace(approved_negative, "")
    recruiting = PROHIBITED_RECRUITING.search(recruiting_text)
    if recruiting:
        errors.append(f"prohibited recruiting marker: {recruiting.group(0)}")
    return errors


def inspect_root(data: bytes) -> tuple[str, list[str]]:
    """Return the reviewed module and content-policy errors for a safe shell."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AuditError("root response is not strict UTF-8") from exc
    document = RootDocument()
    document.feed(text)
    document.close()
    if document.stack:
        document.errors.append("unclosed root element")
    if document.declarations != ["doctype html"]:
        document.errors.append("document type changed")
    expected_counts = {
        "html": 1,
        "head": 1,
        "meta": 7,
        "link": 2,
        "title": 1,
        "script": 1,
        "body": 1,
        "div": 1,
    }
    if document.counts != expected_counts:
        document.errors.append("root element inventory changed")
    if document.canonicals != [ROOT_URL]:
        document.errors.append("root canonical changed")
    if len(document.modules) != 1:
        document.errors.append("root must contain exactly one reviewed module")
    if len(document.stylesheets) != 1:
        document.errors.append("root must contain exactly one reviewed stylesheet")
    if document.errors:
        raise AuditError("; ".join(document.errors))

    expected_metas = {
        "charset": "utf-8",
        "viewport": "width=device-width, initial-scale=1.0",
        "description": EXPECTED_DESCRIPTION,
        "og:title": EXPECTED_TITLE,
        "og:description": EXPECTED_DESCRIPTION,
        "og:url": ROOT_URL,
        "og:type": "website",
    }
    policy_errors: list[str] = []
    if document.titles != [EXPECTED_TITLE]:
        policy_errors.append("root title changed")
    if document.metas != expected_metas:
        policy_errors.append("root metadata crossed the reviewed prelaunch boundary")
    policy_errors.extend(_policy_errors(" ".join(document.public_text), require_boundaries=False))
    return urljoin(ROOT_URL, document.modules[0]), policy_errors


def verify_root(data: bytes) -> str:
    module_url, policy_errors = inspect_root(data)
    if policy_errors:
        raise AuditError("; ".join(policy_errors))
    return module_url


def verify_pending_gates(repo_root: Path) -> None:
    state = json.loads((repo_root / ".github/portfolio/STATE.json").read_text())
    if state.get("pawsfect_walks", {}).get("launch_status") != (
        "not ready; seven confirmations pending"
    ):
        raise AuditError("P003 launch state changed; review the audit boundary")
    evidence = json.loads(
        (
            repo_root
            / ".github/portfolio/pawsfect-recruiting/P015_RECRUITING_EVIDENCE_TEMPLATE.json"
        ).read_text()
    )
    for field in (
        "recruiting_approved",
        "hire_authorized",
        "dispatch_authorized",
        "paid_care_launch_ready",
    ):
        if evidence.get(field) is not False:
            raise AuditError(f"P015 field changed: {field}")
    gates = evidence.get("gates")
    if not isinstance(gates, list) or tuple(gate.get("id") for gate in gates) != P015_GATE_IDS:
        raise AuditError("P015 gate inventory changed; review the audit boundary")
    if any(gate.get("status") != "pending" for gate in gates):
        raise AuditError("P015 gate state changed; review the audit boundary")


def verify_bundle(data: bytes) -> str:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AuditError("module response is not strict UTF-8") from exc
    errors = _policy_errors(text, require_boundaries=True)
    if errors:
        raise AuditError("; ".join(errors))
    return hashlib.sha256(data).hexdigest()


def run(repo_root: Path, opener=None) -> tuple[str, int, int]:
    verify_pending_gates(repo_root)
    root = fetch_url(
        ROOT_URL,
        expected_types={"text/html"},
        limit=ROOT_LIMIT,
        kind="root",
        opener=opener,
    )
    module_url, root_errors = inspect_root(root)
    bundle = fetch_url(
        module_url,
        expected_types={"application/javascript", "text/javascript"},
        limit=BUNDLE_LIMIT,
        kind="asset",
        opener=opener,
    )
    try:
        digest = verify_bundle(bundle)
    except AuditError as exc:
        if root_errors:
            raise AuditError("; ".join([*root_errors, str(exc)])) from exc
        raise
    if root_errors:
        raise AuditError("; ".join(root_errors))
    return digest, len(root), len(bundle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the fixed public Pawsfect prelaunch surface."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing the canonical P003/P015 state.",
    )
    args = parser.parse_args(argv)
    try:
        digest, root_bytes, bundle_bytes = run(args.repo_root.resolve())
    except (AuditError, OSError, json.JSONDecodeError) as exc:
        print(f"Pawsfect public audit failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Pawsfect public audit passed: "
        f"root_bytes={root_bytes}; bundle_bytes={bundle_bytes}; bundle_sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
