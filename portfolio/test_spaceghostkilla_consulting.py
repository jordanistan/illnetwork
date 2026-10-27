import json
import os
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "spaceghostkilla_consulting", ROOT / "spaceghostkilla_consulting.py"
)
CONSULTING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSULTING)


def evidence():
    return json.loads(CONSULTING.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def write_text(directory, text, name="value.json"):
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


def write_json(directory, value, name="value.json"):
    return write_text(directory, json.dumps(value), name)


def verify_gate(value, index, timestamp=None):
    gate_id, roles, _ = CONSULTING.GATES[index]
    item = value["gates"][index]
    assert item["id"] == gate_id
    item.update({
        "status": "verified",
        "checked_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "reviewer_role": sorted(roles)[0],
        "private_evidence_recorded": True,
        "notes": CONSULTING.VERIFIED_NOTE,
    })


class SpaceGhostKillaConsultingTests(unittest.TestCase):
    def assert_rejected(self, value):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                CONSULTING.validate_evidence(write_json(directory, value))

    def test_pending_template_passes_without_readiness_claim(self):
        result = CONSULTING.validate_evidence()
        self.assertFalse(result["p004_global_requirements_complete"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_source_offer_and_engagement_boundaries_are_fixed(self):
        mutations = []
        item = evidence(); item["project"] = "SpaceGhostKilla ready"; mutations.append(item)
        item = evidence(); item["source_repository"] = "example/repo"; mutations.append(item)
        item = evidence(); item["native_source_commit"] = "a" * 40; mutations.append(item)
        item = evidence(); item["source_paths"].pop(); mutations.append(item)
        item = evidence(); item["coordinator_issue"] = 30; mutations.append(item)
        item = evidence(); item["proposed_offer"]["status"] = "approved"; mutations.append(item)
        item = evidence(); item["engagement_boundary"]["status"] = "authorized"; mutations.append(item)
        item = evidence(); item["per_engagement_authorization_required"] = False; mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_root_schema_integer_and_boolean_types_are_strict(self):
        mutations = []
        item = evidence(); item["extra"] = False; mutations.append(item)
        item = evidence(); item["version"] = True; mutations.append(item)
        item = evidence(); item["coordinator_issue"] = True; mutations.append(item)
        item = evidence(); item["p004_global_requirements_complete"] = 0; mutations.append(item)
        item = evidence(); item["gates"] = {}; mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_gate_identity_order_and_fields_are_strict(self):
        mutations = []
        item = evidence(); item["gates"][0], item["gates"][1] = item["gates"][1], item["gates"][0]; mutations.append(item)
        item = evidence(); item["gates"][0]["id"] = "other"; mutations.append(item)
        item = evidence(); item["gates"][0]["evidence_reference"] = "private"; mutations.append(item)
        item = evidence(); item["gates"].pop(); mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_duplicate_keys_constants_large_files_and_leaf_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, text in (("duplicate.json", '{"version":1,"version":1}'), ("constant.json", '{"value":NaN}')):
                with self.subTest(name=name):
                    with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                        CONSULTING.validate_evidence(write_text(directory, text, name))
            large = write_text(directory, " " * 65_537, "large.json")
            with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                CONSULTING.validate_evidence(large)
            target = write_text(directory, "{}", "target.json")
            link = Path(directory) / "link.json"
            os.symlink(target, link)
            with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                CONSULTING.validate_evidence(link)

    def test_symlink_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real"
            real.mkdir()
            value = write_json(real, evidence())
            link = Path(directory) / "linked"
            os.symlink(real, link)
            with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                CONSULTING.validate_evidence(link / value.name)

    def test_invalid_utf8_and_non_object_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_bytes(b"\xff")
            with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                CONSULTING.validate_evidence(invalid)
            for value in ([], None, "text"):
                with self.subTest(value=value):
                    with self.assertRaises(CONSULTING.ConsultingEvidenceError):
                        CONSULTING.validate_evidence(write_json(directory, value, f"{type(value).__name__}.json"))

    def test_pending_gate_cannot_claim_review(self):
        for key, changed in (
            ("checked_at", "2026-10-27T12:00:00Z"),
            ("reviewer_role", "owner"),
            ("private_evidence_recorded", True),
            ("notes", "Done"),
        ):
            value = evidence()
            value["gates"][0][key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_verified_gate_requires_role_evidence_timestamp_and_fixed_note(self):
        for key, changed in (
            ("reviewer_role", "owner"),
            ("private_evidence_recorded", False),
            ("checked_at", ""),
            ("checked_at", "2026-10-27T12:00:00"),
            ("checked_at", "2999-01-01T00:00:00Z"),
            ("notes", "Approved."),
        ):
            value = evidence()
            verify_gate(value, 0)
            value["gates"][0][key] = changed
            with self.subTest(key=key):
                self.assert_rejected(value)

    def test_dependencies_and_timestamp_order_are_enforced(self):
        value = evidence(); verify_gate(value, 1); self.assert_rejected(value)
        value = evidence(); verify_gate(value, 2); self.assert_rejected(value)
        value = evidence()
        verify_gate(value, 0, "2026-10-27T12:00:00Z")
        verify_gate(value, 1, "2026-10-27T11:00:00Z")
        self.assert_rejected(value)
        value = evidence()
        for index in range(3):
            verify_gate(value, index)
        verify_gate(value, 4)
        self.assert_rejected(value)

    def test_partial_verified_progress_is_allowed_but_not_complete(self):
        value = evidence()
        verify_gate(value, 0)
        with tempfile.TemporaryDirectory() as directory:
            result = CONSULTING.validate_evidence(write_json(directory, value))
        self.assertFalse(result["p004_global_requirements_complete"])
        self.assertEqual("verified", result["statuses"]["outside_work_boundaries"])

    def test_sensitive_and_held_content_are_rejected(self):
        samples = (
            "person@example.com", "512-555-1212", "123-45-6789",
            "4111 1111 1111 1111", "client_name=ACME", "invoice id=ABC1234",
            "secret=abc123", "ghp_abcdefghijklmnopqrstuvwxyz", "sxswasted.com",
        )
        for sample in samples:
            value = evidence()
            value["gates"][0]["notes"] = sample
            with self.subTest(sample=sample):
                self.assert_rejected(value)

    def test_incomplete_record_cannot_claim_owner_approval(self):
        value = evidence()
        value["owner_global_approved_at"] = datetime.now(timezone.utc).isoformat()
        self.assert_rejected(value)
        value = evidence()
        value["p004_global_requirements_complete"] = True
        self.assert_rejected(value)

    def test_p027_never_authorizes_external_or_commercial_actions(self):
        for key in CONSULTING.PERMANENT_FALSE_FIELDS:
            for changed in (True, 1, "false"):
                value = evidence()
                value[key] = changed
                with self.subTest(key=key, changed=changed):
                    self.assert_rejected(value)

    def test_complete_global_shape_passes_without_engagement_or_launch_authority(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index)
        value.update({
            "p004_global_requirements_complete": True,
            "owner_global_approved_at": datetime.now(timezone.utc).isoformat(),
        })
        with tempfile.TemporaryDirectory() as directory:
            result = CONSULTING.validate_evidence(write_json(directory, value))
        self.assertTrue(result["p004_global_requirements_complete"])
        self.assertTrue(value["per_engagement_authorization_required"])
        for key in CONSULTING.PERMANENT_FALSE_FIELDS:
            self.assertFalse(value[key])

    def test_owner_approval_is_current_and_after_final_gate(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index, "2026-10-27T12:00:00Z")
        value.update({
            "p004_global_requirements_complete": True,
            "owner_global_approved_at": "2026-10-27T11:59:59Z",
        })
        self.assert_rejected(value)
        value["owner_global_approved_at"] = "2999-01-01T00:00:00Z"
        self.assert_rejected(value)
        value["owner_global_approved_at"] = "2026-10-27T12:00:01Z"
        with tempfile.TemporaryDirectory() as directory:
            result = CONSULTING.validate_evidence(write_json(directory, value))
        self.assertTrue(result["p004_global_requirements_complete"])

    def test_cli_invalid_input_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = write_text(directory, "{}")
            result = subprocess.run(
                [sys.executable, str(ROOT / "spaceghostkilla_consulting.py"), "--path", str(bad)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn("validation failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
