import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SCRIPTS = [
    REPO_ROOT / "setup.sh",
    REPO_ROOT / "Illnet-Rx" / "setup.sh",
]


class SetupPortabilityTests(unittest.TestCase):
    def test_setup_scripts_use_env_bash(self):
        for script in SETUP_SCRIPTS:
            with self.subTest(script=script):
                self.assertEqual(script.read_text().splitlines()[0], "#!/usr/bin/env bash")

    def test_setup_scripts_support_noninteractive_arguments(self):
        for script in SETUP_SCRIPTS:
            content = script.read_text()
            with self.subTest(script=script):
                self.assertIn("--non-interactive", content)
                self.assertIn("REMOTE_HOST", content)
                self.assertIn("OPENAI_API_KEY", content)

    def test_setup_scripts_document_cross_platform_install_commands(self):
        required_markers = ["apt", "dnf", "pacman", "brew"]
        for script in SETUP_SCRIPTS:
            content = script.read_text()
            with self.subTest(script=script):
                for marker in required_markers:
                    self.assertIn(marker, content)

    def test_setup_scripts_do_not_write_default_admin_password(self):
        for script in SETUP_SCRIPTS:
            content = script.read_text()
            with self.subTest(script=script):
                self.assertNotRegex(content, re.compile(r"ADMIN_PASSWORD=password\\b"))

    def test_setup_scripts_write_shell_escaped_env_values(self):
        for script in SETUP_SCRIPTS:
            content = script.read_text()
            with self.subTest(script=script):
                self.assertIn("write_env_var", content)
                self.assertIn("printf '%s=%q\\n'", content)


if __name__ == "__main__":
    unittest.main()
