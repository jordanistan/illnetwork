# Illnet Rx runtime reference

The runtime is a Flask web UI backed by a Python plugin scanner. The repository root owns setup and Compose; this directory owns the container image and application code.

## Run

From the repository root:

```bash
./setup.sh
docker compose -f compose.yaml up --build -d
```

Open `http://localhost:5001`, authenticate, and run a scan from **Scanner**. The raw scan log is written to `data/reports/`; the parser creates matching `.md`, `.html`, and `.json` reports.

## Report generation

`scanner/scanner.py` emits the raw report path and target host. `webui/app.py` captures those markers from `/scan/stream`, then invokes `scanner/parse_logs.py`. The parser always preserves a report: it uses GPT analysis when configured, and writes a fallback summary when the OpenAI key or Python client is unavailable.

## Endpoints

- `GET /login`, `POST /login` — authentication.
- `GET /dashboard` — latest report summary.
- `GET /scanner` — manual scan page.
- `GET /scan/stream` — authenticated Server-Sent Events scan stream.
- `GET /reports` — report archive.
- `GET /report/view/<filename>` — safe Markdown report view.
- `GET /reports/<filename>` — raw report download.
- `POST /api/agent/report` — token-authenticated remote agent intake.
- `POST /report/<filename>/remediate` — generate a remediation script for review.
- `POST /remediate/execute/<target_host>` — execute an explicitly reviewed script.

## Development checks

```bash
cd ..
python3 -m unittest discover -s tests -v
git diff --check
```

Do not weaken CSRF, path validation, secret masking, agent-token validation, or the local-first SSH boundary.
