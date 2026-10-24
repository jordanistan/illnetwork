#!/usr/bin/env python3
"""Audit the fixed Pawsfect public email handoff without sending a message."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

from portfolio.pawsfect_public_audit import (
    BUNDLE_LIMIT,
    ROOT_LIMIT,
    ROOT_URL,
    fetch_url,
    verify_root,
)


APPROVED_RECIPIENT = "jordan.robison@gmail.com"
UNCONFIGURED_ALIAS = "hello@pawsfectwalks.com"
REQUIRED = (
    "Waitlist request",
    "Partnership%20inquiry",
    "General interest:",
    "Do not send addresses, access codes, payment details, IDs, or medical records.",
    "Submitting opens your email app; this site does not store the form.",
)
PROHIBITED = (
    UNCONFIGURED_ALIAS,
    "formspree",
    "XMLHttpRequest",
    "localStorage",
    "sessionStorage",
    "booking confirmed",
    "checkout",
)
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAILTO = re.compile(r"mailto:([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)


class InquiryAuditError(RuntimeError):
    """The live inquiry handoff crossed its reviewed boundary."""


def verify_bundle(data: bytes) -> str:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InquiryAuditError("module response is not strict UTF-8") from exc

    for marker in REQUIRED:
        if marker not in text:
            raise InquiryAuditError(f"missing inquiry boundary: {marker}")
    for marker in PROHIBITED:
        if marker.casefold() in text.casefold():
            raise InquiryAuditError(f"prohibited inquiry marker: {marker}")

    addresses = {address.casefold() for address in EMAIL.findall(text)}
    if addresses != {APPROVED_RECIPIENT, "john@example.com"}:
        raise InquiryAuditError(f"unexpected public email inventory: {sorted(addresses)}")
    recipients = [recipient.casefold() for recipient in MAILTO.findall(text)]
    if len(recipients) < 3 or set(recipients) != {APPROVED_RECIPIENT}:
        raise InquiryAuditError("every mailto must use the reviewed recipient")
    return hashlib.sha256(data).hexdigest()


def run(opener=None) -> tuple[int, int, str]:
    root = fetch_url(
        ROOT_URL,
        expected_types={"text/html"},
        limit=ROOT_LIMIT,
        kind="root",
        opener=opener,
    )
    module_url = verify_root(root)
    bundle = fetch_url(
        module_url,
        expected_types={"application/javascript", "text/javascript"},
        limit=BUNDLE_LIMIT,
        kind="asset",
        opener=opener,
    )
    return len(root), len(bundle), verify_bundle(bundle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the fixed public Pawsfect email handoff without sending email."
    )
    parser.parse_args(argv)
    root_bytes, bundle_bytes, digest = run()
    print(
        "Pawsfect inquiry audit passed: "
        f"root_bytes={root_bytes}; bundle_bytes={bundle_bytes}; bundle_sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
