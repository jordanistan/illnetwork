import os
import json

class Config:
    """
    Manages application configuration, loading from a JSON file and
    falling back to environment variables.
    """
    def __init__(self, config_path='data/config.json'):
        self.config_path = config_path
        self.settings = self._load_config()

    def _load_config(self):
        """Loads settings from the JSON file, with env var fallback."""
        # Default values from environment variables
        env_settings = {
            'REMOTE_HOST': os.getenv('REMOTE_HOST', ''),
            'REMOTE_USER': os.getenv('REMOTE_USER', ''),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
            'SCAN_PATH': os.getenv('SCAN_PATH', '/'),
            'ALERT_SEVERITY_THRESHOLD': os.getenv('ALERT_SEVERITY_THRESHOLD', 'high'),
            'SLACK_WEBHOOK_URL': os.getenv('SLACK_WEBHOOK_URL', ''),
            'SMTP_HOST': os.getenv('SMTP_HOST', ''),
            'SMTP_PORT': os.getenv('SMTP_PORT', '587'),
            'SMTP_USER': os.getenv('SMTP_USER', ''),
            'SMTP_PASS': os.getenv('SMTP_PASS', ''),
            'SMTP_STARTTLS': os.getenv('SMTP_STARTTLS', 'true'),
            'ADMIN_USER': os.getenv('ADMIN_USER', 'admin'),
            'ADMIN_PASSWORD': os.getenv('ADMIN_PASSWORD', 'password'),
            'SCAN_SCHEDULE': os.getenv('SCAN_SCHEDULE', '')
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_settings = json.load(f)
                # Merge, giving preference to file settings over env defaults
                env_settings.update(file_settings)
            except (json.JSONDecodeError, TypeError):
                # If file is corrupt, fall back to env settings
                pass
        
        return env_settings

    def get(self, key, default=None):
        """Gets a configuration value."""
        return self.settings.get(key, default)

    def save(self, new_settings):
        """Saves the updated settings to the JSON file."""
        # Update current settings with the new ones
        self.settings.update(new_settings)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

# Global config instance
config = Config()
