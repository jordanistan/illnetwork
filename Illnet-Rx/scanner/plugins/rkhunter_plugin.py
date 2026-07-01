from .base import ScannerPlugin

class RkhunterPlugin(ScannerPlugin):
    @property
    def name(self):
        return "Rkhunter Rootkit Scan"

    def get_command(self):
        # rkhunter also returns non-zero for warnings
        return ["sudo", "rkhunter", "--check", "--rootdir", self.context.scan_root, "--sk"]
