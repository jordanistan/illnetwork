# Project: Illnet Rx - Homelab Security Scanner

## Directory Overview

This directory contains the source code and configuration for **Illnet Rx**, a web-based security scanner designed for homelab environments. The project's brand identity, "Illnet Rx," positions it as a "prescription for enterprise compliance," using an AI-driven diagnostic approach to security.

The application is containerized using Docker and consists of two main components:
1.  A **scanner** backend that runs security tools like ClamAV (malware), rkhunter (rootkits), and other checks.
2.  A **web UI** (built with Flask) that provides a user interface to run scans, view live log streams, and access generated reports.

## Key Technologies

*   **Backend:** Python, Shell (Bash)
*   **Frontend:** Flask, HTML, CSS, JavaScript
*   **AI:** OpenAI GPT-4 for log analysis and report generation.
*   **Scanning Tools:** ClamAV, rkhunter, `ss`/`netstat`.
*   **Containerization:** Docker, Docker Compose
*   **Alerting:** Slack, Email (SMTP)

## Building and Running the Project

To build and run the application, follow these steps:

1.  **Set Environment Variables:**
    Create a `.env` file in the root directory or export the following environment variables. The `OPENAI_API_KEY` is required for the AI analysis feature.

    ```bash
    # Required for AI-powered analysis
    export OPENAI_API_KEY="sk-..."

    # Optional: For Slack alerts
    export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

    # Optional: For Email alerts
    export ALERT_EMAIL_TO="you@example.com"
    export SMTP_HOST="smtp.example.com"
    export SMTP_PORT="587"
    export SMTP_USER="smtp-user"
    export SMTP_PASS="smtp-pass"
    export SMTP_STARTTLS="true"
    ```

2.  **Run with Docker Compose:**
    Execute the following command to build and start the container in detached mode.

    ```bash
    docker-compose up --build -d
    ```

3.  **Access the Web UI:**
    Open your web browser and navigate to `http://localhost:5000`. From there, you can initiate a new scan.

## Development Conventions

*   **Configuration:** The application is configured via environment variables, as defined in the `docker-compose.yml` file. This includes API keys, alert settings, and scan parameters.
*   **Code Structure:** The project is organized into `scanner/` and `webui/` directories, separating the core scanning logic from the presentation layer.
*   **Output:** Scan logs and AI-generated reports (in Markdown, HTML, and JSON formats) are saved to the `./data/reports` directory by default, which is mapped to `/opt/data/reports` inside the container.
*   **Alerting:** Alerts are triggered based on scan findings (e.g., malware found) or if the AI-generated summary flags a severity of "High" or "Critical". The severity threshold for alerts is configurable via the `ALERT_SEVERITY_THRESHOLD` environment variable.
*   **Dependencies:** Python dependencies are managed in `scanner/requirements.txt`.
