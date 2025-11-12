import subprocess
import os
import shlex
import datetime

import subprocess
import os
import shlex
import datetime
import importlib
import pkgutil
from . import plugins

class Scanner:
    """
    A Python-based security scanner engine that uses a modular plugin
    architecture to run scans.
    """
    def __init__(self, config):
        self.config = config
        self.scan_root = "/"
        self.target_host = "localhost"
        self.report_file_path = self._generate_report_path()
        self.plugins = self._load_plugins()

        if self.config.get("REMOTE_HOST"):
            self.scan_root = "/mnt/remote"
            self.target_host = self.config["REMOTE_HOST"]

    def _load_plugins(self):
        """Dynamically loads all scanner plugins from the plugins directory."""
        loaded_plugins = []
        plugin_package = plugins
        for _, module_name, _ in pkgutil.walk_packages(plugin_package.__path__, plugin_package.__name__ + '.'):
            if module_name.endswith('base'):
                continue
            module = importlib.import_module(module_name)
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, type) and issubclass(attribute, plugins.base.ScannerPlugin) and attribute is not plugins.base.ScannerPlugin:
                    loaded_plugins.append(attribute(self))
        return loaded_plugins

    def _generate_report_path(self):
        """Generates a timestamped path for the raw scan log."""
        output_dir = self.config.get("OUTPUT_DIR", "/opt/data/reports")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(output_dir, f"report_{timestamp}.txt")

    def _run_command(self, command):
        """
        Runs a shell command and yields its output line by line.
        The output is also written to the report file.
        """
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            bufsize=1
        )
        
        with open(self.report_file_path, "a") as report_file:
            for line in process.stdout:
                line = line.strip()
                report_file.write(line + '\n')
                yield line
        
        process.wait()
        if process.returncode != 0:
            err_msg = f"[SCANNER-WARN] Command '{command}' finished with non-zero exit code: {process.returncode}."
            with open(self.report_file_path, "a") as report_file:
                report_file.write(err_msg + '\n')
            yield err_msg

    def run_scan(self):
        """
        Executes the full scan sequence by running all loaded plugins.
        """
        yield "Initializing plugin-based scanner..."
        yield f"Found {len(self.plugins)} plugins to run."
        yield f"Report log will be saved to: {self.report_file_path}"
        yield f"Target: {self.target_host}"
        yield "--------------------------------------"

        for plugin in self.plugins:
            yield from plugin.run()

        yield "--------------------------------------"
        yield "All plugins complete."
        
        yield f"__REPORT_FILE__={self.report_file_path}"
        yield f"__TARGET_HOST__={self.target_host}"

    def run_health_check(self):
        """
        Executes a fast, local health check on the container host.
        """
        yield "Initializing Host Health Check..."
        yield f"Report log will be saved to: {self.report_file_path}"
        yield "Target: localhost (container)"
        yield "--------------------------------------"

        healthcheck_script_path = os.path.join(os.path.dirname(__file__), 'healthcheck.sh')
        yield from self._run_command(f"sudo {shlex.quote(healthcheck_script_path)}")

        yield "--------------------------------------"
        yield "Health check complete."
        
        yield f"__REPORT_FILE__={self.report_file_path}"
        yield f"__TARGET_HOST__=localhost"


if __name__ == '__main__':
    # This allows running the scanner directly for testing
    # It uses environment variables for configuration, similar to the app
    config = {
        "REMOTE_HOST": os.getenv("REMOTE_HOST"),
        "SCAN_PATH": os.getenv("SCAN_PATH"),
        "OUTPUT_DIR": os.getenv("OUTPUT_DIR", "/tmp/reports")
    }
    scanner = Scanner(config)
    for line in scanner.run_scan():
        print(line)
