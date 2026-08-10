# Illnet Rx contributor guide

Illnet Rx is a Dockerized, local-first Linux security scanner. The canonical runtime lives under `Illnet-Rx/`; the repository root owns Compose, setup, the public landing page, and tests.

## Run locally

```bash
export OPENAI_API_KEY="sk-..."
export ADMIN_PASSWORD="use-a-strong-password-at-least-12-characters"
./setup.sh
docker compose -f compose.yaml up --build -d
```

Use `http://localhost:5001`, log in as `admin`, open **Scanner**, and run a scan. Raw logs and generated Markdown/HTML/JSON reports persist under `Illnet-Rx/data/reports/`.

The installer also supports stdin execution:

```bash
export OPENAI_API_KEY="sk-..."
export ADMIN_PASSWORD="use-a-strong-password-at-least-12-characters"
curl -fsSL https://raw.githubusercontent.com/jordanistan/illnetwork/main/setup.sh | bash
cd illnetwork
docker compose -f compose.yaml up --build -d
```

For automation, use `./setup.sh --non-interactive local OPENAI_API_KEY ADMIN_PASSWORD`. SSH mode is `./setup.sh --non-interactive ssh REMOTE_HOST REMOTE_USER OPENAI_API_KEY ADMIN_PASSWORD`.

## Architecture

- `Illnet-Rx/scanner/scanner.py` dynamically loads plugins and emits report markers.
- `Illnet-Rx/scanner/plugins/` contains ClamAV, rkhunter, freshclam, and credential checks.
- `Illnet-Rx/scanner/parse_logs.py` creates Markdown, HTML, and JSON reports. Missing OpenAI dependencies or keys produce a fallback report.
- `Illnet-Rx/webui/app.py` streams scans, invokes the parser, serves reports, and accepts agent reports.
- `compose.yaml` is canonical and maps `Illnet-Rx/data` to `/opt/data`.

## Verification

```bash
python3 -m unittest discover -s tests -v
git diff --check
```

Preserve path validation, CSRF checks, strong-password validation, local-first SSH gating, pipe-safe setup, and fallback report generation.
