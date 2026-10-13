import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("starfield_release", ROOT / "starfield_release.py")
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


def evidence():
    return json.loads(RELEASE.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def write_json(directory, value):
    path = Path(directory) / "value.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def verify_gate(value, index):
    gate_id, roles, _ = RELEASE.GATES[index]
    item = value["gates"][index]
    assert item["id"] == gate_id
    item.update({
        "status": "verified",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_role": sorted(roles)[0],
        "evidence_recorded": True,
        "notes": RELEASE.VERIFIED_NOTE,
    })


class StarfieldReleaseTests(unittest.TestCase):
    def assert_rejected(self, value):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RELEASE.ReleaseError):
                RELEASE.validate_evidence(write_json(directory, value))

    def test_reviewed_official_sources_pass(self):
        result = RELEASE.validate_sources(RELEASE.DEFAULT_SOURCES)
        self.assertEqual(4, result["sources"])

    def test_changed_source_register_is_rejected(self):
        value = json.loads(RELEASE.DEFAULT_SOURCES.read_text(encoding="utf-8"))
        value["sources"][0]["url"] = "https://example.test/"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RELEASE.ReleaseError):
                RELEASE.validate_sources(write_json(directory, value))

    def test_pending_template_passes_without_release_claim(self):
        result = RELEASE.validate_evidence(RELEASE.DEFAULT_EVIDENCE)
        self.assertFalse(result["release_approved"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_gate_identity_order_and_unknown_fields_are_rejected(self):
        for mutation in ("order", "field", "missing"):
            value = evidence()
            if mutation == "order":
                value["gates"][0], value["gates"][1] = value["gates"][1], value["gates"][0]
            elif mutation == "field":
                value["gates"][0]["private_contract"] = "no"
            else:
                value["gates"].pop()
            with self.subTest(mutation=mutation):
                self.assert_rejected(value)

    def test_pending_gate_cannot_claim_review(self):
        for key, value in (
            ("checked_at", "2026-10-13T10:00:00Z"),
            ("checked_at", []),
            ("reviewer_role", "owner"),
            ("reviewer_role", []),
            ("evidence_recorded", True),
        ):
            item = evidence()
            item["gates"][0][key] = value
            with self.subTest(key=key):
                self.assert_rejected(item)

    def test_verified_gate_requires_role_evidence_and_date(self):
        for key, value in (
            ("reviewer_role", "owner"),
            ("evidence_recorded", False),
            ("checked_at", ""),
            ("checked_at", []),
            ("checked_at", "2999-01-01T00:00:00Z"),
        ):
            item = evidence()
            verify_gate(item, 0)
            item["gates"][0][key] = value
            with self.subTest(key=key, value=value):
                self.assert_rejected(item)

    def test_dependency_order_is_enforced(self):
        value = evidence()
        verify_gate(value, 1)
        self.assert_rejected(value)

    def test_dependency_timestamps_must_be_chronological(self):
        value = evidence()
        verify_gate(value, 0)
        verify_gate(value, 1)
        value["gates"][0]["checked_at"] = "2026-10-13T12:00:00Z"
        value["gates"][1]["checked_at"] = "2026-10-13T11:00:00Z"
        self.assert_rejected(value)

    def test_sensitive_and_held_content_are_rejected(self):
        samples = (
            "Contact private@example.com for review.",
            "api_key=abcdefghijklmnop",
            "Card 4111 1111 1111 1111 recorded.",
            "See sxswasted.com for details.",
        )
        for sample in samples:
            value = evidence()
            value["gates"][0]["notes"] = sample
            with self.subTest(sample=sample):
                self.assert_rejected(value)

    def test_public_notes_are_fixed_and_reject_sensitive_identifiers(self):
        for notes in (
            "Reviewed evidence is in a private ledger.",
            "AKIAIOSFODNN7EXAMPLE",
            "123-45-6789",
            "512-555-1212",
            "ORDER-12345",
        ):
            value = evidence()
            value["gates"][0]["notes"] = notes
            with self.subTest(notes=notes):
                self.assert_rejected(value)

    def test_unapproved_release_cannot_have_completion_fields(self):
        for key, value in (
            ("owner_approval_date", "2026-10-13"),
            ("catalog_version", "catalog-v1"),
            ("owner_attested_release_repository", "jordanistan/starfieldstudio"),
            ("owner_attested_release_sha", "a" * 40),
            ("owner_attested_checkout_record", "private-ledger:ABCDEF"),
        ):
            item = evidence()
            item[key] = value
            with self.subTest(key=key):
                self.assert_rejected(item)

    def test_approval_requires_all_gates(self):
        value = evidence()
        value["release_approved"] = True
        value["owner_approval_date"] = "2026-10-13"
        value["catalog_version"] = "catalog-v1"
        value["owner_attested_release_repository"] = "jordanistan/starfieldstudio"
        value["owner_attested_release_sha"] = "a" * 40
        value["owner_attested_checkout_record"] = "private-ledger:ABCDEF"
        self.assert_rejected(value)

    def test_complete_reviewed_shape_passes(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index)
        value.update({
            "release_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
            "catalog_version": "catalog-v1",
            "owner_attested_release_repository": "jordanistan/starfieldstudio",
            "owner_attested_release_sha": "a" * 40,
            "owner_attested_checkout_record": "private-ledger:STAR-01",
        })
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(RELEASE.validate_evidence(write_json(directory, value))["release_approved"])

    def test_completion_identifiers_are_strict(self):
        valid = evidence()
        for index in range(len(valid["gates"])):
            verify_gate(valid, index)
        valid.update({
            "release_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
            "catalog_version": "catalog-v1",
            "owner_attested_release_repository": "jordanistan/starfieldstudio",
            "owner_attested_release_sha": "a" * 40,
            "owner_attested_checkout_record": "private-ledger:STAR-01",
        })
        for key, value in (
            ("owner_approval_date", "2999-01-01"),
            ("catalog_version", "draft"),
            ("owner_attested_release_repository", "jordanistan/illnetwork"),
            ("owner_attested_release_sha", "abc123"),
            ("owner_attested_checkout_record", "https://private.example/order/1"),
        ):
            item = copy.deepcopy(valid)
            item[key] = value
            with self.subTest(key=key):
                self.assert_rejected(item)

    def test_owner_approval_cannot_predate_final_gate(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index)
            value["gates"][index]["checked_at"] = "2026-10-13T12:00:00Z"
        value.update({
            "release_approved": True,
            "owner_approval_date": "2026-10-12",
            "catalog_version": "catalog-v1",
            "owner_attested_release_repository": "jordanistan/starfieldstudio",
            "owner_attested_release_sha": "a" * 40,
            "owner_attested_checkout_record": "private-ledger:STAR-01",
        })
        self.assert_rejected(value)


if __name__ == "__main__":
    unittest.main()
