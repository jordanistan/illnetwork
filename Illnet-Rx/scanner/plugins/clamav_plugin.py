from .base import ScannerPlugin
import os
import shlex

class ClamAVPlugin(ScannerPlugin):
    @property
    def name(self):
        return "ClamAV Malware Scan"

    def get_command(self):
        scan_subdir = self.context.config.get("SCAN_PATH", "")
        full_scan_path = os.path.join(self.context.scan_root, scan_subdir.lstrip('/'))
        # clamscan returns 1 if viruses are found, which is handled by the runner
        return f"sudo clamscan -r --bell -i {shlex.quote(full_scan_path)}"
