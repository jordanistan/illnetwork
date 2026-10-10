import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("approval_pilot", ROOT / "pilot.py")
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def sample_request():
    return {
        "schema_version": 1,
        "request_id": "demo-support-001",
        "workflow": "support_summary",
        "objective": "Prepare a synthetic support summary and review checklist.",
        "data_classification": "synthetic",
        "inputs": [
            {"name": "ticket_summary", "value": "Synthetic user cannot open the demo report."},
            {"name": "observed_state", "value": "Synthetic service health is normal."},
        ],
        "allowed_outputs": ["summary", "review_checklist"],
        "human_owner": "demo-reviewer",
    }


class ApprovalPilotTests(unittest.TestCase):
    def write_request(self, directory, request=None):
        path = Path(directory) / "request.json"
        path.write_text(json.dumps(request or sample_request()), encoding="utf-8")
        return path

    def test_prepare_is_deterministic_and_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            plan = PILOT.prepare(request, Path(directory) / "run", "plan.json")
            self.assertEqual("pending_human_review", plan["status"])
            self.assertFalse(plan["capabilities"]["external_actions"])
            self.assertFalse(plan["capabilities"]["network"])
            self.assertTrue(all(not step["external_effect"] for step in plan["steps"]))
            self.assertEqual(PILOT.digest(PILOT.validate_request(sample_request())), plan["request_sha256"])

    def test_approval_records_hash_but_not_live_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            plan = PILOT.prepare(request, run, "plan.json")
            review = PILOT.record_review(
                request,
                run,
                "plan.json",
                "review.json",
                "approve",
                "demo-reviewer",
                "The synthetic output meets the documented demo criteria.",
            )
            self.assertEqual(PILOT.digest(plan), review["plan_sha256"])
            self.assertEqual("approved_for_demo_handoff", review["status"])
            self.assertFalse(review["live_execution_authorized"])
            self.assertEqual(
                review, PILOT.verify(request, run, "plan.json", "review.json")
            )

    def test_rejection_is_a_valid_audited_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            PILOT.prepare(request, run, "plan.json")
            review = PILOT.record_review(
                request,
                run,
                "plan.json",
                "review.json",
                "reject",
                "demo-reviewer",
                "The synthetic plan needs a clearer acceptance criterion.",
            )
            self.assertEqual("rejected", review["status"])
            PILOT.verify(request, run, "plan.json", "review.json")

    def test_tampered_plan_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            PILOT.prepare(request, run, "plan.json")
            PILOT.record_review(
                request,
                run,
                "plan.json",
                "review.json",
                "approve",
                "demo-reviewer",
                "The unchanged synthetic plan is ready for demo handoff.",
            )
            plan_path = run / "plan.json"
            plan = json.loads(plan_path.read_text())
            plan["objective"] = "Changed after review"
            plan_path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(PILOT.PilotError, "does not match"):
                PILOT.verify(request, run, "plan.json", "review.json")

    def test_sensitive_names_and_values_are_rejected(self):
        for field_name in ("api_key", "aws_access_key_id", "email", "medical_record"):
            with self.subTest(field_name=field_name):
                named = sample_request()
                named["inputs"][0]["name"] = field_name
                with self.assertRaisesRegex(PILOT.PilotError, "unsafe"):
                    PILOT.validate_request(named)
        for field_value in (
            "Bearer abcdefghijklmnop",
            "AKIAIOSFODNN7EXAMPLE",
            "person@example.test",
            "Synthetic patient medical record",
            "eyJheader.eyJpayload.signature",
            "xoxb-1234567890-abcdefgh",
            "AIzaSyD1234567890abcdefghijkl",
        ):
            with self.subTest(field_value=field_value):
                valued = sample_request()
                valued["inputs"][0]["value"] = field_value
                with self.assertRaisesRegex(PILOT.PilotError, "credential"):
                    PILOT.validate_request(valued)

    def test_only_exact_synthetic_schema_is_accepted(self):
        classified = sample_request()
        classified["data_classification"] = "customer"
        with self.assertRaisesRegex(PILOT.PilotError, "synthetic"):
            PILOT.validate_request(classified)
        extra = sample_request()
        extra["email"] = "person@example.test"
        with self.assertRaisesRegex(PILOT.PilotError, "schema exactly"):
            PILOT.validate_request(extra)

    def test_workspace_traversal_symlink_and_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            with self.assertRaisesRegex(PILOT.PilotError, "one visible"):
                PILOT.prepare(request, run, "../plan.json")
            PILOT.prepare(request, run, "plan.json")
            with self.assertRaisesRegex(PILOT.PilotError, "overwrite"):
                PILOT.prepare(request, run, "plan.json")
            link = Path(directory) / "linked-run"
            link.symlink_to(run, target_is_directory=True)
            with self.assertRaisesRegex(PILOT.PilotError, "symlink"):
                PILOT.prepare(request, link, "other.json")

    def test_review_status_cannot_be_forged(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            PILOT.prepare(request, run, "plan.json")
            PILOT.record_review(
                request,
                run,
                "plan.json",
                "review.json",
                "approve",
                "demo-reviewer",
                "The synthetic output meets the documented demo criteria.",
            )
            review_path = run / "review.json"
            review = json.loads(review_path.read_text())
            review["status"] = "live_execution_authorized"
            review_path.write_text(json.dumps(review))
            with self.assertRaisesRegex(PILOT.PilotError, "do not match"):
                PILOT.verify(request, run, "plan.json", "review.json")

    def test_forged_plan_schema_cannot_be_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            run.mkdir()
            forged = {
                "request_id": "demo-support-001",
                "status": "pending_human_review",
                "steps": [{"action": "Send a live message", "external_effect": True}],
            }
            (run / "plan.json").write_text(json.dumps(forged))
            with self.assertRaisesRegex(PILOT.PilotError, "generated schema exactly"):
                PILOT.record_review(
                    request,
                    run,
                    "plan.json",
                    "review.json",
                    "approve",
                    "demo-reviewer",
                    "This forged plan must not be approved for handoff.",
                )

    def test_unexpected_review_fields_fail_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            PILOT.prepare(request, run, "plan.json")
            PILOT.record_review(
                request,
                run,
                "plan.json",
                "review.json",
                "approve",
                "demo-reviewer",
                "The synthetic output meets the documented demo criteria.",
            )
            review_path = run / "review.json"
            review = json.loads(review_path.read_text())
            review["execute_now"] = True
            review_path.write_text(json.dumps(review))
            with self.assertRaisesRegex(PILOT.PilotError, "generated schema exactly"):
                PILOT.verify(request, run, "plan.json", "review.json")

    def test_full_schema_forged_plan_must_match_request(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            plan = PILOT.prepare(request, run, "plan.json")
            plan["objective"] = "A different but schema-valid synthetic objective for review."
            plan_path = run / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(PILOT.PilotError, "supplied synthetic request"):
                PILOT.record_review(
                    request,
                    run,
                    "plan.json",
                    "review.json",
                    "approve",
                    "demo-reviewer",
                    "A valid-looking forged plan must not pass the request binding.",
                )

    def test_full_schema_review_still_requires_request_bound_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            run = Path(directory) / "run"
            plan = PILOT.prepare(request, run, "plan.json")
            plan["objective"] = "A different but schema-valid synthetic objective for review."
            (run / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            forged_review = {
                "schema_version": 1,
                "request_id": plan["request_id"],
                "plan_sha256": PILOT.digest(plan),
                "decision": "approve",
                "status": "approved_for_demo_handoff",
                "reviewer_label": "demo-reviewer",
                "reason": "This valid-looking review must still fail request binding.",
                "live_execution_authorized": False,
            }
            (run / "review.json").write_text(json.dumps(forged_review), encoding="utf-8")
            with self.assertRaisesRegex(PILOT.PilotError, "supplied synthetic request"):
                PILOT.verify(request, run, "plan.json", "review.json")

    def test_malformed_scalar_types_raise_pilot_error(self):
        malformed_requests = []
        workflow = sample_request()
        workflow["workflow"] = []
        malformed_requests.append(workflow)
        outputs = sample_request()
        outputs["allowed_outputs"] = [{}]
        malformed_requests.append(outputs)
        for request in malformed_requests:
            with self.subTest(request=request):
                with self.assertRaises(PILOT.PilotError):
                    PILOT.validate_request(request)

        plan = PILOT.build_plan(PILOT.validate_request(sample_request()))
        plan["input_names"] = [{}]
        with self.assertRaises(PILOT.PilotError):
            PILOT.validate_plan(plan)
        review = {
            "schema_version": 1,
            "request_id": "demo-support-001",
            "plan_sha256": "0" * 64,
            "decision": [],
            "status": "approved_for_demo_handoff",
            "reviewer_label": "demo-reviewer",
            "reason": "This malformed decision must be rejected safely.",
            "live_execution_authorized": False,
        }
        with self.assertRaises(PILOT.PilotError):
            PILOT.validate_review(review)

    def test_symlinked_workspace_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.write_request(directory)
            real_parent = Path(directory) / "real-parent"
            real_parent.mkdir()
            alias = Path(directory) / "alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            with self.assertRaisesRegex(PILOT.PilotError, "ancestors"):
                PILOT.prepare(request, alias / "nested", "plan.json")


if __name__ == "__main__":
    unittest.main()
