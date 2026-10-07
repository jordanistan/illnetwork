# Illnet Rx

Illnet Rx is a local-first Linux security scanner. It runs ClamAV, rkhunter, and credential checks in a Docker container, streams scan output in the web UI, and saves raw logs plus Markdown, HTML, and JSON reports.

## Quick start

From a checkout:

```bash
export OPENAI_API_KEY="sk-..."
export ADMIN_PASSWORD="use-a-strong-password-at-least-12-characters"
./setup.sh
docker compose -f compose.yaml up --build -d
```

Open http://localhost:5001, sign in with username `admin`, open **Scanner**, and select **Run new scan**. The scan log streams live. When it finishes, the report archive contains the raw scan and generated `.md`, `.html`, and `.json` files.

The setup script writes secrets to `Illnet-Rx/.env` with mode `0600`. Reports persist in `Illnet-Rx/data/reports` through the Compose volume.

### Piped bootstrap

The installer is safe to run from stdin. It clones the repository into `./illnetwork` when run outside a checkout, then writes the environment file there:

```bash
export OPENAI_API_KEY="sk-..."
export ADMIN_PASSWORD="use-a-strong-password-at-least-12-characters"
curl -fsSL https://raw.githubusercontent.com/jordanistan/illnetwork/main/setup.sh | bash
cd illnetwork
docker compose -f compose.yaml up --build -d
```

For CI or another non-interactive shell, pass the mode and values explicitly:

```bash
./setup.sh --non-interactive local "$OPENAI_API_KEY" "$ADMIN_PASSWORD"
```

Use `ssh` mode only when the container should scan a mounted remote host:

```bash
./setup.sh --non-interactive ssh REMOTE_HOST REMOTE_USER "$OPENAI_API_KEY" "$ADMIN_PASSWORD"
```

## Scan and report flow

1. `Scanner.run_scan()` executes the enabled plugins and writes a raw log under `/opt/data/reports`.
2. The web UI consumes the `__REPORT_FILE__` and `__TARGET_HOST__` markers from the scan stream.
3. `parse_logs.py` analyzes the raw log. If no OpenAI key or client is available, it still writes a useful fallback report instead of failing.
4. The parser writes Markdown, HTML, and JSON reports to the shared reports directory.
5. `/reports` lists the generated reports and `/report/view/<filename>` renders the Markdown safely.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `ADMIN_USER` | Web UI username | `admin` |
| `ADMIN_PASSWORD` | Strong web UI password | required |
| `OPENAI_API_KEY` | Optional GPT analysis and remediation detail | empty |
| `SCAN_MODE` | `local` or `ssh` | `local` |
| `REMOTE_HOST` | Remote host for SSH mode | empty |
| `REMOTE_USER` | Remote SSH username | empty |
| `SCAN_PATH` | Path inside the target filesystem | `/opt/data` in Compose |
| `AGENT_TOKEN` | Token for remote agent intake | empty |
| `ALERT_SEVERITY_THRESHOLD` | Alert threshold | `high` |
| `SLACK_WEBHOOK_URL` | Optional Slack alert destination | empty |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_STARTTLS` | Optional email alert settings | see `.env` |

## Useful commands

```bash
docker compose -f compose.yaml logs -f illnet-rx
docker compose -f compose.yaml ps
docker compose -f compose.yaml down
python3 -m unittest discover -s tests -v
```

To use a remote agent, configure `AGENT_TOKEN`, then run `Illnet-Rx/agent/install.sh` on the target host. The agent posts scan text to `POST /api/agent/report` and the dashboard generates the same report artifacts.

## Repository map

- `setup.sh` — checkout and pipe-safe installer.
- `compose.yaml` — canonical Docker Compose deployment.
- `learning-labs/` — safe, reproducible Linux, infrastructure, and intelligent-workflow exercises.
- `Illnet-Rx/scanner/` — plugin scanner and report parser.
- `Illnet-Rx/webui/` — Flask application, templates, and report routes.
- `Illnet-Rx/data/reports/` — persisted raw and generated reports.
- `tests/` — installer, security, agent, and report-generation tests.
