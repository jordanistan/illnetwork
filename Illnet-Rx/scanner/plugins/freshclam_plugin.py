from .base import ScannerPlugin

class FreshclamPlugin(ScannerPlugin):
    @property
    def name(self):
        return "ClamAV Definitions Update"

    def get_command(self):
        return "sudo freshclam"
