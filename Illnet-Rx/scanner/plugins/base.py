import shlex

class ScannerPlugin:
    """
    Base class for all scanner plugins.
    Each plugin represents a single check or tool (e.g., ClamAV, rkhunter).
    """
    def __init__(self, scanner_context):
        self.context = scanner_context

    @property
    def name(self):
        """A friendly name for the plugin, used in logs."""
        raise NotImplementedError

    def can_run(self):
        """
        Optional: A check to see if this plugin can run in the current environment.
        (e.g., check if a command exists). Defaults to True.
        """
        return True

    def get_command(self):
        """
        Returns the shell command that this plugin should execute.
        """
        raise NotImplementedError

    def run(self):
        """
        Executes the plugin's command and yields output.
        This is the main entry point for a plugin.
        """
        if not self.can_run():
            yield f"[PLUGIN-SKIP] Skipping '{self.name}' because it cannot run in this environment."
            return

        yield f"[*] Running plugin: {self.name}"
        command = self.get_command()
        
        # Use the _run_command method from the scanner's context
        yield from self.context._run_command(command)
