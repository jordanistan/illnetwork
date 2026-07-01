import importlib.util
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENT_MODULE = REPO_ROOT / "Illnet-Rx" / "webui" / "agent_ingest.py"


def load_agent_module():
    spec = importlib.util.spec_from_file_location("illnet_rx_agent_ingest", AGENT_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentIngestTests(unittest.TestCase):
    def setUp(self):
        self.agent = load_agent_module()

    def test_validate_agent_token_requires_exact_match(self):
        self.assertTrue(self.agent.validate_agent_token("token-123", "token-123"))
        self.assertFalse(self.agent.validate_agent_token("token-123", "wrong"))
        self.assertFalse(self.agent.validate_agent_token("", "token-123"))

    def test_save_agent_scan_log_writes_inside_report_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.agent.save_agent_scan_log(tmpdir, "../server.local", "scan output", timestamp="20260701_120000")

            self.assertTrue(path.startswith(str(pathlib.Path(tmpdir).resolve())))
            self.assertTrue(path.endswith(".txt"))
            self.assertEqual(pathlib.Path(path).read_text(), "scan output")

    def test_agent_bundle_files_include_dashboard_and_token_fields(self):
        install_script = REPO_ROOT / "Illnet-Rx" / "agent" / "install.sh"
        agent_script = REPO_ROOT / "Illnet-Rx" / "agent" / "illnet-agent.sh"

        self.assertIn("DASHBOARD_URL", install_script.read_text())
        self.assertIn("AGENT_TOKEN", install_script.read_text())
        self.assertIn("X-Illnet-Agent-Token", agent_script.read_text())
        self.assertIn("api/agent/report", agent_script.read_text())


if __name__ == "__main__":
    unittest.main()
