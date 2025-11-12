from .base import ScannerPlugin
import shlex

class RkhunterPlugin(ScannerPlugin):
    @property
    def name(self):
        return "Rkhunter Rootkit Scan"

    def get_command(self):
        # rkhunter also returns non-zero for warnings
        return f"sudo rkhunter --check --rootdir {shlex.quote(self.context.scan_root)} --sk"
