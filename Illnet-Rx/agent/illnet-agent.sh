#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/illnet-agent.env}"

if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

: "${DASHBOARD_URL:?Set DASHBOARD_URL in /etc/illnet-agent.env}"
: "${AGENT_TOKEN:?Set AGENT_TOKEN in /etc/illnet-agent.env}"

SCAN_PATH="${SCAN_PATH:-/}"
REPORT_DIR="${REPORT_DIR:-/tmp}"
TARGET_HOST="${TARGET_HOST:-$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo agent)}"
REPORT_FILE="$(mktemp "${REPORT_DIR%/}/illnet-agent-XXXXXX.txt")"

cleanup() {
  rm -f "$REPORT_FILE"
}
trap cleanup EXIT

run_tool() {
  local label="$1"
  shift
  echo "[*] $label"
  if command -v "$1" >/dev/null 2>&1; then
    "$@" || true
  else
    echo "[!] $1 not installed; skipping."
  fi
}

{
  echo "=== Illnet Agent Scan ==="
  echo "Target: $TARGET_HOST"
  echo "Started: $(date -Is)"
  echo "Report file: $REPORT_FILE"
  echo "Scan path: $SCAN_PATH"
  echo "--------------------------------------"

  run_tool "Updating ClamAV defs (freshclam)" freshclam
  run_tool "Running ClamAV scan" clamscan -r --bell -i "$SCAN_PATH"
  run_tool "Running rkhunter rootkit check" rkhunter --check --sk

  echo "[*] Scanning for exposed credentials..."
  find "$SCAN_PATH/home" "$SCAN_PATH/etc" -type f \( -name '*id_rsa*' -o -name '*.pem' -o -name '*.key' -o -name '*.token' -o -name '*.env' \) 2>/dev/null | sed 's/^/CRED: /'

  echo "--------------------------------------"
  echo "Completed: $(date -Is)"
} 2>&1 | tee "$REPORT_FILE"

echo "[*] Reporting scan results to dashboard..."
curl --fail --silent --show-error \
  -X POST "${DASHBOARD_URL%/}/api/agent/report" \
  -H "Content-Type: text/plain" \
  -H "X-Illnet-Agent-Token: ${AGENT_TOKEN}" \
  -H "X-Illnet-Agent-Hostname: ${TARGET_HOST}" \
  --data-binary @"$REPORT_FILE"

echo "[*] Agent run complete."
