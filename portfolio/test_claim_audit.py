import copy
import json
import tempfile
import unittest
from pathlib import Path

from portfolio.claim_audit import ClaimAuditError, audit, load_ledger, parse_remote_refs, release_command


SHA_A = "a" * 40
SHA_B = "b" * 40


def ledger_value():
    return {
        "schema_version": 1,
        "repository": "jordanistan/illnetwork",
        "claims": [
            {"task": "P001", "status": "active", "expected_sha": SHA_A, "issue": 1, "reason": "active task"},
            {"task": "P002", "status": "release_ready", "expected_sha": SHA_B, "issue": 2, "reason": "merged task"},
            {"task": "P003", "status": "released", "expected_sha": "", "issue": 3, "reason": "lease removed"},
        ],
    }


class ClaimAuditTests(unittest.TestCase):
    def write_ledger(self, value):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "claims.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_valid_ledger_and_exact_refs_produce_one_release_command(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        refs = parse_remote_refs(f"{SHA_A}\trefs/heads/claims/P001\n{SHA_B}\trefs/heads/claims/P002\n")
        result = audit(claims, refs)
        self.assertTrue(result["ok"])
        self.assertEqual([item["task"] for item in result["release_commands"]], ["P002"])
        self.assertIn(f"--force-with-lease=refs/heads/claims/P002:{SHA_B}", result["release_commands"][0]["command"])

    def test_active_and_owner_blocked_claims_never_receive_commands(self):
        value = ledger_value()
        value["claims"][1]["status"] = "retain_owner_blocked"
        claims = load_ledger(self.write_ledger(value))
        refs = parse_remote_refs(f"{SHA_A} refs/heads/claims/P001\n{SHA_B} refs/heads/claims/P002")
        result = audit(claims, refs)
        self.assertTrue(result["ok"])
        self.assertEqual(result["release_commands"], [])

    def test_changed_sha_blocks_release_command(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        result = audit(claims, {"P001": SHA_A, "P002": "c" * 40})
        self.assertFalse(result["ok"])
        self.assertEqual(result["release_commands"], [])
        self.assertIn({"task": "P002", "code": "sha_mismatch"}, result["errors"])

    def test_unknown_remote_claim_is_an_error(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        result = audit(claims, {"P001": SHA_A, "P002": SHA_B, "P999": "9" * 40})
        self.assertFalse(result["ok"])
        self.assertEqual(result["release_commands"], [])
        self.assertIn({"task": "P999", "code": "unknown_remote_claim"}, result["errors"])

    def test_missing_active_claim_is_an_error(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        result = audit(claims, {"P002": SHA_B})
        self.assertFalse(result["ok"])
        self.assertEqual(result["release_commands"], [])
        self.assertIn({"task": "P001", "code": "required_ref_missing"}, result["errors"])

    def test_absent_release_ready_claim_is_reported_as_already_released(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        result = audit(claims, {"P001": SHA_A})
        self.assertTrue(result["ok"])
        self.assertIn({"task": "P002", "state": "already_released"}, result["findings"])

    def test_released_status_rejects_a_remaining_remote_ref(self):
        claims = load_ledger(self.write_ledger(ledger_value()))
        result = audit(claims, {"P001": SHA_A, "P002": SHA_B, "P003": "3" * 40})
        self.assertFalse(result["ok"])
        self.assertEqual(result["release_commands"], [])
        self.assertIn({"task": "P003", "code": "released_ref_present"}, result["errors"])

    def test_malformed_and_non_claim_refs_are_rejected(self):
        for text in ("not-a-sha refs/heads/claims/P001", f"{SHA_A} refs/heads/main"):
            with self.subTest(text=text), self.assertRaises(ClaimAuditError):
                parse_remote_refs(text)

    def test_duplicate_remote_ref_is_rejected(self):
        with self.assertRaises(ClaimAuditError):
            parse_remote_refs(f"{SHA_A} refs/heads/claims/P001\n{SHA_A} refs/heads/claims/P001")

    def test_ledger_rejects_duplicate_tasks_bad_status_and_bad_sha(self):
        mutations = []
        duplicate = ledger_value()
        duplicate["claims"].append(copy.deepcopy(duplicate["claims"][0]))
        mutations.append(duplicate)
        bad_status = ledger_value()
        bad_status["claims"][0]["status"] = "stale"
        mutations.append(bad_status)
        bad_sha = ledger_value()
        bad_sha["claims"][0]["expected_sha"] = "main"
        mutations.append(bad_sha)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ClaimAuditError):
                load_ledger(self.write_ledger(value))

    def test_released_entry_requires_empty_sha(self):
        value = ledger_value()
        value["claims"][2]["expected_sha"] = SHA_A
        with self.assertRaises(ClaimAuditError):
            load_ledger(self.write_ledger(value))

    def test_release_command_rejects_untrusted_inputs(self):
        for task, sha in (("P1;echo", SHA_A), ("P٠٠١", SHA_A), ("P001", "main")):
            with self.subTest(task=task, sha=sha), self.assertRaises(ClaimAuditError):
                release_command(task, sha)

    def test_boolean_schema_and_issue_numbers_are_rejected(self):
        for field in ("schema_version", "issue"):
            value = ledger_value()
            if field == "schema_version":
                value[field] = True
            else:
                value["claims"][0][field] = True
            with self.subTest(field=field), self.assertRaises(ClaimAuditError):
                load_ledger(self.write_ledger(value))


if __name__ == "__main__":
    unittest.main()
