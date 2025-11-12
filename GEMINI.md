# Project Overview

This directory contains **Illnet Rx**, a comprehensive, AI-driven security and compliance scanner for Linux systems, designed to be run as a Docker application.

It provides a full-featured web interface for running scans, viewing reports, and managing application settings. The scanner can perform deep audits on remote hosts via SSH or quick health checks on its local environment.

## Key Features

-   **Web Dashboard:** A dashboard provides a high-level overview of the target system's security posture.
-   **Plugin-Based Scanning:** The scanning engine is modular, allowing for easy extension. It currently includes plugins for:
    -   ClamAV (malware scanning)
    -   Rkhunter (rootkit detection)
    -   Credential exposure scanning
-   **AI Analysis & Remediation:** Scan results are analyzed by GPT-4 to generate a detailed report and an actionable remediation script.
-   **Interactive Execution:** Users can review and safely execute the AI-generated remediation script from the UI while monitoring its live output.
-   **Scheduled Scans:** Scans can be run manually or scheduled automatically via cron expressions.
-   **Configuration UI:** All major application settings can be managed from a "Settings" page in the web UI.
-   **Alerting:** Sends notifications for high-severity findings via Slack or Email.

## Running the Application

The application is designed to be run with Docker Compose.

1.  **Initial Setup:** Run the setup script to configure your environment:
    ```bash
    bash Illnet-Rx/setup.sh
    ```
2.  **Launch:** Start the application using Docker Compose:
    ```bash
    docker-compose up --build -d
    ```

The web interface will be available at `http://localhost:5001`.