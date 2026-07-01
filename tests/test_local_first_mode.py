import os
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SETUP_SCRIPTS = [
    REPO_ROOT / "setup.sh",
    REPO_ROOT / "Illnet-Rx" / "setup.sh",
]


class LocalFirstSetupTests(unittest.TestCase):
    def test_noninteractive_local_mode_does_not_require_ssh_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            marker = tmp_path / "ssh-used.txt"

            for tool in ("ssh", "ssh-keygen"):
                stub = bin_dir / tool
                stub.write_text(
                    "#!/usr/bin/env bash\n"
                    f"echo {tool} >> \"{marker}\"\n"
                    "exit 99\n"
                )
                stub.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "HOME": str(tmp_path / "home"),
                    "ENV_FILE": str(tmp_path / "local.env"),
                }
            )

            for script in SETUP_SCRIPTS:
                with self.subTest(script=script):
                    result = subprocess.run(
                        [
                            "bash",
                            str(script),
                            "--non-interactive",
                            "local",
                            "sk-local-test-key",
                            "test-admin-password",
                        ],
                        cwd=REPO_ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
                    )
                    self.assertFalse(marker.exists())
                    env_file = pathlib.Path(env["ENV_FILE"])
                    self.assertTrue(env_file.exists())
                    content = env_file.read_text()
                    self.assertIn("SCAN_MODE=local", content)
                    self.assertNotIn("REMOTE_HOST=", content)
                    env_file.unlink()


if __name__ == "__main__":
    unittest.main()
