#!/usr/bin/env bash

# ill.network Security Scanner - Setup Script

set -e

# --- Configuration ---
REPO_URL="https://github.com/jordanistan/illnetwork.git"
REPO_DIR="ill.network"

# --- Styling ---
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_CYAN="\033[36m"

info()    { printf "${C_CYAN}[i]${C_RESET} %s\n" "$*"; }
success() { printf "${C_GREEN}[+]${C_RESET} %s\n" "$*"; }
warn()    { printf "${C_YELLOW}[!]${C_RESET} %s\n" "$*"; }

# --- Helper Functions ---
require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: '$1' is not installed. Please install it before running this script." >&2
        exit 1
    fi
}

# --- Main Logic ---
main() {
    info "Starting setup for the ill.network Security Scanner..."

    # Check for dependencies
    require_cmd git
    require_cmd docker

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker is not running. Please start Docker and re-run the script." >&2
        exit 1
    fi

    # Clone or update the repository
    if [ -d "$REPO_DIR" ]; then
        info "Directory '$REPO_DIR' already exists. Pulling latest changes..."
        cd "$REPO_DIR"
        git pull origin main
    else
        info "Cloning the repository..."
        git clone "$REPO_URL"
        cd "$REPO_DIR"
    fi

    info "Building and starting the Docker containers..."
    docker compose up --build -d

    success "Setup complete!"
    echo ""
    info "The web interface should now be running at ${C_BOLD}http://localhost:8080${C_RESET}"
    info "To run a scan, use the following command from this directory:"
    echo ""
    printf "  ${C_YELLOW}docker compose exec scanner ./healthcheck.sh -t <target_host>${C_RESET}\n"
    echo ""
}

main
