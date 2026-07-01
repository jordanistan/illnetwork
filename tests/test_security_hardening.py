import importlib.util
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SECURITY_MODULE = REPO_ROOT / "Illnet-Rx" / "webui" / "security.py"


def load_security_module():
    spec = importlib.util.spec_from_file_location("illnet_rx_security", SECURITY_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.security = load_security_module()

    def test_report_path_rejects_traversal_and_absolute_paths(self):
        report_dir = REPO_ROOT / "data" / "reports"

        with self.assertRaises(ValueError):
            self.security.resolve_report_path(report_dir, "../secrets.md", {".md"})

        with self.assertRaises(ValueError):
            self.security.resolve_report_path(report_dir, "/tmp/secrets.md", {".md"})

    def test_report_path_allows_expected_report_inside_directory(self):
        report_dir = REPO_ROOT / "data" / "reports"
        resolved = self.security.resolve_report_path(
            report_dir,
            "localhost-20251109_084432-Summary-Report-critical.md",
            {".md"},
        )

        self.assertEqual(resolved.parent, report_dir.resolve())

    def test_secret_settings_are_masked_before_rendering(self):
        masked = self.security.mask_secret_settings(
            {
                "OPENAI_API_KEY": "sk-real-secret",
                "SMTP_PASS": "smtp-secret",
                "REMOTE_HOST": "server.local",
            }
        )

        self.assertEqual(masked["OPENAI_API_KEY"], "")
        self.assertEqual(masked["SMTP_PASS"], "")
        self.assertEqual(masked["REMOTE_HOST"], "server.local")

    def test_default_admin_password_is_rejected(self):
        with self.assertRaises(ValueError):
            self.security.require_secure_admin_password("password")

        self.assertEqual(
            self.security.require_secure_admin_password("correct-horse-battery-staple"),
            "correct-horse-battery-staple",
        )

    def test_remediation_command_uses_argument_list_not_shell_string(self):
        command = self.security.build_remediation_command(
            target_host="server.local",
            configured_remote_host="server.local",
            configured_remote_user="ubuntu",
        )

        self.assertIsInstance(command, list)
        self.assertEqual(command[0], "ssh")
        self.assertIn("ubuntu@server.local", command)
        self.assertEqual(command[-2:], ["bash", "-s"])

    def test_remediation_command_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            self.security.build_remediation_command(
                target_host="server.local",
                configured_remote_host="server.local",
                configured_remote_user="ubuntu;touch /tmp/pwned",
            )

    def test_report_base_filename_sanitizes_hostnames(self):
        name = self.security.safe_report_base_filename(
            "../bad host;rm -rf /",
            "20260701_130000",
            "critical",
        )

        self.assertNotIn("/", name)
        self.assertNotIn(";", name)
        self.assertTrue(name.endswith("-Summary-Report-critical"))

    def test_csrf_tokens_are_stable_per_session_and_validated(self):
        session = {}
        token = self.security.get_csrf_token(session)

        self.assertEqual(token, self.security.get_csrf_token(session))
        self.assertTrue(self.security.validate_csrf_token(session, token))
        self.assertFalse(self.security.validate_csrf_token(session, "wrong-token"))

    def test_state_changing_templates_include_csrf_token(self):
        for template in [
            REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "settings.html",
            REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "reports.html",
        ]:
            with self.subTest(template=template):
                self.assertIn("csrf_token", template.read_text())

    def test_ui_templates_reflect_local_first_and_agent_mode(self):
        settings_template = REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "settings.html"
        index_template = REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "index.html"
        dashboard_template = REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "dashboard.html"

        self.assertIn("SCAN_MODE", settings_template.read_text())
        self.assertIn("AGENT_TOKEN", settings_template.read_text())
        self.assertIn("Local-first", index_template.read_text())
        self.assertIn("Agent", index_template.read_text())
        self.assertIn("Local-first monitoring", dashboard_template.read_text())

    def test_remediation_fetch_sends_csrf_header(self):
        template = REPO_ROOT / "Illnet-Rx" / "webui" / "templates" / "remediation.html"
        content = template.read_text()

        self.assertIn("X-CSRFToken", content)
        self.assertIn("csrf_token", content)

    def test_flask_app_enforces_csrf_on_post(self):
        app_source = (REPO_ROOT / "Illnet-Rx" / "webui" / "app.py").read_text()

        self.assertIn("@app.before_request", app_source)
        self.assertIn("validate_csrf_request", app_source)

    def test_scanner_uses_shell_only_for_string_commands(self):
        scanner_source = (REPO_ROOT / "Illnet-Rx" / "scanner" / "scanner.py").read_text()

        self.assertIn("shell=isinstance(command, str)", scanner_source)

    def test_scanner_plugins_return_arg_lists_when_no_pipeline_is_needed(self):
        for plugin in [
            REPO_ROOT / "Illnet-Rx" / "scanner" / "plugins" / "freshclam_plugin.py",
            REPO_ROOT / "Illnet-Rx" / "scanner" / "plugins" / "clamav_plugin.py",
            REPO_ROOT / "Illnet-Rx" / "scanner" / "plugins" / "rkhunter_plugin.py",
        ]:
            with self.subTest(plugin=plugin):
                self.assertIn("return [", plugin.read_text())


if __name__ == "__main__":
    unittest.main()
