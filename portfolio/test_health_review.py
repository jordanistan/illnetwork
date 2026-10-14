import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("health_review", ROOT / "health_review.py")
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


def evidence():
    return json.loads(REVIEW.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def write_json(directory, value, name="value.json"):
    path = Path(directory) / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def verify_gate(value, index, timestamp=None):
    gate_id, roles, _ = REVIEW.GATES[index]
    item = value["gates"][index]
    assert item["id"] == gate_id
    item.update({
        "status": "verified",
        "checked_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "reviewer_role": sorted(roles)[0],
        "private_evidence_recorded": True,
        "notes": REVIEW.VERIFIED_NOTE,
    })


class HealthReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current_artifacts = REVIEW.build_artifact_records()

    def assert_rejected(self, value, current_artifacts=None):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(REVIEW.ReviewError):
                REVIEW.validate_evidence(
                    write_json(directory, value),
                    self.current_artifacts if current_artifacts is None else current_artifacts,
                )

    def inventory_verified(self):
        value = evidence()
        verify_gate(value, 0)
        value["owner_attested_reviewed_source_sha"] = "a" * 40
        value["reviewed_artifacts"] = copy.deepcopy(self.current_artifacts)
        return value

    def fully_verified(self):
        value = self.inventory_verified()
        for index in range(1, len(value["gates"])):
            verify_gate(value, index)
        return value

    def test_reviewed_official_sources_pass(self):
        self.assertEqual(4, REVIEW.validate_sources()["sources"])

    def test_changed_source_register_is_rejected(self):
        value = json.loads(REVIEW.DEFAULT_SOURCES.read_text(encoding="utf-8"))
        value["sources"][0]["url"] = "https://example.test/"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(REVIEW.ReviewError):
                REVIEW.validate_sources(write_json(directory, value))

    def test_content_inventory_has_exact_domains_and_artifact_digests(self):
        self.assertEqual(list(REVIEW.HEALTH_DOMAINS), [site["domain"] for site in REVIEW.health_content()])
        self.assertEqual(4, len(self.current_artifacts))
        self.assertEqual(
            [(domain, mode) for domain in REVIEW.HEALTH_DOMAINS for mode in REVIEW.MODES],
            [(item["domain"], item["mode"]) for item in self.current_artifacts],
        )
        for item in self.current_artifacts:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_missing_or_duplicate_health_domain_is_rejected(self):
        catalog = json.loads(REVIEW.DEFAULT_SITES.read_text(encoding="utf-8"))
        for mutation in ("missing", "duplicate"):
            value = copy.deepcopy(catalog)
            if mutation == "missing":
                value["sites"] = [site for site in value["sites"] if site.get("domain") != "hearty.fit"]
            else:
                value["sites"].append(next(site for site in value["sites"] if site.get("domain") == "hearty.fit"))
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(REVIEW.ReviewError):
                    REVIEW.health_content(write_json(directory, value, "sites.json"))

    def test_pending_template_passes_without_approval(self):
        result = REVIEW.validate_evidence(current_artifacts=self.current_artifacts)
        self.assertFalse(result["publication_approved"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_artifact_inventory_identity_order_and_fields_are_fixed(self):
        for mutation in ("order", "field", "domain", "missing"):
            value = evidence()
            if mutation == "order":
                value["reviewed_artifacts"][0], value["reviewed_artifacts"][1] = value["reviewed_artifacts"][1], value["reviewed_artifacts"][0]
            elif mutation == "field":
                value["reviewed_artifacts"][0]["path"] = "index.html"
            elif mutation == "domain":
                value["reviewed_artifacts"][0]["domain"] = "sxswasted.com"
            else:
                value["reviewed_artifacts"].pop()
            with self.subTest(mutation=mutation):
                self.assert_rejected(value)

    def test_gate_identity_order_and_unknown_fields_are_rejected(self):
        for mutation in ("order", "field", "missing"):
            value = evidence()
            if mutation == "order":
                value["gates"][0], value["gates"][1] = value["gates"][1], value["gates"][0]
            elif mutation == "field":
                value["gates"][0]["reviewer_name"] = "private"
            else:
                value["gates"].pop()
            with self.subTest(mutation=mutation):
                self.assert_rejected(value)

    def test_pending_gate_cannot_claim_review(self):
        for key, item_value in (
            ("checked_at", "2026-10-14T10:00:00Z"),
            ("reviewer_role", "qualified_health_professional"),
            ("private_evidence_recorded", True),
            ("notes", REVIEW.VERIFIED_NOTE),
        ):
            value = evidence()
            value["gates"][0][key] = item_value
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_verified_gate_requires_exact_role_evidence_date_and_note(self):
        for key, item_value in (
            ("reviewer_role", "owner"),
            ("private_evidence_recorded", False),
            ("checked_at", ""),
            ("checked_at", "2999-01-01T00:00:00Z"),
            ("notes", "Reviewed by a professional."),
        ):
            value = evidence()
            verify_gate(value, 0)
            value["gates"][0][key] = item_value
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_dependency_order_and_timestamps_are_enforced(self):
        value = evidence()
        verify_gate(value, 1)
        self.assert_rejected(value)

    def test_verified_inventory_requires_source_sha_and_current_artifacts(self):
        valid = self.inventory_verified()
        result = REVIEW.validate_evidence(
            write_json(tempfile.mkdtemp(), valid), self.current_artifacts
        )
        self.assertEqual("a" * 40, result["owner_attested_reviewed_source_sha"])
        for mutation in ("short-sha", "uppercase-sha", "stale-digest", "blank-digest"):
            value = copy.deepcopy(valid)
            if mutation == "short-sha":
                value["owner_attested_reviewed_source_sha"] = "abc123"
            elif mutation == "uppercase-sha":
                value["owner_attested_reviewed_source_sha"] = "A" * 40
            elif mutation == "stale-digest":
                value["reviewed_artifacts"][0]["sha256"] = "b" * 64
            else:
                value["reviewed_artifacts"][0]["sha256"] = ""
            with self.subTest(mutation=mutation):
                self.assert_rejected(value)

    def test_pending_inventory_rejects_source_or_artifact_claims(self):
        for mutation in ("source", "artifact"):
            value = evidence()
            if mutation == "source":
                value["owner_attested_reviewed_source_sha"] = "a" * 40
            else:
                value["reviewed_artifacts"][0]["sha256"] = "b" * 64
            with self.subTest(mutation=mutation):
                self.assert_rejected(value)

        value = evidence()
        verify_gate(value, 0, "2026-10-14T12:00:00Z")
        verify_gate(value, 1, "2026-10-14T11:00:00Z")
        self.assert_rejected(value)

    def test_sensitive_identifiers_are_rejected(self):
        samples = (
            "Contact reviewer@example.com",
            "api_key=abcdefghijklmnop",
            "Patient: ABC123",
            "MRN: 123456",
            "NPI=1234567890",
            "4111 1111 1111 1111",
        )
        for sample in samples:
            value = evidence()
            value["gates"][0]["notes"] = sample
            with self.subTest(sample=sample):
                self.assert_rejected(value)

    def test_unapproved_publication_cannot_have_completion_fields(self):
        for key, item_value in (("owner_approval_date", "2026-10-14"),):
            value = evidence()
            value[key] = item_value
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_approval_requires_all_gates(self):
        value = self.inventory_verified()
        value.update({
            "publication_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
        })
        self.assert_rejected(value)

    def test_complete_reviewed_shape_passes(self):
        value = self.fully_verified()
        value.update({
            "publication_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
        })
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(REVIEW.validate_evidence(
                write_json(directory, value), self.current_artifacts
            )["publication_approved"])

    def test_root_types_repository_and_future_date_are_strict(self):
        valid = self.fully_verified()
        valid.update({
            "publication_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
        })
        for key, item_value in (
            ("version", True),
            ("publication_approved", "true"),
            ("owner_approval_date", "2999-01-01"),
            ("source_repository", "jordanistan/healthyheart"),
        ):
            value = copy.deepcopy(valid)
            value[key] = item_value
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_owner_approval_cannot_predate_final_gate(self):
        value = self.inventory_verified()
        value["gates"][0]["checked_at"] = "2026-10-14T12:00:00Z"
        for index in range(1, len(value["gates"])):
            verify_gate(value, index, "2026-10-14T12:00:00Z")
        value.update({
            "publication_approved": True,
            "owner_approval_date": "2026-10-13",
        })
        self.assert_rejected(value)

    def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(self):
        for raw in ('{"version":1,"version":1}', '{"version":NaN}'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.json"
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(REVIEW.ReviewError):
                    REVIEW.read_json(path)

    def test_tree_digest_rejects_unexpected_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in REVIEW.EXPECTED_ARTIFACT_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            self.assertRegex(REVIEW.tree_digest(root), r"^[0-9a-f]{64}$")
            extra = root / "unexpected.txt"
            extra.write_text("no", encoding="utf-8")
            with self.assertRaises(REVIEW.ReviewError):
                REVIEW.tree_digest(root)
            extra.unlink()
            link = root / "link"
            link.symlink_to(root / "index.html")
            with self.assertRaises(REVIEW.ReviewError):
                REVIEW.tree_digest(root)
            link.unlink()
            (root / "empty").mkdir()
            with self.assertRaises(REVIEW.ReviewError):
                REVIEW.tree_digest(root)


if __name__ == "__main__":
    unittest.main()
