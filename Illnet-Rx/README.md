# Illnet Rx - Technical Reference

This document provides a technical overview of the Illnet Rx application, intended for developers and contributors.

## Architecture

The application is composed of a `scanner` engine and a `webui` for interaction and reporting.

-   **`scanner/`**: This directory contains the core Python-based scanning engine.
    -   `scanner.py`: The main scanner module. It does not contain any hardcoded scan logic. Instead, it dynamically loads and executes all available plugins from the `plugins/` directory.
    -   `plugins/`: This directory contains the modular scanning tools. Each file is a self-contained plugin that inherits from `plugins/base.py` and performs a single action (e.g., `clamav_plugin.py`, `rkhunter_plugin.py`). To add a new scanner, you simply add a new file to this directory.
    -   `parse_logs.py`: A Python script that takes raw scan logs, extracts key indicators, and sends the log to the GPT-4 API for analysis and report generation.
    -   `alerts.py`: Handles sending notifications to Slack or via email if the scan results meet the configured severity threshold.

-   **`webui/`**: A Python Flask application that provides the user interface.
    -   `app.py`: The main Flask application file. It handles all HTTP requests, serves the frontend, manages user sessions, and orchestrates the scanner and analysis processes.
    -   `config.py`: A configuration management module that loads settings from `data/config.json`, falling back to environment variables. It provides a single source of truth for all application settings.
    -   `templates/`: Contains the Jinja2 HTML templates for all pages (Dashboard, Scanner, Reports, Settings, etc.).
    -   `static/`: Contains the CSS stylesheets.

-   **`Dockerfile`**: A `python:3.12-slim` based Dockerfile that installs all necessary system-level tools (e.g., `clamav`, `rkhunter`, `sshfs`) and Python dependencies.

-   **`entrypoint.sh`**: This script is the container's entrypoint. Its primary role is to check for a remote host configuration and, if present, mount the remote host's root filesystem to `/mnt/remote` using `sshfs` before starting the web application.

## Configuration

The application is configured primarily via the **Settings** page in the web UI. On first launch, it loads its configuration from environment variables defined in `docker-compose.yml` and the `.env` file. After settings are saved in the UI, they are persisted in `data/config.json`, which then takes precedence.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ADMIN_USER` | Username for the web UI login. | `admin` |
| `ADMIN_PASSWORD` | Password for the web UI login. | `password` |
| `REMOTE_HOST` | IP address or hostname of the server to scan. | |
| `REMOTE_USER` | Username for the SSH connection to the remote host. | |
| `OPENAI_API_KEY` | API key for OpenAI (used for GPT-4 analysis). | |
| `SCAN_PATH` | The absolute path to scan on the target host. | `/` |
| `SCAN_SCHEDULE`| A cron expression to enable automatic scans (e.g., `0 2 * * 0`). | (empty) |
| `ALERT_SEVERITY_THRESHOLD` | Minimum severity (`low`, `medium`, `high`, `critical`) to trigger alerts. | `high` |
| `SLACK_WEBHOOK_URL` | Your Slack incoming webhook URL for alerts. | |
| `ALERT_EMAIL_TO` | Recipient email address for alerts. | |
| `SMTP_HOST` | SMTP server for sending email alerts. | |
| `SMTP_PORT` | SMTP port. | `587` |
| `SMTP_USER` | SMTP username. | |
| `SMTP_PASS` | SMTP password. | |
| `SMTP_STARTTLS` | Whether to use STARTTLS for SMTP. | `true` |


## API Endpoints

The Flask web application exposes several endpoints:

-   `GET /login`: Renders the login page.
-   `POST /login`: Handles user authentication.
-   `GET /logout`: Logs the user out.
-   `GET /`: Redirects to the main dashboard.
-   `GET /dashboard`: Displays the main security dashboard.
-   `GET /scanner`: Displays the page for running manual scans.
-   `GET /scan/stream`: An `text/event-stream` endpoint that streams the live output of a running scan. Accepts a `scan_type` query parameter.
-   `GET /reports`: Displays the list of all generated reports.
-   `GET /report/view/<filename>`: Renders a parsed, human-readable view of a specific report.
-   `POST /report/<filename>/remediate`: Generates an AI-based remediation script for a report.
-   `POST /remediate/execute/<target_host>`: Executes a remediation script on the specified target.
-   `GET /settings`: Renders the application settings page.
-   `POST /settings`: Saves updated application settings.
