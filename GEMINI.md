# Project Overview

This directory contains `healthcheck.sh`, a security and health audit script for Debian-based homelab servers, particularly those running Docker. The script performs various checks to identify potential security vulnerabilities and misconfigurations.

## Key Features

- **System Health:** Checks for pending updates and problematic APT repository configurations.
- **Security Scanning:** Uses tools like `rkhunter`, `chkrootkit`, and `debsums` to scan for rootkits and file integrity issues.
- **Network Exposure:** Identifies public-facing services and Docker containers that might be unintentionally exposed to the internet.
- **Docker Security:** Audits Docker configurations for common security risks, such as host networking mode and secrets stored in environment variables.
- **Firewall Check:** Inspects `iptables` rules to ensure the firewall is properly configured to protect Docker containers.
- **Remediation Plan:** Generates a shell script with recommended commands to fix the identified issues.

# Running the Script

The script is designed to be run on the target Debian-based server.

**To run the healthcheck:**

```bash
sudo ./healthcheck.sh
```

The script will print its findings to the console and create a remediation plan at `/root/hardening_recommendations.sh`.

# Development Conventions

- The script is written in `bash` and follows common shell scripting practices.
- It uses color-coded output to distinguish between good, warning, and bad findings.
- Functions are used to structure the code and improve readability.
- The script is designed to be run with `root` privileges (`sudo`) as it needs to inspect system-level configurations.
