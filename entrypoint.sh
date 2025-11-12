#!/bin/bash
set -e

# If REMOTE_HOST is set, mount the remote filesystem
if [ -n "${REMOTE_HOST}" ]; then
    echo "--- Remote host provided, attempting to mount via sshfs ---"
    
    REMOTE_USER="${REMOTE_USER:-root}"
    MOUNT_POINT="/mnt/remote"
    SSH_KEY_PATH="/root/.ssh/id_rsa"

    # Check for required tools and permissions
    if ! command -v sshfs >/dev/null 2>&1; then
        echo "[!] sshfs command not found. Please install it in the container." >&2
        exit 1
    fi
    if [ ! -e /dev/fuse ]; then
        echo "[!] FUSE device /dev/fuse not found. Please run the container with the required device mapping." >&2
        exit 1
    fi
    if [ ! -f "${SSH_KEY_PATH}" ]; then
        echo "[!] SSH private key not found at ${SSH_KEY_PATH}. It must be mounted into the container." >&2
        exit 1
    fi

    # Create the mount point
    mkdir -p "${MOUNT_POINT}"

    echo "[*] Mounting ${REMOTE_USER}@${REMOTE_HOST}:/ to ${MOUNT_POINT}"    
    # Mount the remote filesystem
    sshfs -o allow_other -o StrictHostKeyChecking=no -o IdentityFile="${SSH_KEY_PATH}" \
        "${REMOTE_USER}@${REMOTE_HOST}:/" "${MOUNT_POINT}"
    
    echo "[*] Mount successful."
fi

echo "--- Starting application ---"
# Execute the command passed to this script (e.g., "python app.py")
exec "$@"
