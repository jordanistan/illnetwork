import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pawsfect_recruiting", ROOT / "pawsfect_recruiting.py")
RECRUITING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECRUITING)


def evidence():
    return json.loads(RECRUITING.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def write_text(directory, text):
    path = Path(directory) / "value.json"
    path.write_text(text, encoding="utf-8")
    return path


def write_json(directory, value):
    return write_text(directory, json.dumps(value))


def verify_gate(value, index, timestamp=None):
    gate_id, roles, _ = RECRUITING.GATES[index]
    item = value["gates"][index]
    assert item["id"] == gate_id
    item.update({
        "status": "verified",
        "checked_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "reviewer_role": sorted(roles)[0],
        "private_evidence_recorded": True,
        "notes": RECRUITING.VERIFIED_NOTE,
    })
    if gate_id == "pilot_role_scope":
        value["owner_attested_packet_sha"] = "a" * 40
    if gate_id == "pay_control_terms_reviewed":
        value["role_policy_version"] = "pawsfect-role-v1"


class PawsfectRecruitingTests(unittest.TestCase):
    def assert_rejected(self, value):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_evidence(write_json(directory, value))

    def test_reviewed_official_sources_pass(self):
        result = RECRUITING.validate_sources()
        self.assertEqual(4, result["sources"])

    def test_changed_source_register_is_rejected(self):
        value = json.loads(RECRUITING.DEFAULT_SOURCES.read_text(encoding="utf-8"))
        value["sources"][0]["url"] = "https://example.test/"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_sources(write_json(directory, value))

    def test_pending_template_passes_without_recruiting_claim(self):
        result = RECRUITING.validate_evidence()
        self.assertFalse(result["recruiting_approved"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_schema_order_and_types_are_strict(self):
        mutations = []
        item = evidence(); item["extra"] = False; mutations.append(item)
        item = evidence(); item["version"] = True; mutations.append(item)
        item = evidence(); item["pilot"]["target_walkers"] = "many"; mutations.append(item)
        item = evidence(); item["gates"][0], item["gates"][1] = item["gates"][1], item["gates"][0]; mutations.append(item)
        item = evidence(); item["gates"][0]["candidate_name"] = "redacted"; mutations.append(item)
        item = evidence(); item["gates"].pop(); mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_duplicate_keys_constants_large_files_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = write_text(directory, '{"version":1,"version":1}')
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_evidence(duplicate)
            constant = write_text(directory, '{"value":NaN}')
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_evidence(constant)
            large = write_text(directory, ' ' * 65_537)
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_evidence(large)
            target = Path(directory) / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = Path(directory) / "link.json"
            os.symlink(target, link)
            with self.assertRaises(RECRUITING.RecruitingError):
                RECRUITING.validate_evidence(link)

    def test_pending_gate_cannot_claim_review(self):
        for key, changed in (
            ("checked_at", "2026-10-15T10:00:00Z"),
            ("reviewer_role", "owner"),
            ("private_evidence_recorded", True),
            ("notes", "Done"),
        ):
            value = evidence()
            value["gates"][0][key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_verified_gate_requires_role_evidence_and_current_timestamp(self):
        for key, changed in (
            ("reviewer_role", "owner"),
            ("private_evidence_recorded", False),
            ("checked_at", ""),
            ("checked_at", "2999-01-01T00:00:00Z"),
            ("notes", "Qualified reviewer approved."),
        ):
            value = evidence()
            verify_gate(value, 0)
            value["gates"][0][key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_packet_sha_and_role_policy_follow_their_gates(self):
        value = evidence(); value["owner_attested_packet_sha"] = "a" * 40; self.assert_rejected(value)
        value = evidence(); verify_gate(value, 0); value["owner_attested_packet_sha"] = "short"; self.assert_rejected(value)
        value = evidence(); value["role_policy_version"] = "pawsfect-role-v1"; self.assert_rejected(value)
        value = evidence(); verify_gate(value, 0); verify_gate(value, 1); verify_gate(value, 2); value["role_policy_version"] = "draft"; self.assert_rejected(value)

    def test_dependencies_and_timestamp_order_are_enforced(self):
        value = evidence(); verify_gate(value, 1); self.assert_rejected(value)
        value = evidence()
        verify_gate(value, 0, "2026-10-15T12:00:00Z")
        verify_gate(value, 1, "2026-10-15T11:00:00Z")
        self.assert_rejected(value)

    def test_sensitive_and_held_content_are_rejected(self):
        samples = (
            "person@example.com", "512-555-1212", "123-45-6789",
            "4111 1111 1111 1111", "candidate_name=Someone",
            "driver license=TX123456", "bank=123456", "sxswasted.com",
        )
        for sample in samples:
            value = evidence()
            value["gates"][0]["notes"] = sample
            with self.subTest(sample=sample):
                self.assert_rejected(value)

    def test_unapproved_recruiting_cannot_claim_completion(self):
        for key, changed in (("owner_approval_date", "2026-10-15"),):
            value = evidence(); value[key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_p015_never_authorizes_hiring_dispatch_or_paid_launch(self):
        for key in ("hire_authorized", "dispatch_authorized", "paid_care_launch_ready"):
            for changed in (True, 1, "false"):
                value = evidence(); value[key] = changed
                with self.subTest(key=key, changed=changed):
                    self.assert_rejected(value)

    def test_approval_requires_every_gate_and_valid_completion_fields(self):
        value = evidence()
        value.update({
            "recruiting_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
        })
        self.assert_rejected(value)

    def test_complete_reviewed_shape_passes(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index)
        value.update({
            "recruiting_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
        })
        with tempfile.TemporaryDirectory() as directory:
            result = RECRUITING.validate_evidence(write_json(directory, value))
        self.assertTrue(result["recruiting_approved"])

    def test_completion_date_and_marker_are_strict(self):
        valid = evidence()
        for index in range(len(valid["gates"])):
            verify_gate(valid, index)
        valid.update({
            "recruiting_approved": True,
            "owner_approval_date": datetime.now(timezone.utc).date().isoformat(),
            "owner_attested_private_review_record": "private-ledger:PAWS-01",
        })
        for key, changed in (("owner_approval_date", "2999-01-01"),):
            value = copy.deepcopy(valid); value[key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_owner_approval_cannot_predate_final_gate(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index, "2026-10-15T12:00:00Z")
        value.update({
            "recruiting_approved": True,
            "owner_approval_date": "2026-10-14",
        })
        self.assert_rejected(value)


if __name__ == "__main__":
    unittest.main()
