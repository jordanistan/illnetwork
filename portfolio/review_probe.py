#!/usr/bin/env python3
"""Verify the public educational review catalog without changing deployment state."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_URL = "https://iamjordanrobison.com/domain-previews/review.html"
MAX_RESPONSE_BYTES = 512 * 1024
ALLOWED_HOSTS = {
    "iamjordanrobison.com",
    "ill.network",
    "jordanistan.github.io",
}
PAYMENT_HOST_MARKERS = (
    "checkout",
    "lemonsqueezy",
    "paypal",
    "squareup",
    "stripe",
)
EXPECTED_SCRIPT = "assets/site.js"
REQUIRED_CSP = {
    "default-src": {"'none'"},
    "script-src": {"'self'"},
    "style-src": {"'self'"},
    "img-src": {
        "'self'",
        "https://raw.githubusercontent.com/jordanistan/iambirdy/main/iambirdy.jpg",
    },
    "font-src": {"'self'"},
    "connect-src": {"'none'"},
    "frame-src": {"'none'"},
    "object-src": {"'none'"},
    "base-uri": {"'none'"},
    "form-action": {"'none'"},
}


class ProbeError(ValueError):
    """A public-review verification failure."""


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.script_sources: list[str] = []
        self.inline_scripts = 0
        self.base_elements = 0
        self.capture_controls: list[str] = []
        self.csp_values: list[str] = []
        self.stylesheets: list[str] = []
        self.icons: list[str] = []
        self.active_resource_tags: list[str] = []
        self.duplicate_attributes: list[str] = []
        self.event_attributes: list[str] = []
        self.unapproved_links: list[str] = []
        self.meta_refresh = 0
        self.inline_styles = 0
        self.head_elements = 0
        self.csp_outside_head = 0
        self.inert_containers: list[str] = []
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self._in_head = False
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute_names = [name for name, _ in attrs]
        if len(attribute_names) != len(set(attribute_names)):
            self.duplicate_attributes.append(tag)
        self.event_attributes.extend(
            f"{tag}[{name}]" for name in attribute_names if name.startswith("on")
        )
        attributes = dict(attrs)
        if tag == "head":
            self.head_elements += 1
            self._in_head = True
        if tag in {"template", "noscript"}:
            self.inert_containers.append(tag)
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"] or "")
        if tag == "script":
            if attributes.get("src"):
                self.script_sources.append(attributes["src"] or "")
            else:
                self.inline_scripts += 1
        if tag == "base":
            self.base_elements += 1
        if tag == "style" or "style" in attributes:
            self.inline_styles += 1
        if tag in {"embed", "iframe", "img", "object", "source", "track", "video", "audio"}:
            self.active_resource_tags.append(tag)
        if tag == "link":
            relation = {
                value.lower() for value in (attributes.get("rel") or "").split()
            }
            if relation == {"stylesheet"}:
                self.stylesheets.append(attributes.get("href") or "")
            elif relation == {"icon"}:
                self.icons.append(attributes.get("href") or "")
            else:
                self.unapproved_links.append(attributes.get("rel") or "(missing rel)")
        if tag in {"form", "input", "select", "textarea"}:
            self.capture_controls.append(tag)
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == (
            "content-security-policy"
        ):
            self.csp_values.append(attributes.get("content") or "")
            if not self._in_head:
                self.csp_outside_head += 1
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "refresh":
            self.meta_refresh += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._in_head = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)


def approved_url(value: str) -> str:
    if not isinstance(value, str) or not value or any(
        ord(character) <= 32 or character == "\\" for character in value
    ):
        raise ProbeError("URL contains unsafe whitespace, controls, or backslashes")
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ProbeError("URL contains an invalid port") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname.lower() not in ALLOWED_HOSTS
        or parsed.username
        or parsed.password
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise ProbeError("URL must be an approved credential-free HTTPS review endpoint")
    return value


class ApprovedRedirectHandler(HTTPRedirectHandler):
    """Refuse an unsafe redirect before urllib sends the next request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        approved_url(target)
        return super().redirect_request(req, fp, code, msg, headers, target)


def load_domains(config_path: Path) -> tuple[list[str], list[str]]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"Cannot read portfolio configuration: {config_path}") from exc
    try:
        allowed = [item["domain"] for item in config["sites"] + config["aliases"]]
        excluded = list(config["excluded"])
    except (KeyError, TypeError) as exc:
        raise ProbeError("Portfolio configuration does not match the expected schema") from exc
    if (
        len(allowed) != 14
        or len(set(allowed)) != 14
        or not all(isinstance(domain, str) for domain in allowed + excluded)
    ):
        raise ProbeError("Portfolio configuration must contain 14 unique allowed domains")
    return allowed, excluded


def parse_catalog(html: bytes) -> CatalogParser:
    if len(html) > MAX_RESPONSE_BYTES:
        raise ProbeError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes")
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError("Response is not UTF-8 HTML") from exc
    parser = CatalogParser()
    parser.feed(text)
    parser.close()
    return parser


def validate_csp(values: list[str]) -> None:
    if len(values) != 1:
        raise ProbeError("Catalog must contain exactly one CSP meta policy")
    directives: dict[str, set[str]] = {}
    for part in values[0].split(";"):
        tokens = part.strip().split()
        if not tokens:
            continue
        name, sources = tokens[0].lower(), {token.lower() for token in tokens[1:]}
        if name in directives:
            raise ProbeError(f"Catalog CSP repeats directive: {name}")
        directives[name] = sources
    if directives != REQUIRED_CSP:
        raise ProbeError("Catalog CSP does not match the complete approved policy")
    if any("'unsafe-inline'" in sources or "*" in sources for sources in directives.values()):
        raise ProbeError("Catalog CSP permits unsafe inline or wildcard content")


def validate_catalog(
    html: bytes,
    *,
    source_url: str,
    allowed_domains: list[str],
    excluded_domains: list[str],
) -> dict:
    parser = parse_catalog(html)
    title = " ".join("".join(parser.title_parts).split())
    visible_text = " ".join(" ".join(parser.text_parts).split())
    expected_links = {f"{domain}/index.html" for domain in allowed_domains}
    catalog_links = {href for href in parser.hrefs if href in expected_links}
    missing = sorted(expected_links - catalog_links)
    if title != "Domain studio / All previews":
        raise ProbeError("Unexpected catalog title")
    if "DESIGN REVIEW" not in visible_text or "No live booking" not in visible_text:
        raise ProbeError("Educational-review boundary notice is missing")
    if missing:
        raise ProbeError(f"Missing allowed preview links: {', '.join(missing)}")
    if parser.capture_controls:
        raise ProbeError("Catalog contains form or data-entry controls")
    if parser.duplicate_attributes:
        raise ProbeError("Catalog contains duplicate HTML attributes")
    if parser.event_attributes:
        raise ProbeError("Catalog contains inline event-handler attributes")
    if parser.base_elements:
        raise ProbeError("Catalog contains a base element that can rewrite link targets")
    if parser.inline_scripts:
        raise ProbeError("Catalog contains inline script")
    if parser.inline_styles:
        raise ProbeError("Catalog contains inline style content")
    if parser.meta_refresh:
        raise ProbeError("Catalog contains a meta refresh redirect")
    if parser.active_resource_tags:
        raise ProbeError("Catalog contains an unapproved active resource element")
    if parser.inert_containers:
        raise ProbeError("Catalog contains an inert container that can hide active content")
    if parser.head_elements != 1 or parser.csp_outside_head:
        raise ProbeError("Catalog CSP must appear in the single document head")
    if parser.unapproved_links:
        raise ProbeError("Catalog contains an unapproved link relationship")
    validate_csp(parser.csp_values)

    references = parser.hrefs + parser.script_sources + parser.stylesheets + parser.icons
    if any(
        not reference
        or any(ord(character) <= 32 or character == "\\" for character in reference)
        for reference in references
    ):
        raise ProbeError("Catalog contains an unsafe URL reference")
    lowered_hrefs = [href.lower() for href in parser.hrefs]
    for domain in excluded_domains:
        if any(domain.lower() in href for href in lowered_hrefs):
            raise ProbeError(f"Held domain is linked from the catalog: {domain}")
    if any(href.startswith("mailto:") for href in lowered_hrefs):
        raise ProbeError("Review catalog contains a live email inquiry link")
    if any(href.startswith(("data:", "javascript:")) for href in lowered_hrefs):
        raise ProbeError("Review catalog contains an active URL scheme")
    if any(marker in href for href in lowered_hrefs for marker in PAYMENT_HOST_MARKERS):
        raise ProbeError("Review catalog contains a payment or checkout link")

    if parser.script_sources != [EXPECTED_SCRIPT]:
        raise ProbeError(
            "Catalog scripts do not match the exact source allowlist: "
            + ", ".join(parser.script_sources)
        )
    if parser.stylesheets != ["assets/site.css"]:
        raise ProbeError("Catalog stylesheet does not match the exact source allowlist")
    if parser.icons != ["assets/favicon.svg"]:
        raise ProbeError("Catalog icon does not match the exact source allowlist")

    return {
        "title": title,
        "catalog_links": len(catalog_links),
        "expected_domains": sorted(allowed_domains),
        "capture_controls": 0,
        "mailto_links": 0,
        "scripts": parser.script_sources,
        "stylesheets": parser.stylesheets,
        "csp_meta": True,
    }


def fetch_catalog(url: str, *, timeout: float) -> tuple[bytes, dict]:
    approved_url(url)
    request = Request(
        url,
        headers={
            "Accept": "text/html",
            "User-Agent": "illnetwork-review-verifier/1.0",
        },
    )
    try:
        opener = build_opener(ApprovedRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            final_url = approved_url(response.geturl())
            content_type = response.headers.get_content_type()
            content_length = response.headers.get("Content-Length")
            if status != 200:
                raise ProbeError(f"Endpoint returned HTTP {status}")
            if content_type != "text/html":
                raise ProbeError(f"Endpoint returned {content_type}, not text/html")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError as exc:
                    raise ProbeError("Endpoint returned an invalid Content-Length") from exc
                if declared_size > MAX_RESPONSE_BYTES:
                    raise ProbeError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except ProbeError:
        raise
    except HTTPError as exc:
        raise ProbeError(f"Endpoint returned HTTP {exc.code}") from exc
    except (OSError, TimeoutError, URLError) as exc:
        raise ProbeError(f"Endpoint request failed: {exc}") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProbeError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes")
    return body, {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "response_bytes": len(body),
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--url", default=DEFAULT_URL)
    command.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("sites.json")
    )
    command.add_argument("--timeout", type=float, default=20.0)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if not 1 <= args.timeout <= 60:
            raise ProbeError("timeout must be between 1 and 60 seconds")
        allowed, excluded = load_domains(args.config)
        html, result = fetch_catalog(args.url, timeout=args.timeout)
        result.update(
            validate_catalog(
                html,
                source_url=result["final_url"],
                allowed_domains=allowed,
                excluded_domains=excluded,
            )
        )
    except ProbeError as exc:
        print(f"Review probe failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
