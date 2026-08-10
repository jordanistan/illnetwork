import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PARSERS = [
    REPO_ROOT / "scanner" / "parse_logs.py",
    REPO_ROOT / "Illnet-Rx" / "scanner" / "parse_logs.py",
]


class ReportGenerationTests(unittest.TestCase):
    def test_report_is_written_without_openai_package_or_key(self):
        scan_log = "=== Scan ===\nTarget: localhost\nCRED: /etc/example.env\n"
        for parser in PARSERS:
            with self.subTest(parser=parser), tempfile.TemporaryDirectory() as tmpdir:
                report_dir = pathlib.Path(tmpdir) / "reports"
                env = os.environ.copy()
                env.pop("OPENAI_API_KEY", None)
                env["OUTPUT_DIR"] = str(report_dir)
                env["PYTHONPATH"] = str(parser.parent)
                result = subprocess.run(
                    [sys.executable, str(parser), "localhost", str(pathlib.Path(tmpdir) / "scan.txt")],
                    input=scan_log,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn("Reports saved:", result.stdout)
                self.assertEqual(len(list(report_dir.glob("*-Summary-Report-low.md"))), 1)
                self.assertEqual(len(list(report_dir.glob("*-Summary-Report-low.html"))), 1)
                self.assertEqual(len(list(report_dir.glob("*-Summary-Report-low.json"))), 1)


if __name__ == "__main__":
    unittest.main()
