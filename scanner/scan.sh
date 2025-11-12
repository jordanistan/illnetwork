#!/bin/bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-/opt/data/reports}"
mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$OUTPUT_DIR/report_${TIMESTAMP}.txt"

# This function contains the core scanning logic.
run_scan() {
    local SCAN_ROOT="/"
    local TARGET_HOST="localhost"

    if [[ -n "${REMOTE_HOST:-}" ]]; then
        # If a remote host is defined, we scan the mount point.
        SCAN_ROOT="/mnt/remote"
        TARGET_HOST="${REMOTE_HOST}"
        echo "[*] Remote host is defined. Scanning filesystem mounted at ${SCAN_ROOT}"
    else
        echo "[*] No remote host defined. Scanning local container filesystem."
    fi

    echo "=== Homelab Security Scan ==="
    echo "Target: $TARGET_HOST"
    echo "Started: $(date -Is)"
    echo "Report file: $REPORT_FILE"
    echo "--------------------------------------"

    # Update AV defs (always runs locally in the container)
    echo "[*] Updating ClamAV defs (freshclam)..."
    sudo freshclam || echo "[!] freshclam update failed (continuing)."

    # 1. Malware scan
    # If SCAN_PATH is provided, it's treated as a subdirectory of the scan root.
    SCAN_SUBDIR="${SCAN_PATH:-}"
    FULL_SCAN_PATH="${SCAN_ROOT}${SCAN_SUBDIR}"
    echo "[*] Running ClamAV scan on: ${FULL_SCAN_PATH}"
    # The `|| true` is important because clamscan returns 1 if viruses are found,
    # which would otherwise cause the script to exit due to `set -e`.
    sudo clamscan -r --bell -i "${FULL_SCAN_PATH}" || true

    # 2. Rootkit scan
    echo "[*] Running rkhunter rootkit check on filesystem at ${SCAN_ROOT}"
    # We use --rootdir to tell rkhunter to check the specified directory as the root.
    # This is less effective than a live scan, but it's the correct approach for a mounted fs.
    sudo rkhunter --check --rootdir "${SCAN_ROOT}" --sk || true

    # 3. Credential & secret scan
    echo "[*] Scanning for exposed credentials in ${SCAN_ROOT}/home and ${SCAN_ROOT}/etc..."
    # We search common locations within the mounted filesystem.
    sudo find "${SCAN_ROOT}/home" "${SCAN_ROOT}/etc" -type f \( -name '*id_rsa*' -o -name '*.pem' -o -name '*.key' -o -name '*.token' -o -name '*.env' \) 2>/dev/null | sed 's/^/CRED: /'

    echo "--------------------------------------"
    echo "Completed: $(date -Is)"
    echo "[*] Scan complete. Report saved to $REPORT_FILE"
}

# --- Execution ---
run_scan 2>&1 | tee -a "$REPORT_FILE"

# Emit machine-readable lines for the UI.
echo "__REPORT_FILE__=$REPORT_FILE"
echo "__TARGET_HOST__=${REMOTE_HOST:-localhost}"
