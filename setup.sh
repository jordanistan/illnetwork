#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]-}"
if [[ -n "$SCRIPT_SOURCE" && -f "$SCRIPT_SOURCE" ]]; then
  SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd)"
else
  # A script downloaded with `curl | bash` has no file-backed BASH_SOURCE.
  SCRIPT_DIR="$(pwd -P)"
fi
if [[ -d "${SCRIPT_DIR}/Illnet-Rx" ]]; then
  REPO_ROOT="$SCRIPT_DIR"
elif [[ -d "${SCRIPT_DIR}/../Illnet-Rx" ]]; then
  REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
else
  REPO_ROOT="$SCRIPT_DIR"
fi

# When run from a pipe outside a checkout, fetch the runnable repository first.
if [[ ! -d "${REPO_ROOT}/Illnet-Rx" || ! -f "${REPO_ROOT}/docker-compose.yml" ]]; then
  INSTALL_DIR="${ILLNET_INSTALL_DIR:-${PWD}/illnetwork}"
  REPO_URL="${ILLNET_REPO_URL:-https://github.com/jordanistan/illnetwork.git}"
  if [[ "${ILLNET_BOOTSTRAPPED:-0}" != "1" ]]; then
    if ! command -v git >/dev/null 2>&1; then
      echo "[!] git is required when setup.sh is run from a pipe outside a checkout." >&2
      exit 1
    fi
    if [[ -e "$INSTALL_DIR" && ! -d "$INSTALL_DIR/.git" ]]; then
      echo "[!] Install directory already exists and is not a Git checkout: $INSTALL_DIR" >&2
      exit 1
    fi
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
      echo "[*] Downloading Illnet Rx into $INSTALL_DIR."
      git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
    bootstrap_args=("$@")
    if [[ ${#bootstrap_args[@]} -eq 0 && -n "${OPENAI_API_KEY:-}" ]]; then
      bootstrap_args=(--non-interactive local "$OPENAI_API_KEY" "${ADMIN_PASSWORD:-}")
    fi
    export ILLNET_BOOTSTRAPPED=1
    exec env ENV_FILE="${ENV_FILE:-$INSTALL_DIR/Illnet-Rx/.env}" \
      "$INSTALL_DIR/setup.sh" "${bootstrap_args[@]}"
  fi
fi

DEFAULT_ENV_FILE="${REPO_ROOT}/Illnet-Rx/.env"
ENV_FILE="${ENV_FILE:-$DEFAULT_ENV_FILE}"
SSH_KEY_PATH="${SSH_KEY_PATH:-$HOME/.ssh/id_rsa}"
NON_INTERACTIVE=0

# Permit `OPENAI_API_KEY=... ADMIN_PASSWORD=... curl ... | bash`.
if [[ $# -eq 0 && -n "${OPENAI_API_KEY:-}" ]]; then
  set -- --non-interactive local "$OPENAI_API_KEY" "${ADMIN_PASSWORD:-}"
fi

usage() {
  cat <<'USAGE'
Illnet Rx Remote Scanner Setup

Usage:
  ./setup.sh
  ./setup.sh --non-interactive local <OPENAI_API_KEY> [ADMIN_PASSWORD]
  ./setup.sh --non-interactive ssh <REMOTE_HOST> <REMOTE_USER> <OPENAI_API_KEY> [ADMIN_PASSWORD]

Required tools:
  Debian/Ubuntu: sudo apt install openssh-client
  Red Hat/Fedora: sudo dnf install openssh-clients
  Arch: sudo pacman -S openssh
  macOS: xcode-select --install, or brew install openssh

Environment overrides:
  ENV_FILE       Destination .env path
  SSH_KEY_PATH   SSH private key path
  ADMIN_PASSWORD Admin UI password for non-interactive mode
USAGE
}

install_help() {
  echo "[!] Missing required OpenSSH tools." >&2
  echo "Install them with one of:" >&2
  echo "  Debian/Ubuntu: sudo apt install openssh-client" >&2
  echo "  Red Hat/Fedora: sudo dnf install openssh-clients" >&2
  echo "  Arch: sudo pacman -S openssh" >&2
  echo "  macOS: xcode-select --install, or brew install openssh" >&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

prompt_required() {
  local prompt="$1"
  local var
  while true; do
    read -r -p "$prompt" var
    if [[ -n "$var" ]]; then
      printf '%s' "$var"
      return
    fi
    echo "[!] Value cannot be empty." >&2
  done
}

prompt_secret_required() {
  local prompt="$1"
  local var
  while true; do
    read -r -s -p "$prompt" var
    echo
    if [[ -n "$var" ]]; then
      printf '%s' "$var"
      return
    fi
    echo "[!] Value cannot be empty." >&2
  done
}

prompt_choice() {
  local prompt="$1"
  local choice
  while true; do
    read -r -p "$prompt" choice
    case "$choice" in
      local|ssh)
        printf '%s' "$choice"
        return
        ;;
      *)
        echo "[!] Choose either 'local' or 'ssh'." >&2
        ;;
    esac
  done
}

generate_password() {
  if need_cmd openssl; then
    openssl rand -base64 24 | tr -d '\n'
  elif need_cmd python3; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(24), end="")'
  else
    echo "[!] openssl/python3 not found; generating a lower-grade fallback password." >&2
    printf 'illnet-%s-%s' "$(date +%s)" "$$"
  fi
}

write_env_var() {
  local key="$1"
  local value="$2"
  printf '%s=%q\n' "$key" "$value" >> "$ENV_FILE"
}

ensure_ssh_key() {
  mkdir -p "$(dirname "$SSH_KEY_PATH")"
  chmod 700 "$(dirname "$SSH_KEY_PATH")"

  if [[ -f "$SSH_KEY_PATH" ]]; then
    echo "[*] Existing SSH key found at $SSH_KEY_PATH."
    return
  fi

  echo "[*] No existing SSH key found at $SSH_KEY_PATH."
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
    echo "[*] Non-interactive mode: generating a new SSH key."
    ssh-keygen -t ed25519 -N "" -f "$SSH_KEY_PATH" >/dev/null
    return
  fi

  read -r -p "Generate a new SSH key now? (y/n) " reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    ssh-keygen -t ed25519 -N "" -f "$SSH_KEY_PATH"
  else
    echo "[!] SSH key is required. Generate one and run setup again." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive)
      NON_INTERACTIVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [[ ! -t 0 ]]; then
  NON_INTERACTIVE=1
fi

echo "--- Illnet Rx Remote Scanner Setup ---"
echo

MODE="local"

if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
  if [[ "${1:-}" == "local" || "${1:-}" == "ssh" ]]; then
    MODE="$1"
    shift
  fi
  if [[ "$MODE" == "local" && ( "$#" -lt 1 || "$#" -gt 2 ) ]]; then
    echo "[!] Local non-interactive mode requires OPENAI_API_KEY and optional ADMIN_PASSWORD." >&2
    usage >&2
    exit 1
  fi
  if [[ "$MODE" == "ssh" && ( "$#" -lt 3 || "$#" -gt 4 ) ]]; then
    echo "[!] SSH non-interactive mode requires REMOTE_HOST, REMOTE_USER, OPENAI_API_KEY, and optional ADMIN_PASSWORD." >&2
    usage >&2
    exit 1
  fi
  if [[ "$MODE" == "local" ]]; then
    REMOTE_HOST=""
    REMOTE_USER=""
    OPENAI_API_KEY="$1"
    ADMIN_PASSWORD="${2:-${ADMIN_PASSWORD:-}}"
  else
    REMOTE_HOST="$1"
    REMOTE_USER="$2"
    OPENAI_API_KEY="$3"
    ADMIN_PASSWORD="${4:-${ADMIN_PASSWORD:-}}"
  fi
  if [[ -z "$ADMIN_PASSWORD" ]]; then
    ADMIN_PASSWORD="$(generate_password)"
    echo "[*] Generated ADMIN_PASSWORD for the web UI: $ADMIN_PASSWORD"
  fi
else
  MODE="$(prompt_choice "Choose deployment mode (local or ssh): ")"
  if [[ "$MODE" == "ssh" ]]; then
    REMOTE_HOST="$(prompt_required "Enter the remote host IP address or hostname: ")"
    REMOTE_USER="$(prompt_required "Enter the remote host username: ")"
  else
    REMOTE_HOST=""
    REMOTE_USER=""
  fi
  OPENAI_API_KEY="$(prompt_secret_required "Enter your OpenAI API key: ")"
  ADMIN_PASSWORD="$(prompt_secret_required "Create a web UI admin password (12+ chars): ")"
fi

if [[ ${#ADMIN_PASSWORD} -lt 12 || "$ADMIN_PASSWORD" == "password" ]]; then
  echo "[!] ADMIN_PASSWORD must be non-default and at least 12 characters." >&2
  exit 1
fi

if [[ "$MODE" == "ssh" ]]; then
  if ! need_cmd ssh-keygen || ! need_cmd ssh; then
    install_help
    exit 1
  fi
  ensure_ssh_key
  if [[ "$NON_INTERACTIVE" -eq 0 ]] && need_cmd ssh-copy-id; then
    echo "[*] Copying your public SSH key to ${REMOTE_USER}@${REMOTE_HOST}."
    ssh-copy-id "${REMOTE_USER}@${REMOTE_HOST}"
  else
    echo
    echo "--- ACTION REQUIRED ---"
    echo "Add this public key to ~${REMOTE_USER}/.ssh/authorized_keys on ${REMOTE_HOST}:"
    echo "----"
    cat "${SSH_KEY_PATH}.pub"
    echo "----"
    echo
  fi
fi

echo "[*] Creating $ENV_FILE."
mkdir -p "$(dirname "$ENV_FILE")"
umask 077
: > "$ENV_FILE"
{
  echo "# This file is automatically generated by setup.sh"
  echo "# Docker Compose uses these variables to configure Illnet Rx."
  echo
} >> "$ENV_FILE"
write_env_var "SCAN_MODE" "$MODE"
if [[ "$MODE" == "ssh" ]]; then
  write_env_var "REMOTE_HOST" "$REMOTE_HOST"
  write_env_var "REMOTE_USER" "$REMOTE_USER"
fi
write_env_var "OPENAI_API_KEY" "$OPENAI_API_KEY"
write_env_var "ADMIN_USER" "admin"
write_env_var "ADMIN_PASSWORD" "$ADMIN_PASSWORD"
write_env_var "SCAN_SCHEDULE" ""
chmod 600 "$ENV_FILE"

echo
echo "--- Setup Complete ---"
echo "Environment written to: $ENV_FILE"
echo "Start the app with Docker Compose, then open http://localhost:5001."
echo "Local scans are enabled by default. Use SSH mode only if you want a mounted remote host."
echo "Remote agents can be installed from Illnet-Rx/agent/install.sh."
