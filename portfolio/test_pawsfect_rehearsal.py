import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pawsfect_rehearsal", ROOT / "pawsfect_rehearsal.py")
REHEARSAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REHEARSAL)
EXAMPLE = ROOT.parent / ".github/portfolio/pawsfect-rehearsal/example.json"


def request():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def write_json(directory, value, name="value.json"):
    path = Path(directory) / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class PawsfectRehearsalTests(unittest.TestCase):
    def assert_request_rejected(self, value):
        with self.assertRaises(REHEARSAL.RehearsalError):
            REHEARSAL.validate_request(value)

    def generate(self, base):
        request_path = Path(base) / "request.json"
        request_path.write_bytes(EXAMPLE.read_bytes())
        report_path = Path(base) / "report.json"
        review_path = Path(base) / "review.json"
        report = REHEARSAL.run(request_path, report_path)
        review = REHEARSAL.record_review(
            request_path, report_path, review_path,
            "accept_offline_result", "synthetic_controls_match",
        )
        return request_path, report_path, review_path, report, review

    def test_example_has_frozen_source_prerequisites_and_scenarios(self):
        value = REHEARSAL.validate_request(request())
        self.assertEqual(REHEARSAL.SOURCE_PATH, value["source_path"])
        self.assertEqual(REHEARSAL.SOURCE_BLOB_SHA, value["source_blob_sha"])
        self.assertEqual(list(REHEARSAL.PREREQUISITES), [item["id"] for item in value["prerequisites"]])
        self.assertEqual({REHEARSAL.NOT_EVALUATED}, {item["status"] for item in value["prerequisites"]})
        self.assertEqual([item[0] for item in REHEARSAL.SCENARIO_REGISTRY], [item["id"] for item in value["scenarios"]])

    def test_report_compares_all_eleven_synthetic_controls(self):
        raw = EXAMPLE.read_bytes()
        report = REHEARSAL.expected_report(request(), REHEARSAL.sha256_bytes(raw))
        self.assertEqual(11, len(report["scenario_results"]))
        self.assertEqual({"matches_expected_synthetic_branch"}, {item["comparison"] for item in report["scenario_results"]})
        self.assertEqual("hold_for_human_booking_confirmation", report["scenario_results"][3]["expected_control"])

    def test_every_real_capability_and_authority_is_false(self):
        report = REHEARSAL.expected_report(request(), REHEARSAL.sha256_bytes(EXAMPLE.read_bytes()))
        self.assertIs(report["capabilities"]["synthetic_data_only"], True)
        for key, value in report["capabilities"].items():
            if key != "synthetic_data_only":
                self.assertIs(value, False)
        self.assertTrue(all(value is False for value in report["authorizations"].values()))

    def test_review_binds_raw_normalized_and_report_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path, report_path, review_path, report, review = self.generate(directory)
            self.assertEqual(REHEARSAL.sha256_bytes(request_path.read_bytes()), review["request_file_sha256"])
            self.assertEqual(REHEARSAL.digest(REHEARSAL.validate_request(request())), review["normalized_request_sha256"])
            self.assertEqual(REHEARSAL.digest(report), review["report_sha256"])
            self.assertEqual(review, REHEARSAL.verify(request_path, report_path, review_path))

    def test_output_is_byte_deterministic_across_directories(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_files = self.generate(first)[:3]
            second_files = self.generate(second)[:3]
            self.assertEqual(first_files[1].read_bytes(), second_files[1].read_bytes())
            self.assertEqual(first_files[2].read_bytes(), second_files[2].read_bytes())

    def test_prerequisites_cannot_claim_real_state(self):
        for changed in (True, False, 1, "verified", "approved", "ready", "pending"):
            value = request()
            value["prerequisites"][0]["status"] = changed
            with self.subTest(changed=changed):
                self.assert_request_rejected(value)

    def test_request_root_nested_types_order_and_source_are_exact(self):
        mutations = []
        value = request(); value["extra"] = False; mutations.append(value)
        value = request(); value["version"] = True; mutations.append(value)
        value = request(); value["offline_only"] = 1; mutations.append(value)
        value = request(); value["live_execution_authorized"] = True; mutations.append(value)
        value = request(); value["source_blob_sha"] = "0" * 40; mutations.append(value)
        value = request(); value["source_path"] = "changed.md"; mutations.append(value)
        value = request(); value["prerequisites"][0] = {"status": REHEARSAL.NOT_EVALUATED, "id": REHEARSAL.PREREQUISITES[0]}; mutations.append(value)
        value = request(); value["scenarios"][0], value["scenarios"][1] = value["scenarios"][1], value["scenarios"][0]; mutations.append(value)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_request_rejected(value)

    def test_variants_and_controls_are_closed_enums(self):
        value = request(); value["scenarios"][0]["variant"] = "real-customer"; self.assert_request_rejected(value)
        value = request(); value["scenarios"][0]["observed_control"] = "book_now"; self.assert_request_rejected(value)
        value = request(); value["scenarios"][0]["note"] = "free text"; self.assert_request_rejected(value)

    def test_every_reviewed_variant_reaches_its_exact_matching_control(self):
        base = request()
        for scenario_index, (scenario_id, variants) in enumerate(REHEARSAL.SCENARIO_REGISTRY):
            for variant, expected_control in variants.items():
                value = copy.deepcopy(base)
                value["scenarios"][scenario_index] = {
                    "id": scenario_id,
                    "variant": variant,
                    "observed_control": expected_control,
                }
                raw = json.dumps(value).encode()
                report = REHEARSAL.expected_report(value, REHEARSAL.sha256_bytes(raw))
                result = report["scenario_results"][scenario_index]
                with self.subTest(scenario=scenario_id, variant=variant):
                    self.assertEqual(expected_control, result["expected_control"])
                    self.assertEqual("matches_expected_synthetic_branch", result["comparison"])
                    review = REHEARSAL.expected_review(
                        value, report, "accept_offline_result", "synthetic_controls_match"
                    )
                    self.assertEqual("reviewed_offline_only", review["status"])

    def test_unsafe_weather_control_preserves_refund_due_branch(self):
        result = REHEARSAL.expected_report(request(), REHEARSAL.sha256_bytes(EXAMPLE.read_bytes()))
        self.assertEqual(
            "use_preapproved_safe_alternative_or_stop_and_record_full_refund_due",
            result["scenario_results"][6]["expected_control"],
        )

    def test_mismatch_cannot_be_accepted_but_can_be_rejected(self):
        value = request()
        value["scenarios"][5] = {
            "id": "p016-s06-worker-unavailable",
            "variant": "ready-backup",
            "observed_control": "notify_and_record_full_refund_due",
        }
        raw = json.dumps(value).encode()
        report = REHEARSAL.expected_report(value, REHEARSAL.sha256_bytes(raw))
        self.assertEqual("needs_offline_review", report["scenario_results"][5]["comparison"])
        with self.assertRaises(REHEARSAL.RehearsalError):
            REHEARSAL.expected_review(value, report, "accept_offline_result", "synthetic_controls_match")
        review = REHEARSAL.expected_review(value, report, "reject_offline_result", "synthetic_control_mismatch")
        self.assertEqual("reviewed_offline_only", review["status"])

    def test_sensitive_and_held_content_are_rejected(self):
        samples = (
            "person@example.com", "512-555-1212", "123-45-6789",
            "4111 1111 1111 1111", "api_key=abcdefghijklmnop",
            "door code=1234", "123 Main Street", "sxswasted.com",
        )
        for sample in samples:
            value = request(); value["unexpected"] = sample
            with self.subTest(sample=sample):
                self.assert_request_rejected(value)

    def test_strict_json_rejects_duplicate_constants_utf8_oversize_and_nonobject(self):
        with tempfile.TemporaryDirectory() as directory:
            samples = {
                "duplicate.json": b'{"version":1,"version":1}',
                "constant.json": b'{"value":NaN}',
                "invalid.json": b'\xff\xfe',
                "large.json": b' ' * (REHEARSAL.MAX_JSON_BYTES + 1),
                "array.json": b'[]',
            }
            for name, content in samples.items():
                path = Path(directory) / name; path.write_bytes(content)
                with self.subTest(name=name), self.assertRaises(REHEARSAL.RehearsalError):
                    REHEARSAL.read_json(path)

    def test_inputs_reject_leaf_and_ancestor_symlinks_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); real = base / "real"; real.mkdir()
            target = write_json(real, request(), "target.json")
            leaf = base / "leaf.json"; leaf.symlink_to(target)
            alias = base / "alias"; alias.symlink_to(real, target_is_directory=True)
            for path in (leaf, alias / "target.json", base):
                with self.subTest(path=path), self.assertRaises(REHEARSAL.RehearsalError):
                    REHEARSAL.read_json(path)

    def test_outputs_are_owner_only_create_once_and_reject_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); request_path = write_json(base, request(), "request.json")
            report_path = base / "report.json"
            REHEARSAL.run(request_path, report_path)
            self.assertEqual(0o600, stat.S_IMODE(report_path.stat().st_mode))
            with self.assertRaisesRegex(REHEARSAL.RehearsalError, "overwrite"):
                REHEARSAL.run(request_path, report_path)
            for path in (base / ".hidden.json", base / "wrong.txt", base / "sub" / ".." / "escape.json"):
                with self.subTest(path=path), self.assertRaises(REHEARSAL.RehearsalError):
                    REHEARSAL.run(request_path, path)
            real = base / "real"; real.mkdir(); alias = base / "alias"; alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises(REHEARSAL.RehearsalError):
                REHEARSAL.run(request_path, alias / "report.json")

    def test_tampered_request_report_or_review_fails_verification(self):
        for target in ("request", "report", "review"):
            with tempfile.TemporaryDirectory() as directory:
                request_path, report_path, review_path, _, _ = self.generate(directory)
                path = {"request": request_path, "report": report_path, "review": review_path}[target]
                value = json.loads(path.read_text())
                if target == "request":
                    value["request_id"] = "changed-synthetic-id"
                elif target == "report":
                    value["authorizations"]["booking_authorized"] = True
                else:
                    value["report_sha256"] = "0" * 64
                path.write_text(json.dumps(value))
                with self.subTest(target=target), self.assertRaises(REHEARSAL.RehearsalError):
                    REHEARSAL.verify(request_path, report_path, review_path)

    def test_schema_valid_forgery_and_authority_true_are_rejected(self):
        raw_sha = REHEARSAL.sha256_bytes(EXAMPLE.read_bytes())
        report = REHEARSAL.expected_report(request(), raw_sha)
        forged = copy.deepcopy(report); forged["scenario_results"][0]["expected_control"] = "book_now"
        with self.assertRaises(REHEARSAL.RehearsalError):
            REHEARSAL.validate_report(forged, request(), raw_sha)
        forged = copy.deepcopy(report); forged["authorizations"]["launch_authorized"] = True
        with self.assertRaises(REHEARSAL.RehearsalError):
            REHEARSAL.validate_report(forged, request(), raw_sha)

    def test_cli_invalid_input_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"; bad.write_text("{}")
            result = subprocess.run(
                [sys.executable, str(ROOT / "pawsfect_rehearsal.py"), "run", str(bad), str(Path(directory) / "out.json")],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("pawsfect-rehearsal:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
