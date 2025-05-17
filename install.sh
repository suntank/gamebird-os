#!/bin/bash
set -e

# Paths
REPO_DIR="/home/pi/gamebird-os"
TARGET_SETTINGS_DIR="/home/pi/gamebird/settings"
LOG_FILE="$REPO_DIR/install.log"

echo "=== Game Bird Installer ===" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"

# 1. Copy settings
if [ -d "$REPO_DIR/settings" ]; then
    echo "Copying settings..." | tee -a "$LOG_FILE"
    for file in "$REPO_DIR/settings/"*.sh; do
        target="$TARGET_SETTINGS_DIR/$(basename "$file")"
        if ! cmp -s "$file" "$target"; then
            echo "Installing updated: $(basename "$file")" | tee -a "$LOG_FILE"
            cp "$file" "$target"
            chmod +x "$target"
        else
            echo "Unchanged: $(basename "$file")" | tee -a "$LOG_FILE"
        fi
    done
else
    echo "No settings to install." | tee -a "$LOG_FILE"
fi

# # 2. Copy service files EXAMPLE
# if [ -d "$REPO_DIR/services" ]; then
#     echo "[2/3] Installing systemd services..." | tee -a "$LOG_FILE"
#     cp "$REPO_DIR/services/"*.service /etc/systemd/system/
#     systemctl daemon-reexec
#     systemctl daemon-reload
#     systemctl enable gamebird-overlay.service 2>/dev/null || true
# else
#     echo "No services to install." | tee -a "$LOG_FILE"
# fi

# 3. Log version
if [ -f "$REPO_DIR/.last_update_commit" ]; then
    echo "Updated to commit:" | tee -a "$LOG_FILE"
    cat "$REPO_DIR/.last_update_commit" | tee -a "$LOG_FILE"
fi

echo "Install finished: $(date)" | tee -a "$LOG_FILE"
exit 0
