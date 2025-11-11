<div align="center">
  <img src="assets/img/logo.png" alt="Illnet Rx Logo" width="120">
  <h1 style="font-family: 'Montserrat', sans-serif; font-weight: 700; color: #e5e7eb;">Illnet Rx</h1>
  <p style="font-family: 'Montserrat', sans-serif; font-style: italic; color: #93c5fd;">Your prescription for enterprise compliance.</p>
</div>

<p align="center">
  <img alt="Language" src="https://img.shields.io/github/languages/top/jordanistan/illnetwork?style=for-the-badge&color=2563eb&labelColor=0b1220">
  <img alt="Repo Size" src="https://img.shields.io/github/repo-size/jordanistan/illnetwork?style=for-the-badge&color=2563eb&labelColor=0b1220">
  <img alt="License" src="https://img.shields.io/github/license/jordanistan/illnetwork?style=for-the-badge&color=2563eb&labelColor=0b1220">
</p>

---

## :pill: About Illnet Rx

**Illnet Rx** is an AI-driven security and compliance scanner designed for modern homelabs and enterprise systems. It performs a comprehensive audit of a target system (local or remote), uses the power of GPT-4 to analyze the findings, and generates a clear, actionable "prescription" to remediate vulnerabilities and harden your security posture.

Don't just scan. **Diagnose and cure.**

## :sparkles: Features

- :microscope: **Comprehensive Diagnostics:** Utilizes a suite of industry-standard tools like **ClamAV** (malware), **rkhunter** (rootkits), and various system checks to perform a deep-level audit.
- :robot: **AI-Powered Analysis:** Leverages **GPT-4** to interpret raw scan logs, identify critical issues, and provide expert-level analysis.
- :clipboard: **Actionable Prescriptions:** Generates detailed, copy-pasteable remediation commands for every identified issue.
- :satellite: **Remote & Local Scanning:** Seamlessly scan the local container environment or a remote host over SSH.
- :bell: **Real-time Alerts:** Get notified via **Slack** or **Email** when high-severity issues are detected.
- :tv: **Live Web Interface:** A modern, real-time web UI to run scans, monitor progress, and view reports.

## :rocket: Getting Started

Getting started with Illnet Rx involves a one-time setup script and a single Docker command.

### 1. Prerequisites

- **Docker** and **Docker Compose**
- **Git**
- **SSH access** to the remote host you intend to scan (with a private key, typically `~/.ssh/id_rsa`).

### 2. Configuration

The included setup script will configure your environment, create a `.env` file for your credentials, and prepare the application for launch.

```bash
# Run the interactive setup script
bash Illnet-Rx/setup.sh
```

This script will ask for:
1.  The **remote host's IP address or hostname**.
2.  The **remote user** for the SSH connection.
3.  Your **OpenAI API Key**.

It will then verify SSH access and create the `./Illnet-Rx/.env` file for you.

### 3. Launching the Application

Once the setup is complete, you can build and run the application using Docker Compose:

```bash
# Build and start the services in detached mode
docker-compose up --build -d
```

### 4. Accessing Illnet Rx

The web interface will be available at: **[http://localhost:5001](http://localhost:5001)**

From there, you can start your first scan and view the live results.

## :memo: License

This project is under the MIT License. For more details, see the `LICENSE` file.

<div align="center">
Made with :heart: by <a href="https://github.com/jordanistan" target="_blank">Jordanistan</a>
</div>