#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
SERVICE_DIR="${SERVICE_DIR:-/etc/systemd/system}"
CONFIG_FILE="${CONFIG_FILE:-/etc/illnet-agent.env}"

usage() {
  cat <<'USAGE'
Illnet Rx Agent Installer

Usage:
  ./install.sh <DASHBOARD_URL> <AGENT_TOKEN> [SCAN_PATH]

The installer writes:
  - /usr/local/bin/illnet-agent
  - /etc/illnet-agent.env
  - a systemd service and timer when systemd is available
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 1
fi

DASHBOARD_URL="$1"
AGENT_TOKEN="$2"
SCAN_PATH="${3:-/}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -m 0755 "$SOURCE_DIR/illnet-agent.sh" "$INSTALL_DIR/illnet-agent"

mkdir -p "$(dirname "$CONFIG_FILE")"
cat > "$CONFIG_FILE" <<EOF
DASHBOARD_URL=$DASHBOARD_URL
AGENT_TOKEN=$AGENT_TOKEN
SCAN_PATH=$SCAN_PATH
REPORT_DIR=/tmp
EOF
chmod 600 "$CONFIG_FILE"

if command -v systemctl >/dev/null 2>&1; then
  cat > "$SERVICE_DIR/illnet-agent.service" <<EOF
[Unit]
Description=Illnet Rx security agent

[Service]
Type=oneshot
EnvironmentFile=$CONFIG_FILE
ExecStart=$INSTALL_DIR/illnet-agent
EOF

  cat > "$SERVICE_DIR/illnet-agent.timer" <<EOF
[Unit]
Description=Run Illnet Rx security agent daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now illnet-agent.timer
  echo "Installed systemd timer: illnet-agent.timer"
else
  echo "systemd not available. Run this command from cron instead:"
  echo "$INSTALL_DIR/illnet-agent"
fi

echo "Agent configuration written to: $CONFIG_FILE"
