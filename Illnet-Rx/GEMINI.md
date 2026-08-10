# Illnet Rx application guide

This directory contains the runtime application: the plugin scanner, Flask web UI, Dockerfile, and persistent data volume.

## Start

Run setup from the repository root, then start Compose:

```bash
cd ..
export OPENAI_API_KEY="sk-..."
export ADMIN_PASSWORD="use-a-strong-password-at-least-12-characters"
./setup.sh
docker compose -f compose.yaml up --build -d
```

The UI is at `http://localhost:5001`. Sign in as `admin`, open **Scanner**, and run a scan. Reports are stored in `data/reports/` and survive container recreation.

OpenAI analysis is optional at runtime: without a usable key or client, the raw scan still produces fallback Markdown, HTML, and JSON reports.

## Runtime flow

The scanner emits `__REPORT_FILE__=...` and `__TARGET_HOST__=...`. The web UI captures those markers, passes the raw log to `parse_logs.py`, and refreshes the report archive. A report is complete when the parser prints `Reports saved:` and the three output files exist.

## Components

- `scanner/scanner.py` — plugin orchestration and raw report logging.
- `scanner/plugins/` — ClamAV, rkhunter, freshclam, and credential checks.
- `scanner/parse_logs.py` — report generation and severity derivation.
- `webui/app.py` — authentication, SSE scan streaming, reports, remediation, scheduling, and agent intake.
- `webui/security.py` — CSRF, path, secret masking, and remediation safety controls.
- `entrypoint.sh` — mounts SSH mode only when explicitly configured, then starts Flask.
