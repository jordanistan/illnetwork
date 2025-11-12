from .base import ScannerPlugin
import shlex

class CredentialScanPlugin(ScannerPlugin):
    @property
    def name(self):
        return "Exposed Credential Scan"

    def get_command(self):
        scan_paths = f"{shlex.quote(self.context.scan_root)}/home {shlex.quote(self.context.scan_root)}/etc"
        command = (
            f"sudo find {scan_paths} -type f "
            r"\( -name '*id_rsa*' -o -name '*.pem' -o -name '*.key' -o -name '*.token' -o -name '*.env' \) "
            r"2>/dev/null | sed 's/^/CRED: /'"
        )
        return command
