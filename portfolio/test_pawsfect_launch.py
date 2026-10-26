import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pawsfect_launch", ROOT / "pawsfect_launch.py")
LAUNCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCH)


def evidence():
    return json.loads(LAUNCH.DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def write_text(directory, text, name="value.json"):
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


def write_json(directory, value, name="value.json"):
    return write_text(directory, json.dumps(value), name)


def verify_gate(value, index, timestamp=None):
    gate_id, issue, roles, _ = LAUNCH.GATES[index]
    item = value["gates"][index]
    assert item["id"] == gate_id and item["issue"] == issue
    item.update({
        "status": "verified",
        "checked_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "reviewer_role": sorted(roles)[0],
        "private_evidence_recorded": True,
        "notes": LAUNCH.VERIFIED_NOTE,
    })


class PawsfectLaunchTests(unittest.TestCase):
    def assert_rejected(self, value):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(write_json(directory, value))

    def test_pending_template_passes_without_launch_claim(self):
        result = LAUNCH.validate_evidence()
        self.assertFalse(result["p003_operating_requirements_complete"])
        self.assertEqual({"pending"}, set(result["statuses"].values()))

    def test_project_source_issues_and_pilot_are_fixed(self):
        mutations = []
        item = evidence(); item["project"] = "Pawsfect Walks launch ready"; mutations.append(item)
        item = evidence(); item["source_repository"] = "example/repo"; mutations.append(item)
        item = evidence(); item["native_source_commit"] = "a" * 40; mutations.append(item)
        item = evidence(); item["coordinator_issues"] = [39, 40]; mutations.append(item)
        item = evidence(); item["proposed_pilot"]["status"] = "approved"; mutations.append(item)
        item = evidence(); item["proposed_pilot"]["included_services"].append("boarding"); mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_root_schema_and_boolean_types_are_strict(self):
        mutations = []
        item = evidence(); item["extra"] = False; mutations.append(item)
        item = evidence(); item["version"] = True; mutations.append(item)
        item = evidence(); item["p003_operating_requirements_complete"] = 0; mutations.append(item)
        item = evidence(); item["gates"] = {}; mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_gate_identity_issue_order_and_fields_are_strict(self):
        mutations = []
        item = evidence(); item["gates"][0], item["gates"][1] = item["gates"][1], item["gates"][0]; mutations.append(item)
        item = evidence(); item["gates"][0]["issue"] = 40; mutations.append(item)
        item = evidence(); item["gates"][0]["issue"] = True; mutations.append(item)
        item = evidence(); item["gates"][0]["evidence_reference"] = "private"; mutations.append(item)
        item = evidence(); item["gates"].pop(); mutations.append(item)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejected(value)

    def test_duplicate_keys_constants_large_files_and_leaf_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = write_text(directory, '{"version":1,"version":1}')
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(duplicate)
            constant = write_text(directory, '{"value":NaN}')
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(constant)
            large = write_text(directory, " " * 65_537)
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(large)
            target = write_text(directory, "{}", "target.json")
            link = Path(directory) / "link.json"
            os.symlink(target, link)
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(link)

    def test_symlink_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real"
            real.mkdir()
            value = write_json(real, evidence())
            link = Path(directory) / "linked"
            os.symlink(real, link)
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(link / value.name)

    def test_invalid_utf8_and_non_object_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_bytes(b"\xff")
            with self.assertRaises(LAUNCH.LaunchEvidenceError):
                LAUNCH.validate_evidence(invalid)
            for value in ([], None, "text"):
                with self.subTest(value=value):
                    with self.assertRaises(LAUNCH.LaunchEvidenceError):
                        LAUNCH.validate_evidence(write_json(directory, value, f"{type(value).__name__}.json"))

    def test_pending_gate_cannot_claim_review(self):
        for key, changed in (
            ("checked_at", "2026-10-26T12:00:00Z"),
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
            ("checked_at", "2026-10-26T12:00:00"),
            ("checked_at", "2999-01-01T00:00:00Z"),
            ("notes", "Coverage confirmed."),
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
        verify_gate(value, 1, "2026-10-26T12:00:00Z")
        verify_gate(value, 2, "2026-10-26T11:00:00Z")
        self.assert_rejected(value)
        value = evidence()
        verify_gate(value, 0)
        verify_gate(value, 1)
        verify_gate(value, 4)
        self.assert_rejected(value)

    def test_partial_verified_progress_is_allowed_but_not_complete(self):
        value = evidence()
        verify_gate(value, 0)
        with tempfile.TemporaryDirectory() as directory:
            result = LAUNCH.validate_evidence(write_json(directory, value))
        self.assertFalse(result["p003_operating_requirements_complete"])
        self.assertEqual("verified", result["statuses"]["insurance_and_ccc"])

    def test_sensitive_and_held_content_are_rejected(self):
        samples = (
            "person@example.com", "512-555-1212", "123-45-6789",
            "4111 1111 1111 1111", "policy number=ABC1234",
            "customer_name=Someone", "door code=1234", "sxswasted.com",
        )
        for sample in samples:
            value = evidence()
            value["gates"][0]["notes"] = sample
            with self.subTest(sample=sample):
                self.assert_rejected(value)

    def test_incomplete_record_cannot_claim_owner_approval(self):
        value = evidence()
        value["owner_operating_approved_at"] = datetime.now(timezone.utc).isoformat()
        self.assert_rejected(value)
        value = evidence()
        value["p003_operating_requirements_complete"] = True
        self.assert_rejected(value)

    def test_p026_never_authorizes_external_or_live_actions(self):
        for key in LAUNCH.PERMANENT_FALSE_FIELDS:
            for changed in (True, 1, "false"):
                value = evidence()
                value[key] = changed
                with self.subTest(key=key, changed=changed):
                    self.assert_rejected(value)

    def test_complete_reviewed_operating_shape_passes_without_launch_authority(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index)
        value.update({
            "p003_operating_requirements_complete": True,
            "owner_operating_approved_at": datetime.now(timezone.utc).isoformat(),
        })
        with tempfile.TemporaryDirectory() as directory:
            result = LAUNCH.validate_evidence(write_json(directory, value))
        self.assertTrue(result["p003_operating_requirements_complete"])
        for key in LAUNCH.PERMANENT_FALSE_FIELDS:
            self.assertFalse(value[key])

    def test_owner_approval_timestamp_is_current_and_after_final_gate(self):
        value = evidence()
        for index in range(len(value["gates"])):
            verify_gate(value, index, "2026-10-26T12:00:00Z")
        value.update({
            "p003_operating_requirements_complete": True,
            "owner_operating_approved_at": "2026-10-26T11:59:59Z",
        })
        self.assert_rejected(value)
        value["owner_operating_approved_at"] = "2999-01-01T00:00:00Z"
        self.assert_rejected(value)
        value["owner_operating_approved_at"] = "2026-10-26T12:00:01Z"
        with tempfile.TemporaryDirectory() as directory:
            result = LAUNCH.validate_evidence(write_json(directory, value))
        self.assertTrue(result["p003_operating_requirements_complete"])

    def test_cli_invalid_input_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = write_text(directory, "{}")
            result = subprocess.run(
                [sys.executable, str(ROOT / "pawsfect_launch.py"), "--path", str(bad)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn("validation failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
