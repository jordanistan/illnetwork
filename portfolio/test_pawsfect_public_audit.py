#!/usr/bin/env python3
"""Offline tests for the fixed Pawsfect public-boundary audit."""

from email.message import Message
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request

from portfolio.pawsfect_public_audit import (
    AuditError,
    BUNDLE_LIMIT,
    EXPECTED_DESCRIPTION,
    EXPECTED_TITLE,
    ExactRedirectHandler,
    PROHIBITED_MARKERS,
    P015_GATE_IDS,
    REQUIRED_BOUNDARIES,
    ROOT_LIMIT,
    ROOT_URL,
    fetch_url,
    run,
    validate_asset_url,
    validate_root_url,
    verify_bundle,
    verify_pending_gates,
    verify_root,
)


MODULE_PATH = "/assets/index-Test_123.js"
MODULE_URL = f"https://pawsfectwalks.com{MODULE_PATH}"


def valid_root(extra: str = "", body_extra: str = "") -> bytes:
    return f"""<!doctype html><html lang="en"><head>
<title>{EXPECTED_TITLE}</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{EXPECTED_DESCRIPTION}">
<meta property="og:title" content="{EXPECTED_TITLE}">
<meta property="og:description" content="{EXPECTED_DESCRIPTION}">
<meta property="og:url" content="{ROOT_URL}">
<meta property="og:type" content="website">
<link rel="canonical" href="{ROOT_URL}">
<script type="module" crossorigin src="{MODULE_PATH}"></script>
<link rel="stylesheet" crossorigin href="/assets/index-Test_123.css">
{extra}</head><body><div id="root">{body_extra}</div></body></html>""".encode()


def safe_bundle() -> bytes:
    return (";".join(REQUIRED_BOUNDARIES)).encode()


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        url: str,
        content_type: str,
        status: int = 200,
        content_length: str | None = None,
    ) -> None:
        self.status = status
        self._url = url
        self._stream = io.BytesIO(body)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        return None


class FakeOpener:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = iter(responses)
        self.requests: list[tuple[Request, int | float | None]] = []

    def open(self, request: Request, timeout=None):  # noqa: ANN001
        self.requests.append((request, timeout))
        return next(self.responses)


def write_gate_fixture(root: Path) -> None:
    state_path = root / ".github/portfolio/STATE.json"
    evidence_path = (
        root
        / ".github/portfolio/pawsfect-recruiting/P015_RECRUITING_EVIDENCE_TEMPLATE.json"
    )
    state_path.parent.mkdir(parents=True)
    evidence_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {"pawsfect_walks": {"launch_status": "not ready; seven confirmations pending"}}
        )
    )
    evidence_path.write_text(
        json.dumps(
            {
                "recruiting_approved": False,
                "hire_authorized": False,
                "dispatch_authorized": False,
                "paid_care_launch_ready": False,
                "gates": [
                    {"id": gate_id, "status": "pending"}
                    for gate_id in P015_GATE_IDS
                ],
            }
        )
    )


class EndpointTests(unittest.TestCase):
    def test_root_is_exact_https_without_url_extras(self) -> None:
        validate_root_url(ROOT_URL)
        invalid = [
            "http://pawsfectwalks.com/",
            "https://evil.example/",
            "https://user@pawsfectwalks.com/",
            "https://pawsfectwalks.com:443/",
            "https://pawsfectwalks.com/?source=test",
            "https://pawsfectwalks.com/#top",
            "https://pawsfectwalks.com/%2e%2e/",
            "https://pawsfectwalks.com/\\evil",
            "https://pawsfectwalks.com/ bad",
        ]
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(AuditError):
                validate_root_url(url)

    def test_asset_is_exact_same_origin_reviewed_path(self) -> None:
        validate_asset_url(MODULE_URL, MODULE_URL)
        invalid = [
            "https://evil.example/assets/index-Test_123.js",
            "https://pawsfectwalks.com:443/assets/index-Test_123.js",
            "https://pawsfectwalks.com/assets/../index-Test_123.js",
            "https://pawsfectwalks.com/assets/%69ndex-Test_123.js",
            "https://pawsfectwalks.com//assets/index-Test_123.js",
            "https://pawsfectwalks.com/assets/index-Test_123.js?x=1",
            "https://pawsfectwalks.com/assets/other.js",
        ]
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(AuditError):
                validate_asset_url(url, MODULE_URL)

    def test_redirects_revalidate_before_following(self) -> None:
        root_handler = ExactRedirectHandler(ROOT_URL, "root")
        request = Request(ROOT_URL)
        redirected = root_handler.redirect_request(
            request, None, 302, "Found", {}, ROOT_URL
        )
        self.assertEqual(redirected.full_url, ROOT_URL)
        with self.assertRaises(AuditError):
            root_handler.redirect_request(
                request, None, 302, "Found", {}, "https://evil.example/"
            )


class FetchTests(unittest.TestCase):
    def test_get_is_bounded_and_has_no_ambient_credentials(self) -> None:
        opener = FakeOpener(
            [FakeResponse(valid_root(), url=ROOT_URL, content_type="text/html")]
        )
        self.assertEqual(
            fetch_url(
                ROOT_URL,
                expected_types={"text/html"},
                limit=ROOT_LIMIT,
                kind="root",
                opener=opener,
            ),
            valid_root(),
        )
        request, timeout = opener.requests[0]
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 10)
        self.assertEqual(headers["accept-encoding"], "identity")
        for forbidden in ("authorization", "cookie", "referer"):
            self.assertNotIn(forbidden, headers)

    def test_status_type_final_url_and_declared_size_are_strict(self) -> None:
        cases = [
            FakeResponse(b"x", url=ROOT_URL, content_type="text/html", status=503),
            FakeResponse(b"x", url=ROOT_URL, content_type="application/json"),
            FakeResponse(b"x", url="https://evil.example/", content_type="text/html"),
            FakeResponse(
                b"x",
                url=ROOT_URL,
                content_type="text/html",
                content_length=str(ROOT_LIMIT + 1),
            ),
            FakeResponse(
                b"x", url=ROOT_URL, content_type="text/html", content_length="bad"
            ),
            FakeResponse(
                b"x", url=ROOT_URL, content_type="text/html", content_length="-1"
            ),
        ]
        for response in cases:
            with self.subTest(response=response), self.assertRaises(AuditError):
                fetch_url(
                    ROOT_URL,
                    expected_types={"text/html"},
                    limit=ROOT_LIMIT,
                    kind="root",
                    opener=FakeOpener([response]),
                )

    def test_streamed_limit_is_enforced(self) -> None:
        with self.assertRaises(AuditError):
            fetch_url(
                ROOT_URL,
                expected_types={"text/html"},
                limit=4,
                kind="root",
                opener=FakeOpener(
                    [FakeResponse(b"12345", url=ROOT_URL, content_type="text/html")]
                ),
            )


class RootTests(unittest.TestCase):
    def test_reviewed_root_returns_exact_module(self) -> None:
        self.assertEqual(verify_root(valid_root()), MODULE_URL)

    def test_active_and_ambiguous_root_content_is_rejected(self) -> None:
        extras = [
            '<base href="https://evil.example/">',
            '<meta http-equiv="refresh" content="0;url=https://evil.example">',
            '<form></form>',
            '<script>alert(1)</script>',
            '<script type="module" src="//evil.example/x.js"></script>',
            f'<script type="module" src="{MODULE_PATH}"></script>',
            '<link rel="preconnect" href="https://evil.example">',
            '<link rel="icon" href="https://evil.example/pixel.png">',
            '<link rel="stylesheet" href="https://evil.example/x.css">',
            '<style>@import "https://evil.example/x.css";</style>',
            '<img src="https://evil.example/pixel.png">',
            '<video src="https://evil.example/x.mp4"></video>',
            '<svg><use href="https://evil.example/x.svg#x"></use></svg>',
            '<div id="root" style="background:url(https://evil.example/x)"></div>',
            '<img src="x" onerror="alert(1)">',
            f'<script type="module" src="{MODULE_PATH}" src="/assets/index-Other.js"></script>',
        ]
        for extra in extras:
            with self.subTest(extra=extra), self.assertRaises(AuditError):
                verify_root(valid_root(extra))

    def test_root_metadata_and_visible_claims_are_prelaunch_only(self) -> None:
        old_claim = "Pawsfect Walks provides dependable dog walking and sitting services in Austin."
        with self.assertRaisesRegex(AuditError, "metadata crossed"):
            verify_root(valid_root().replace(EXPECTED_DESCRIPTION.encode(), old_claim.encode()))
        for claim in ("Booking confirmed", "Dog Sitting", "$50 per hour"):
            with self.subTest(claim=claim), self.assertRaises(AuditError):
                verify_root(valid_root(body_extra=claim))

    def test_title_canonical_and_utf8_are_strict(self) -> None:
        source = valid_root().decode()
        for data in [
            b"\xff",
            source.replace(EXPECTED_TITLE, "Changed").encode(),
            source.replace(ROOT_URL, "https://example.com/").encode(),
        ]:
            with self.subTest(data=data), self.assertRaises(AuditError):
                verify_root(data)


class BoundaryTests(unittest.TestCase):
    def test_safe_prelaunch_fixture_passes(self) -> None:
        self.assertEqual(len(verify_bundle(safe_bundle())), 64)

    def test_every_required_boundary_is_required(self) -> None:
        text = safe_bundle().decode()
        for marker in REQUIRED_BOUNDARIES:
            with self.subTest(marker=marker), self.assertRaises(AuditError):
                verify_bundle(text.replace(marker, "").encode())

    def test_every_prohibited_marker_fails_independently(self) -> None:
        for marker in PROHIBITED_MARKERS:
            with self.subTest(marker=marker), self.assertRaises(AuditError):
                verify_bundle(safe_bundle() + marker.encode())

    def test_boundary_matching_ignores_case_and_collapsed_whitespace(self) -> None:
        varied = safe_bundle().decode().replace(
            "Paid care is not available yet.",
            "PAID   CARE\nIS NOT AVAILABLE YET.",
        )
        self.assertEqual(len(verify_bundle(varied.encode())), 64)
        with self.assertRaisesRegex(AuditError, "Hiring now"):
            verify_bundle(safe_bundle() + b"hIrInG   NOW")

    def test_prices_booking_and_checkout_are_review_required(self) -> None:
        # Minified JavaScript capture variables such as ``$1`` are not prices.
        self.assertEqual(len(verify_bundle(safe_bundle() + b"const token='$1'")), 64)
        for marker in (
            "$50",
            "$22.00",
            "$9 per walk",
            "per hour",
            "Book now",
            "Booking confirmed",
            "Checkout",
            "Stripe",
            "coverage active",
            "care is available now",
        ):
            with self.subTest(marker=marker), self.assertRaises(AuditError):
                verify_bundle(safe_bundle() + marker.encode())

    def test_candidate_paths_are_rejected_even_when_dynamic_or_encoded(self) -> None:
        paths = (
            "Submit an application to hello@pawsfectwalks.com",
            "mailto:hello@pawsfectwalks.com?subject=Project%20Manager%20application",
            "mailto:hello@pawsfectwalks.com?subject=${encodeURIComponent(`${role.title} application`)}",
            "We are hiring walkers",
            "Become a walker",
            "Send a resume",
            "Explore careers",
        )
        for path in paths:
            with self.subTest(path=path), self.assertRaisesRegex(
                AuditError, "recruiting marker"
            ):
                verify_bundle(safe_bundle() + path.encode())

    def test_invalid_bundle_utf8_is_rejected(self) -> None:
        with self.assertRaises(AuditError):
            verify_bundle(b"\xff")


class GateTests(unittest.TestCase):
    def test_checked_in_pending_gates_match_audit_assumptions(self) -> None:
        verify_pending_gates(Path(__file__).resolve().parents[1])

    def test_any_changed_gate_requires_audit_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_gate_fixture(root)
            verify_pending_gates(root)
            evidence_path = (
                root
                / ".github/portfolio/pawsfect-recruiting/P015_RECRUITING_EVIDENCE_TEMPLATE.json"
            )
            evidence = json.loads(evidence_path.read_text())
            evidence["recruiting_approved"] = True
            evidence_path.write_text(json.dumps(evidence))
            with self.assertRaises(AuditError):
                verify_pending_gates(root)

    def test_gate_inventory_and_status_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_gate_fixture(root)
            evidence_path = (
                root
                / ".github/portfolio/pawsfect-recruiting/P015_RECRUITING_EVIDENCE_TEMPLATE.json"
            )
            original = json.loads(evidence_path.read_text())
            variants = []
            missing = json.loads(json.dumps(original))
            missing["gates"].pop()
            variants.append(missing)
            duplicate = json.loads(json.dumps(original))
            duplicate["gates"][-1]["id"] = duplicate["gates"][0]["id"]
            variants.append(duplicate)
            nonpending = json.loads(json.dumps(original))
            nonpending["gates"][0]["status"] = "verified"
            variants.append(nonpending)
            for evidence in variants:
                with self.subTest(evidence=evidence), self.assertRaises(AuditError):
                    evidence_path.write_text(json.dumps(evidence))
                    verify_pending_gates(root)

    def test_live_workflow_is_main_only(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/pawsfect-public-audit.yml"
        ).read_text()
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)

    def test_full_run_fetches_only_root_and_one_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_gate_fixture(root)
            opener = FakeOpener(
                [
                    FakeResponse(valid_root(), url=ROOT_URL, content_type="text/html"),
                    FakeResponse(
                        safe_bundle(),
                        url=MODULE_URL,
                        content_type="application/javascript",
                    ),
                ]
            )
            digest, root_bytes, bundle_bytes = run(root, opener=opener)
            self.assertEqual(len(digest), 64)
            self.assertEqual(root_bytes, len(valid_root()))
            self.assertEqual(bundle_bytes, len(safe_bundle()))
            self.assertEqual(
                [request.full_url for request, _ in opener.requests],
                [ROOT_URL, MODULE_URL],
            )
            self.assertEqual(BUNDLE_LIMIT, 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
