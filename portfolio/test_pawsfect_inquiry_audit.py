#!/usr/bin/env python3
"""Offline tests for the fixed Pawsfect public inquiry handoff."""

from pathlib import Path
import unittest

from portfolio.pawsfect_inquiry_audit import (
    APPROVED_RECIPIENT,
    InquiryAuditError,
    PROHIBITED,
    REQUIRED,
    verify_bundle,
)


def safe_bundle() -> bytes:
    text = ";".join(REQUIRED) + ";john@example.com;" + ";".join(
        f"mailto:{APPROVED_RECIPIENT}?subject=test" for _ in range(3)
    )
    return text.encode()


class InquiryBoundaryTests(unittest.TestCase):
    def test_reviewed_handoff_passes(self) -> None:
        self.assertEqual(len(verify_bundle(safe_bundle())), 64)

    def test_every_required_boundary_is_required(self) -> None:
        text = safe_bundle().decode()
        for marker in REQUIRED:
            with self.subTest(marker=marker), self.assertRaises(InquiryAuditError):
                verify_bundle(text.replace(marker, "").encode())

    def test_every_prohibited_marker_is_rejected(self) -> None:
        for marker in PROHIBITED:
            with self.subTest(marker=marker), self.assertRaises(InquiryAuditError):
                verify_bundle(safe_bundle() + marker.encode())

    def test_recipient_drift_and_extra_email_are_rejected(self) -> None:
        source = safe_bundle().decode()
        for changed in (
            source.replace(APPROVED_RECIPIENT, "other@example.com"),
            source + ";support@example.com",
            ";".join(REQUIRED) + f";john@example.com;mailto:{APPROVED_RECIPIENT}",
        ):
            with self.subTest(changed=changed), self.assertRaises(InquiryAuditError):
                verify_bundle(changed.encode())

    def test_invalid_utf8_is_rejected(self) -> None:
        with self.assertRaises(InquiryAuditError):
            verify_bundle(b"\xff")

    def test_live_workflow_is_trusted_main_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/pawsfect-inquiry-audit.yml").read_text()
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertEqual(workflow.count("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"), 2)
        self.assertEqual(workflow.count("persist-credentials: false"), 2)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("python3 -m portfolio.pawsfect_inquiry_audit", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("secrets.", workflow)


if __name__ == "__main__":
    unittest.main()
