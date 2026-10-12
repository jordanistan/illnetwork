import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("hosting_preflight", ROOT / "hosting_preflight.py")
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def target(domain="pawsfectwalks.com"):
    return next(item for item in PREFLIGHT.EXPECTED_TARGETS if item["domain"] == domain)


def valid_html(site):
    return (
        "<!doctype html><html><head><link rel=\"canonical\" href=\""
        + site["canonical_url"]
        + "\"><title>"
        + site["identity_text"]
        + "</title></head><body><p>"
        + site["required_notice"]
        + "</p><a href=\"mailto:"
        + site["inquiry_email"]
        + "?subject="
        + site["inquiry_subject"].replace(" ", "+")
        + "\">Contact</a><link rel=\"stylesheet\" href=\""
        + site["stylesheet_source"]
        + "\"><script src=\""
        + site["script_source"]
        + "\"></script></body></html>"
    )


def headers_text(site):
    required = PREFLIGHT.expected_headers(site["domain"])
    return site["headers_rule"] + "\n" + "".join(
        f"  {name}: {value}\n" for name, value in required.items()
    )


def make_artifact(directory, site, html=None, headers=None):
    root = Path(directory)
    for name in site["allowed_files"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    (root / site["entrypoint"]).write_text(html or valid_html(site), encoding="utf-8")
    (root / "_headers").write_text(headers or headers_text(site), encoding="utf-8")
    return root


def pending_evidence():
    return {
        "version": 1,
        "cutover_approved": False,
        "owner_approval_date": None,
        "targets": [
            {
                "domain": item["domain"], "status": "pending", "staging_url": "",
                "production_url": "", "deployment_sha": "", "checked_at": "",
                "http_200": False, "headers_verified": False,
                "inquiry_link_verified": False, "inbox_receipt_verified": False,
                "dns_snapshot_reviewed": False, "rollback_recorded": False,
                "notes": "Pending owner action.",
            }
            for item in PREFLIGHT.EXPECTED_TARGETS
        ],
    }


class HostingPreflightTests(unittest.TestCase):
    def test_reviewed_manifest_matches_fixed_two_targets(self):
        loaded = PREFLIGHT.load_manifest(PREFLIGHT.DEFAULT_MANIFEST)
        self.assertEqual(["pawsfectwalks.com", "spaceghostkilla.com"], [x["domain"] for x in loaded])

    def test_manifest_rejects_added_or_held_target(self):
        for domain in ("iambirdy.com", "sxswasted.com"):
            with self.subTest(domain=domain), tempfile.TemporaryDirectory() as directory:
                manifest = {"version": 1, "targets": PREFLIGHT.EXPECTED_TARGETS + [{"domain": domain}]}
                path = Path(directory) / "manifest.json"
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.load_manifest(path)

    def test_both_reviewed_artifact_shapes_pass(self):
        for domain in ("pawsfectwalks.com", "spaceghostkilla.com"):
            with self.subTest(domain=domain), tempfile.TemporaryDirectory() as directory:
                result = PREFLIGHT.validate_artifact(make_artifact(directory, target(domain)), target(domain))
                self.assertEqual("artifact_ready_for_staging_review", result["status"])

    def test_form_checkout_and_active_html_are_rejected(self):
        unsafe = (
            "<form></form>", '<select name="lead"></select>',
            "<a data-checkout=\"x\">buy</a>",
            "<script>fetch('/send')</script>", '<body onload="send()">',
            "<style>body{display:none}</style>", '<div style="display:none">x</div>',
            '<base href="https://evil.example/">',
            '<meta http-equiv="refresh" content="0;url=https://evil.example/">',
        )
        for markup in unsafe:
            with self.subTest(markup=markup), tempfile.TemporaryDirectory() as directory:
                site = target()
                html = valid_html(site).replace("</body>", markup + "</body>")
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)

    def test_external_scripts_and_payment_links_are_rejected(self):
        unsafe = (
            '<script src="https://evil.example/app.js"></script>',
            '<script src=" https://evil.example/app.js"></script>',
            '<script src="other.js"></script>',
            '<link rel="preconnect" href="https://evil.example">',
            '<link rel="stylesheet" href="other.css">',
            '<img src="https://evil.example/pixel">',
            '<iframe src="https://evil.example/"></iframe>',
            '<a href="https://checkout.stripe.com/demo">Pay</a>',
            '<a href="javascript:alert(1)">Run</a>',
        )
        for markup in unsafe:
            with self.subTest(markup=markup), tempfile.TemporaryDirectory() as directory:
                site = target()
                html = valid_html(site).replace("</body>", markup + "</body>")
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)

    def test_wrong_or_missing_inquiry_email_is_rejected(self):
        site = target()
        for html in (valid_html(site).replace(site["inquiry_email"], "wrong@example.test"), valid_html(site).replace("mailto:", "https://")):
            with self.subTest(html=html), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)

    def test_missing_or_weakened_headers_are_rejected(self):
        site = target()
        variants = (
            "",
            headers_text(site).replace("  x-frame-options: DENY\n", ""),
            headers_text(site).replace("default-src 'none'", "default-src *"),
        )
        for value in variants:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = make_artifact(directory, site)
                (root / "_headers").write_text(value, encoding="utf-8")
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(root, site)

    def test_overlapping_header_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            site = target("spaceghostkilla.com")
            headers = headers_text(site) + "/*\n  Content-Security-Policy: default-src *\n"
            with self.assertRaisesRegex(PREFLIGHT.PreflightError, "unreviewed"):
                PREFLIGHT.validate_artifact(
                    make_artifact(directory, site, headers=headers), site
                )

    def test_symlink_artifact_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            site = target()
            root = make_artifact(directory, site)
            (root / "linked").symlink_to(root / site["entrypoint"])
            with self.assertRaisesRegex(PREFLIGHT.PreflightError, "symlink"):
                PREFLIGHT.validate_artifact(root, site)

    def test_unreviewed_artifact_files_are_rejected(self):
        for name in (".env", "_worker.js", "functions/services.js"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                site = target()
                root = make_artifact(directory, site)
                extra = root / name
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("unexpected", encoding="utf-8")
                with self.assertRaisesRegex(PREFLIGHT.PreflightError, "file set"):
                    PREFLIGHT.validate_artifact(root, site)

    def test_mailto_query_must_be_single_reviewed_subject(self):
        site = target()
        reviewed = site["inquiry_subject"].replace(" ", "+")
        for query in (
            "bcc=evil@example.test", f"subject={reviewed}&subject=Second",
            f"subject={reviewed}&body=Unexpected",
        ):
            with self.subTest(query=query), tempfile.TemporaryDirectory() as directory:
                html = valid_html(site).replace(f"subject={reviewed}", query)
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)

    def test_held_domains_and_inert_notice_containers_are_rejected(self):
        site = target()
        for domain in sorted(PREFLIGHT.HELD_DOMAINS):
            encoded = domain.replace(".", "&#46;")
            for reference in (domain, encoded):
                with self.subTest(domain=domain, reference=reference), tempfile.TemporaryDirectory() as directory:
                    html = valid_html(site).replace("</body>", f'<a href="https://{reference}">held</a></body>')
                    with self.assertRaises(PREFLIGHT.PreflightError):
                        PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)
        for tag in ("template", "noscript"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                html = valid_html(site).replace(
                    f"<p>{site['required_notice']}</p>",
                    f"<{tag}>{site['required_notice']}</{tag}>",
                )
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.validate_artifact(make_artifact(directory, site, html=html), site)

    def test_held_domain_in_other_deployable_text_is_rejected(self):
        site = target()
        for content in (
            "https://sxswasted&#46;com/", "https://sxswasted%2Ecom/",
            r"https://sxswasted\x2ecom/",
        ):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = make_artifact(directory, site)
                (root / site["script_source"]).write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(PREFLIGHT.PreflightError, "held domain"):
                    PREFLIGHT.validate_artifact(root, site)
        with tempfile.TemporaryDirectory() as directory:
            root = make_artifact(directory, site)
            (root / "assets/hero.svg").write_text(
                '<svg><a href="https://sxswasted.com/">held</a></svg>', encoding="utf-8"
            )
            with self.assertRaisesRegex(PREFLIGHT.PreflightError, "held domain"):
                PREFLIGHT.validate_artifact(root, site)

    def test_pending_evidence_template_passes_without_claiming_completion(self):
        result = PREFLIGHT.validate_evidence(PREFLIGHT.DEFAULT_EVIDENCE)
        self.assertFalse(result["cutover_approved"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_pending_evidence_cannot_contain_success_claims(self):
        evidence = pending_evidence()
        evidence["targets"][0]["headers_verified"] = True
        self.assert_evidence_rejected(evidence)

    def test_staging_evidence_requires_https_pages_host_full_sha_and_checks(self):
        for key, value in (
            ("staging_url", "http://demo.pages.dev"),
            ("staging_url", "https://evil.example"),
            ("staging_url", "https://p005-review.pages.dev/path"),
            ("deployment_sha", "abc123"),
            ("checked_at", "2026-10-12"),
            ("headers_verified", False),
        ):
            evidence = pending_evidence()
            evidence["targets"][0].update(self.verified_fields())
            evidence["targets"][0][key] = value
            self.assert_evidence_rejected(evidence)

    def test_cutover_requires_exact_production_url(self):
        evidence = pending_evidence()
        evidence["targets"][0].update(self.verified_fields(status="cutover_verified"))
        evidence["targets"][0]["production_url"] = "https://example.test/"
        self.assert_evidence_rejected(evidence)

    def test_overall_approval_requires_both_cutovers_and_date(self):
        evidence = pending_evidence()
        evidence["cutover_approved"] = True
        evidence["owner_approval_date"] = "2026-10-12"
        self.assert_evidence_rejected(evidence)

    def test_complete_two_target_evidence_passes(self):
        evidence = pending_evidence()
        for index, item in enumerate(evidence["targets"]):
            item.update(self.verified_fields(status="cutover_verified", host=f"p005-{index}"))
            item["production_url"] = f'https://{item["domain"]}/'
        evidence["cutover_approved"] = True
        evidence["owner_approval_date"] = "2026-10-12"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            self.assertTrue(PREFLIGHT.validate_evidence(path)["cutover_approved"])

    def test_verified_targets_require_distinct_staging_hosts(self):
        evidence = pending_evidence()
        for item in evidence["targets"]:
            item.update(self.verified_fields())
        self.assert_evidence_rejected(evidence)

    def test_future_timestamp_is_rejected(self):
        evidence = pending_evidence()
        evidence["targets"][0].update(self.verified_fields())
        evidence["targets"][0]["checked_at"] = "2999-01-01T00:00:00Z"
        self.assert_evidence_rejected(evidence)

    def test_future_owner_approval_date_is_rejected(self):
        evidence = pending_evidence()
        for index, item in enumerate(evidence["targets"]):
            item.update(self.verified_fields(status="cutover_verified", host=f"p005-{index}"))
            item["production_url"] = f'https://{item["domain"]}/'
        evidence["cutover_approved"] = True
        evidence["owner_approval_date"] = "2999-01-01"
        self.assert_evidence_rejected(evidence)

    def test_held_domain_in_evidence_is_rejected(self):
        evidence = pending_evidence()
        evidence["targets"][0]["notes"] = "See sxswasted.com"
        self.assert_evidence_rejected(evidence)

    def verified_fields(self, status="staging_verified", host="p005-review"):
        return {
            "status": status,
            "staging_url": f"https://{host}.pages.dev/",
            "deployment_sha": "a" * 40,
            "checked_at": "2026-10-12T18:00:00-05:00",
            "http_200": True,
            "headers_verified": True,
            "inquiry_link_verified": True,
            "inbox_receipt_verified": True,
            "dns_snapshot_reviewed": True,
            "rollback_recorded": True,
        }

    def assert_evidence_rejected(self, evidence):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaises(PREFLIGHT.PreflightError):
                PREFLIGHT.validate_evidence(path)


if __name__ == "__main__":
    unittest.main()
