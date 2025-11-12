# Illnet Rx - Technical Reference

This document provides a technical overview of the Illnet Rx application, intended for developers and contributors.

## Architecture

The application is composed of two main components: a `scanner` engine and a `webui` for interaction and reporting.

-   **`scanner/`**: This directory contains the core logic for the security audit.
    -   `scan.sh`: The main Bash script that executes the sequence of security tools (ClamAV, rkhunter, etc.). It is designed to be able to run against the local filesystem or a mounted remote filesystem.
    -   `parse_logs.py`: A Python script that takes the raw output from `scan.sh`, extracts key indicators, and sends the log to the GPT-4 API for analysis and report generation.
    -   `alerts.py`: Handles sending notifications to Slack or via email if the scan results meet the configured severity threshold.

-   **`webui/`**: A Python Flask application that provides the user interface.
    -   `app.py`: The main Flask application file. It handles HTTP requests, serves the frontend, and manages the scanning process.
    -   `templates/`: Contains the Jinja2 HTML templates for the web interface.
    -   `static/`: Contains the CSS stylesheets.

-   **`Dockerfile`**: A `python:3.12-slim` based Dockerfile that installs all necessary system-level tools (e.g., `clamav`, `rkhunter`, `sshfs`) and Python dependencies.

-   **`entrypoint.sh`**: This script is the container's entrypoint. Its primary role is to check for the `REMOTE_HOST` environment variable and, if present, mount the remote host's root filesystem to `/mnt/remote` using `sshfs` before starting the web application.

## Environment Variables

The application is configured via environment variables, which are loaded from the `.env` file by `docker-compose`.

| Variable | Required | Description | Default |
| :--- | :---: | :--- | :--- |
| `REMOTE_HOST` | **Yes** | IP address or hostname of the server to scan. | |
| `REMOTE_USER` | **Yes** | Username for the SSH connection to the remote host. | |
| `OPENAI_API_KEY` | **Yes** | API key for OpenAI (used for GPT-4 analysis). | |
| `SCAN_PATH` | No | Specify a subdirectory to scan relative to the root of the target filesystem. | `/opt/data` |
| `ALERT_SEVERITY_THRESHOLD` | No | Minimum severity (`low`, `medium`, `high`, `critical`) to trigger alerts. | `high` |
| `SLACK_WEBHOOK_URL` | No | Your Slack incoming webhook URL for alerts. | |
| `ALERT_EMAIL_TO` | No | Recipient email address for alerts. | |
| `ALERT_EMAIL_FROM`| No | Sender email address for alerts. | `alerts@example.local` |
| `SMTP_HOST` | No | SMTP server for sending email alerts. | |
| `SMTP_PORT` | No | SMTP port. | `587` |
| `SMTP_USER` | No | SMTP username. | |
| `SMTP_PASS` | No | SMTP password. | |
| `SMTP_STARTTLS` | No | Whether to use STARTTLS for SMTP. | `true` |

## API Endpoints

The Flask web application exposes a few simple endpoints:

-   `GET /`: The main scanner page with the live log viewer.
-   `GET /scan/stream`: An `text/event-stream` endpoint that streams the live output of a running scan to the client.
-   `GET /reports`: Displays a list of all generated reports.
-   `GET /reports/<path:filename>`: Serves a specific report file from the reports directory.
-   `GET /api/reports`: A JSON endpoint that returns a list of all available report filenames.