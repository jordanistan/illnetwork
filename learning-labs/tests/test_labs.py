from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


LABS_ROOT = Path(__file__).resolve().parents[1]


def run_script(relative: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LABS_ROOT / relative), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, LABS_ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LearningLabTests(unittest.TestCase):
    def test_linux_inventory_is_local_and_excludes_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "inventory.json"
            completed = run_script("linux-inventory/run.py", "--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                set(report),
                {
                    "schema_version",
                    "exercise_id",
                    "generated_at_utc",
                    "scope",
                    "network_activity",
                    "platform",
                    "root_filesystem",
                    "listening_tcp_ports",
                    "excluded_fields",
                    "limitations",
                },
            )
            self.assertEqual(
                set(report["platform"]),
                {"system", "kernel_release", "architecture", "python_version", "os_release"},
            )
            self.assertEqual(report["network_activity"], "none")
            self.assertEqual(report["scope"], "local machine only")
            self.assertIn("IP addresses", report["excluded_fields"])
            self.assertIn("user names", report["excluded_fields"])
            self.assertTrue(all(isinstance(port, int) and 0 <= port <= 65535 for port in report["listening_tcp_ports"]))
            serialized = output.read_text(encoding="utf-8").lower()
            self.assertNotIn("hostname", serialized)
            self.assertNotIn("username", serialized)

            original = output.read_text(encoding="utf-8")
            refused = run_script("linux-inventory/run.py", "--output", str(output))
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), original)

    def test_linux_parsers_accept_only_selected_local_fields(self) -> None:
        linux = load_module("linux_inventory", "linux-inventory/run.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "os-release"
            release.write_text(
                'ID="example"\nVERSION_ID="1"\nPRETTY_NAME="Example Linux"\nHOME_URL="https://ignored.invalid"\n',
                encoding="utf-8",
            )
            self.assertEqual(
                linux.read_os_release(release),
                {"id": "example", "version_id": "1", "pretty_name": "Example Linux"},
            )
            proc = root / "proc"
            proc.mkdir()
            (proc / "tcp").write_text(
                "  sl  local_address rem_address   st\n"
                "   0: 0100007F:01BB 00000000:0000 0A\n"
                "   1: 00000000:0050 00000000:0000 01\n",
                encoding="ascii",
            )
            self.assertEqual(linux.listening_tcp_ports(proc), [443])

    def test_restore_drill_uses_synthetic_data_and_matches_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = run_script("infrastructure-restore/run.py", "--workspace", directory)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            reports = list(Path(directory).glob("run-*/outcome.json"))
            self.assertEqual(len(reports), 1)
            report = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["data_classification"], "synthetic")
            self.assertTrue(report["archive_members_safe"])
            self.assertTrue(all(item["match"] for item in report["files"]))

    def test_restore_member_validation_rejects_cross_platform_traversal(self) -> None:
        restore = load_module("infrastructure_restore", "infrastructure-restore/run.py")
        for unsafe in ("", "/absolute", "../escape", "a/../escape", "a//b", "a/./b", "..\\escape", "C:/escape", "C:\\escape", "name\x00.txt"):
            with self.subTest(unsafe=unsafe):
                self.assertFalse(restore.safe_member(unsafe))
        self.assertTrue(restore.safe_member("customers/example.txt"))

    def test_review_gate_detects_deliberately_unsafe_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review.json"
            completed = run_script("intelligent-review-gate/run.py", "--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["data_classification"], "synthetic")
            self.assertEqual(report["detected_candidate_mismatches"], ["wrong-output"])

            original = output.read_text(encoding="utf-8")
            refused = run_script("intelligent-review-gate/run.py", "--output", str(output))
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
